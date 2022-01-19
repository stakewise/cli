import collections
import copy
import json
import time
from functools import cached_property, lru_cache
from os import listdir, makedirs
from shutil import rmtree
from typing import Dict, OrderedDict, Set, Union

import click
from eth2deposit.key_handling.keystore import ScryptKeystore
from eth_typing import BLSPubkey, ChecksumAddress, HexStr
from eth_utils import add_0x_prefix
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3
from web3.beacon import Beacon

from operator_cli.eth1 import (
    get_operators_deposit_data_merkle_proofs,
    get_validator_operator_address,
    is_validator_registered,
)
from operator_cli.eth2 import (
    EXITED_STATUSES,
    generate_password,
    get_mnemonic_signing_key,
    get_validators,
)
from operator_cli.ipfs import get_operator_deposit_datum
from operator_cli.queries import get_stakewise_gql_client
from operator_cli.typings import LocalKeystore, LocalState, SigningKey
from operator_cli.vault import generate_validator_name

MAX_KEYS_PER_VALIDATOR = 100
LEGACY_TOTAL_KEYS = 1000


class LocalStorage(object):
    def __init__(
        self,
        beacon: Beacon,
        chain: str,
        mnemonic: str,
        folder: str,
    ):
        self.sw_gql_client = get_stakewise_gql_client(chain)
        self.beacon = beacon
        self.mnemonic = mnemonic
        self.check_mnemonic()
        self.folder = folder

    @cached_property
    def local_validator_names(self) -> Set[str]:
        """Fetches names of local validators."""
        try:
            name = listdir("validators")
            return set(name)
        except FileNotFoundError:
            return set()

    @cached_property
    def local_current_state(self) -> LocalState:
        """Returns mappings of local public keys to keystores."""
        result: LocalState = {}
        with click.progressbar(
            self.local_validator_names,
            label="Fetching local current state\t\t",
            show_percent=False,
            show_pos=True,
        ) as validator_names:
            for validator_name in validator_names:
                try:
                    validator_keystores: Dict[str, str] = []
                    keystores = listdir(f"{self.folder}/{validator_name}/keystores")
                    for keystore in keystores:
                        with open(
                            f"{self.folder}/{validator_name}/keystores/{keystore}"
                        ) as f:
                            data = f.readline()
                            validator_keystores.append(data)
                except FileNotFoundError:
                    continue

                for keystore_str in validator_keystores:
                    keystore = json.loads(keystore_str)
                    public_key = add_0x_prefix(HexStr(keystore["pubkey"]))
                    if public_key in result:
                        raise click.ClickException(
                            f"Public key {public_key} is presented in {validator_name}"
                            f" and {result[public_key]} local validators."
                            f" You must immediately stop both validators to avoid slashing!"
                        )
                    result[public_key] = LocalKeystore(
                        validator_name=validator_name, keystore=keystore_str
                    )

        return result

    @cached_property
    def all_operators_deposit_data_public_keys(self) -> Dict[HexStr, ChecksumAddress]:
        """Fetches public keys and operators from deposit datum."""
        deposit_data_merkle_proofs = get_operators_deposit_data_merkle_proofs(
            self.sw_gql_client
        )
        result: Dict[HexStr, ChecksumAddress] = {}
        with click.progressbar(
            deposit_data_merkle_proofs.items(),
            label="Fetching deposit datum\t\t",
            show_percent=False,
            show_pos=True,
        ) as merkle_proofs:
            for operator_addr, merkle_proofs_url in merkle_proofs:
                deposit_datum = get_operator_deposit_datum(merkle_proofs_url)
                for deposit_data in deposit_datum:
                    public_key = deposit_data["public_key"]
                    if public_key in result:
                        raise click.ClickException(
                            f"Public key {public_key} is presented in"
                            f" deposit datum for {operator_addr} and {result[public_key]} operators"
                        )
                    result[public_key] = operator_addr

        return result

    @cached_property
    def operator_address(self) -> Union[ChecksumAddress, None]:
        """Returns local's operator address."""
        signing_key = get_mnemonic_signing_key(self.mnemonic, 0)
        first_public_key = Web3.toHex(
            primitive=G2ProofOfPossession.SkToPk(signing_key.key)
        )
        operator_address = get_validator_operator_address(
            self.sw_gql_client, first_public_key
        )

        if not operator_address:
            return self.all_operators_deposit_data_public_keys.get(
                first_public_key, None
            )

        return operator_address

    @cached_property
    def operator_deposit_data_public_keys(self) -> Set[HexStr]:
        """Returns operator's deposit data public keys."""
        return set(
            [
                pub_key
                for pub_key, operator in self.all_operators_deposit_data_public_keys.items()
                if operator == self.operator_address
            ]
        )

    @cached_property
    def local_missing_keypairs(self) -> OrderedDict[HexStr, SigningKey]:
        """
        Returns ordered mapping of BLS public key to private key
        that are in deposit data or active but are missing in the local.
        """

        missed_keypairs: OrderedDict[HexStr, SigningKey] = collections.OrderedDict()
        from_index = 0
        while True:
            signing_key = get_mnemonic_signing_key(self.mnemonic, from_index)
            public_key = Web3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))

            if public_key in self.local_current_state:
                from_index += 1
                continue

            if public_key in self.operator_deposit_data_public_keys:
                missed_keypairs[public_key] = signing_key
                from_index += 1
                continue

            is_registered = is_validator_registered(
                gql_client=self.sw_gql_client, public_key=public_key
            )
            if is_registered:
                missed_keypairs[public_key] = signing_key
                from_index += 1
                continue

            break

        if not missed_keypairs:
            return missed_keypairs

        click.confirm(
            f"Fetched {len(missed_keypairs)} missing validator keys. Save them to the local storage?",
            abort=True,
        )

        exited_public_keys: Set[HexStr] = set()
        missed_keypairs_items = list(missed_keypairs.items())
        missed_keypairs_count = len(missed_keypairs_items)
        with click.progressbar(
            length=missed_keypairs_count,
            label="Checking local missing keys statuses\t\t",
            show_percent=False,
            show_pos=True,
        ) as bar:
            for i in range(0, missed_keypairs_count, 100):
                keypairs_chunk = missed_keypairs_items[i : i + 100]
                validators = get_validators(
                    beacon=self.beacon,
                    public_keys=[HexStr(keypair[0]) for keypair in keypairs_chunk],
                    state_id="finalized",
                )
                for validator in validators:
                    if validator["status"] in EXITED_STATUSES:
                        public_key = validator["validator"]["pubkey"]
                        exited_public_keys.add(public_key)

                bar.update(len(keypairs_chunk))

        for public_key in exited_public_keys:
            del missed_keypairs[public_key]

        return missed_keypairs

    @cached_property
    def operator_exited_public_keys(self) -> Set[HexStr]:
        """Returns operator's public keys that have been exited but are still in the local."""
        result: Set[HexStr] = set()

        # fetch validators in chunks of 100 keys
        all_public_keys = list(self.local_current_state.keys())
        for i in range(0, len(all_public_keys), 100):
            validators = get_validators(
                beacon=self.beacon,
                public_keys=all_public_keys[i : i + 100],
                state_id="finalized",
            )
            for validator in validators:
                if validator["status"] in EXITED_STATUSES:
                    public_key = validator["validator"]["pubkey"]
                    result.add(public_key)

        return result

    @cached_property
    def local_new_state(self) -> LocalState:
        """Calculates local new state."""
        validator_keys_count: Dict[str, int] = collections.Counter(
            [
                keystore["validator_name"]
                for keystore in self.local_current_state.values()
            ]
        )
        total_capacity = MAX_KEYS_PER_VALIDATOR * len(validator_keys_count)
        available_slots = (
            total_capacity
            - sum(validator_keys_count.values())
            - len(self.operator_exited_public_keys)
        )
        while available_slots < len(self.local_missing_keypairs):
            new_validator_name = generate_validator_name(
                set(validator_keys_count.keys())
            )
            validator_keys_count[new_validator_name] = 0
            available_slots += MAX_KEYS_PER_VALIDATOR

        new_state = copy.deepcopy(self.local_current_state)

        # get rid of exited validator keys
        for exited_public_key in self.operator_exited_public_keys:
            if exited_public_key in new_state:
                validator_name = self.local_current_state[exited_public_key][
                    "validator_name"
                ]
                del new_state[exited_public_key]

                validator_keys_count[validator_name] -= 1

        # distribute missing keypairs across validators
        with click.progressbar(
            self.local_missing_keypairs,
            label="Provisioning missing validator keys\t\t",
            show_percent=False,
            show_pos=True,
        ) as missing_keypairs:
            for public_key in missing_keypairs:
                validator_name = min(validator_keys_count, key=validator_keys_count.get)
                if public_key not in new_state:
                    signing_key = self.local_missing_keypairs[public_key]
                    secret = signing_key.key.to_bytes(32, "big")
                    password = self.get_or_create_keystore_password(validator_name)
                    keystore = ScryptKeystore.encrypt(
                        secret=secret, password=password, path=signing_key.path
                    ).as_json()
                    new_state[public_key] = LocalKeystore(
                        validator_name=validator_name, keystore=keystore
                    )
                    validator_keys_count[validator_name] += 1

        return new_state

    @lru_cache
    def get_or_create_keystore_password(self, validator_name) -> str:
        """Retrieves validator keystore password if exists or creates a new one."""
        try:
            with open(f"{self.folder}/{validator_name}/password/password.txt") as file:
                password = file.readline()
        except FileNotFoundError:
            password = generate_password()
            makedirs(f"{self.folder}/{validator_name}/password", exist_ok=True)
            with open(
                f"{self.folder}/{validator_name}/password/password.txt", "w"
            ) as file:
                file.write(password)

        return password

    def apply_local_changes(self) -> None:
        """Updates local from current state to new state."""
        # update validator entries
        self.sync_local_validators()

        # sync keystores
        self.sync_local_keystores()

    def sync_local_validators(self) -> None:
        """Synchronizes local validators."""
        prev_validators: Set[str] = set(
            [
                keystore["validator_name"]
                for keystore in self.local_current_state.values()
            ]
        )
        new_validators: Set[str] = set(
            [keystore["validator_name"] for keystore in self.local_new_state.values()]
        )

        removed_validators = prev_validators.difference(new_validators)

        # sync validators
        with click.progressbar(
            length=len(new_validators) + len(removed_validators),
            label="Syncing local validator directories\t\t",
            show_percent=False,
            show_pos=True,
        ) as bar:
            for validator_name in removed_validators:
                rmtree(f"{self.folder}/{validator_name}/password", ignore_errors=True)
                rmtree(f"{self.folder}/{validator_name}/keystores", ignore_errors=True)
                bar.update(1)

    def sync_local_keystores(self) -> None:
        """Synchronizes local keystores."""
        validators_keystores: Dict[str, Dict[str, str]] = {}
        for public_key, local_keystore in self.local_new_state.items():
            validator_name = local_keystore["validator_name"]
            keystores = validators_keystores.setdefault(validator_name, {})
            keystore = local_keystore["keystore"]
            keystore_path = json.loads(keystore)["path"]

            # generate unique keystore name
            keystore_name = "keystore-%s-%i.json" % (
                keystore_path.replace("/", "_"),
                time.time(),
            )

            # save keystore
            keystores[keystore_name] = keystore

        # sync keystores in the local storage
        with click.progressbar(
            validators_keystores,
            label="Syncing local keystores\t\t",
            show_percent=False,
            show_pos=True,
        ) as _validators_keystores:
            for validator_name in _validators_keystores:
                for name, keystore in validators_keystores[validator_name].items():
                    makedirs(f"{self.folder}/{validator_name}/keystores", exist_ok=True)
                    with open(
                        f"{self.folder}/{validator_name}/keystores/" + name, "w"
                    ) as file:
                        file.write(keystore)

    def verify_local_keystores(self) -> None:
        # clean up cached property
        try:
            # noinspection PyPropertyAccess
            del self.local_validator_names
        except AttributeError:
            pass

        public_keys: Set[BLSPubkey] = set()
        with click.progressbar(
            self.local_validator_names,
            label="Verifying local state\t\t",
            show_percent=False,
            show_pos=True,
        ) as validator_names:
            for validator_name in validator_names:
                try:
                    validator_keystores: Dict[str, str] = []
                    keystores = listdir(f"{self.folder}/{validator_name}/keystores")
                    for keystore in keystores:
                        with open(
                            f"{self.folder}/{validator_name}/keystores/{keystore}"
                        ) as f:
                            data = f.readline()
                            validator_keystores.append(data)
                except FileNotFoundError:
                    continue

                for keystore_str in validator_keystores:
                    keystore = json.loads(keystore_str)
                    password = self.get_or_create_keystore_password(validator_name)
                    private_key = ScryptKeystore.from_json(keystore).decrypt(password)
                    public_key = G2ProofOfPossession.SkToPk(
                        int.from_bytes(private_key, byteorder="big")
                    )
                    if public_key in public_keys:
                        raise click.ClickException(
                            f"Public key {Web3.toHex(public_key)} is presented in multiple keystores"
                        )

                    public_keys.add(public_key)
                    if Web3.toBytes(hexstr=keystore["pubkey"]) != public_key:
                        raise click.ClickException(
                            f"Failed to verify keystore for validator {validator_name}"
                        )

    def check_mnemonic(self) -> None:
        """Checks whether the mnemonic is correct."""
        if not self.local_current_state:
            return

        public_key1 = next(iter(self.local_current_state))
        local_keystore = self.local_current_state[public_key1]
        keystore = ScryptKeystore.from_json(json.loads(local_keystore["keystore"]))

        from_index = int(keystore.path.split("/")[3])

        signing_key = get_mnemonic_signing_key(
            mnemonic=self.mnemonic, from_index=from_index
        )
        public_key2 = Web3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))

        if public_key1 != public_key2:
            raise click.ClickException(
                "The local keys does not belong to the provided mnemonic."
            )
