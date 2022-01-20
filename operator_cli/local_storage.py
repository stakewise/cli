import collections
import errno
import json
import time
from functools import cached_property, lru_cache
from os import listdir, makedirs
from os.path import exists
from typing import Dict, OrderedDict, Set, Union

import click
from eth2deposit.key_handling.keystore import ScryptKeystore
from eth_typing import ChecksumAddress, HexStr
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
        self.folder = folder

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
    def generate_keystores(self) -> LocalState:
        """
        Returns ordered mapping of BLS public key to private key
        that are in deposit data or active but are missing in the local.
        """

        missed_keypairs: OrderedDict[HexStr, SigningKey] = collections.OrderedDict()
        from_index = 0
        while True:
            signing_key = get_mnemonic_signing_key(self.mnemonic, from_index)
            public_key = Web3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))

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

        new_state: Dict[str, int] = collections.Counter([])

        # distribute missing keypairs across validators
        with click.progressbar(
            missed_keypairs,
            label="Provisioning missing validator keys\t\t",
            show_percent=False,
            show_pos=True,
        ) as missing_keypairs:
            for public_key in missing_keypairs:
                validator_name = "validator"
                signing_key = missed_keypairs[public_key]
                secret = signing_key.key.to_bytes(32, "big")
                password = self.get_or_create_keystore_password()
                keystore = ScryptKeystore.encrypt(
                    secret=secret, password=password, path=signing_key.path
                ).as_json()
                new_state[public_key] = LocalKeystore(
                    validator_name=validator_name, keystore=keystore
                )

        return new_state

    @lru_cache
    def get_or_create_keystore_password(self) -> str:
        """Retrieves validator keystore password if exists or creates a new one."""
        try:
            with open(f"{self.folder}/password/password.txt") as file:
                password = file.readline()
        except FileNotFoundError:
            password = generate_password()
            makedirs(f"{self.folder}/password", exist_ok=True)
            with open(f"{self.folder}/password/password.txt", "w") as file:
                file.write(password)

        return password

    def apply_local_changes(self) -> None:
        """Updates local from current state to new state."""

        if exists(self.folder):
            if len(listdir(self.folder)) > 1:
                raise click.ClickException(f"{self.folder} already exist and not empty")
        else:
            try:
                makedirs(self.folder)
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise e

        # sync keystores
        self.sync_local_keystores()

    def sync_local_keystores(self) -> None:
        """Synchronizes local keystores."""
        validators_keystores: Dict[str, Dict[str, str]] = {}
        for public_key, local_keystore in self.generate_keystores.items():
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
                    makedirs(f"{self.folder}/keystores", exist_ok=True)
                    with open(f"{self.folder}/keystores/{name}", "w") as file:
                        file.write(keystore)
