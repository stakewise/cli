import errno
import time
from functools import cached_property, lru_cache
from os import listdir, makedirs
from os.path import exists
from typing import Dict, Set

import click
from eth_typing import ChecksumAddress, HexStr
from py_ecc.bls import G2ProofOfPossession
from staking_deposit.key_handling.keystore import ScryptKeystore
from web3 import Web3

from stakewise_cli.eth1 import (
    get_operator_deposit_data_ipfs_link,
    is_validator_registered,
)
from stakewise_cli.eth2 import generate_password, get_mnemonic_signing_key
from stakewise_cli.ipfs import ipfs_fetch
from stakewise_cli.queries import get_stakewise_gql_client


class LocalStorage(object):
    def __init__(
        self,
        dst_folder: str,
        operator: ChecksumAddress,
        network: str,
        mnemonic: str,
    ):
        self.dst_folder = dst_folder
        self.sw_gql_client = get_stakewise_gql_client(network)
        self.mnemonic = mnemonic
        self.operator_address = operator

    @cached_property
    def operator_deposit_data_public_keys(self) -> Set[HexStr]:
        """Returns operator's deposit data public keys."""
        deposit_data_ipfs_link = get_operator_deposit_data_ipfs_link(
            self.sw_gql_client, self.operator_address
        )
        result: Set[HexStr] = set()
        if not deposit_data_ipfs_link:
            return result

        deposit_datum = ipfs_fetch(deposit_data_ipfs_link)
        for deposit_data in deposit_datum:
            public_key = deposit_data["public_key"]
            if public_key in result:
                raise click.ClickException(
                    f"Public key {public_key} is presented twice in {deposit_data_ipfs_link}"
                )
            result.add(public_key)

        return result

    @cached_property
    def deposit_data_keystores(self) -> Dict[str, str]:
        """
        Returns mapping of keystore name to string-encoded keystore file
        that are in the latest deposit data.
        """
        keystores: Dict[str, str] = {}
        keys_count = len(self.operator_deposit_data_public_keys)
        if not keys_count:
            return keystores

        from_index = 0
        with click.progressbar(
            length=keys_count,
            label="Syncing deposit data keystores\t\t",
            show_percent=False,
            show_pos=True,
        ) as bar:
            while True:
                signing_key = get_mnemonic_signing_key(self.mnemonic, from_index)
                public_key = Web3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))
                if public_key not in self.operator_deposit_data_public_keys:
                    break

                is_registered = is_validator_registered(
                    gql_client=self.sw_gql_client, public_key=public_key
                )
                if is_registered:
                    click.secho(
                        f"Public key {public_key} is in deposit data and already in use, skipping...",
                        bold=True,
                        fg="red",
                    )
                    bar.update(1)
                    continue

                secret = signing_key.key.to_bytes(32, "big")
                password = self.get_or_create_keystore_password()
                keystore = ScryptKeystore.encrypt(
                    secret=secret, password=password, path=signing_key.path
                ).as_json()
                keystore_name = "keystore-%s-%i.json" % (
                    signing_key.path.replace("/", "_"),
                    time.time(),
                )
                keystores[keystore_name] = keystore
                from_index += 1
                bar.update(1)

        return keystores

    @lru_cache
    def get_or_create_keystore_password(self) -> str:
        """Retrieves validator keystore password if exists or creates a new one."""
        try:
            with open(f"{self.dst_folder}/password/password.txt") as file:
                password = file.readline()
        except FileNotFoundError:
            password = generate_password()
            makedirs(f"{self.dst_folder}/password", exist_ok=True)
            with open(f"{self.dst_folder}/password/password.txt", "w") as file:
                file.write(password)

        return password

    def apply_local_changes(self) -> None:
        """Updates local from current state to new state."""

        if exists(self.dst_folder) and len(listdir(self.dst_folder)) > 1:
            raise click.ClickException(f"{self.dst_folder} must be empty")

        try:
            makedirs(self.dst_folder)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise e

        # sync keystores
        self.save_local_keystores()

    def save_local_keystores(self) -> None:
        """Saves latest deposit data keystores to local folder."""
        if not self.deposit_data_keystores:
            return

        makedirs(f"{self.dst_folder}/keystores", exist_ok=True)
        with click.progressbar(
            self.deposit_data_keystores.items(),
            label="Saving keystores\t\t",
            show_percent=False,
            show_pos=True,
        ) as keystores:
            for name, keystore in keystores:
                with open(f"{self.dst_folder}/keystores/{name}", "w") as file:
                    file.write(keystore)
