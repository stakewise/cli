import math
from collections import OrderedDict
from functools import cached_property
from typing import Dict, List, Set

import click
from eth_typing import ChecksumAddress, HexStr
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3
from web3.beacon import Beacon

from stakewise_cli.encoder import Encoder
from stakewise_cli.eth1 import (
    get_operator_deposit_data_ipfs_link,
    is_validator_registered,
)
from stakewise_cli.eth2 import EXITED_STATUSES, get_mnemonic_signing_key, get_validators
from stakewise_cli.ipfs import ipfs_fetch
from stakewise_cli.queries import get_ethereum_gql_client, get_stakewise_gql_client
from stakewise_cli.settings import IS_LEGACY
from stakewise_cli.typings import DatabaseKeyRecord, SigningKey
from stakewise_cli.utils import bytes_to_str


class Web3SignerManager:
    def __init__(
        self,
        operator: ChecksumAddress,
        network: str,
        mnemonic: str,
        validator_capacity: int,
        beacon: Beacon,
    ):
        self.sw_gql_client = get_stakewise_gql_client(network)
        self.eth_gql_client = get_ethereum_gql_client(network)
        self.beacon = beacon
        self.network = network
        self.mnemonic = mnemonic
        self.validator_capacity = validator_capacity
        self.operator_address = operator
        self.encoder = Encoder()

    @cached_property
    def keys(self) -> List[DatabaseKeyRecord]:
        """
        Returns prepared database key records from the latest deposit data or already registered.
        """
        public_keys: Dict[HexStr, SigningKey] = OrderedDict()

        index = 0
        click.secho("Syncing key pairs...", bold=True)
        while True:
            signing_key = get_mnemonic_signing_key(self.mnemonic, index, IS_LEGACY)
            public_key = Web3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))
            if public_key not in self.operator_deposit_data_public_keys:
                is_registered = is_validator_registered(
                    gql_client=self.eth_gql_client, public_key=public_key
                )
                if not is_registered:
                    break
            public_keys[public_key] = signing_key
            index += 1
            if not (index % 10):
                click.clear()
                click.secho(f"Synced {index} key pairs...", bold=True)

        self.remove_exited_public_keys(public_keys)

        click.secho("Generating private keys...", bold=True)
        deposit_data_key_records: List[DatabaseKeyRecord] = list()
        index = 0
        for public_key, signing_key in public_keys.items():
            private_key = str(signing_key.key)
            encrypted_private_key, nonce = self.encoder.encrypt(private_key)

            key_record = DatabaseKeyRecord(
                public_key=public_key,
                private_key=bytes_to_str(encrypted_private_key),
                nonce=bytes_to_str(nonce),
                validator_index=index // self.validator_capacity,
            )

            if key_record not in deposit_data_key_records:
                deposit_data_key_records.append(key_record)
                index += 1

        return deposit_data_key_records

    @cached_property
    def validators_count(self) -> int:
        return math.ceil(len(self.keys) / self.validator_capacity)

    @cached_property
    def deposit_data_ipfs_link(self) -> str:
        return get_operator_deposit_data_ipfs_link(
            self.sw_gql_client, self.operator_address
        )

    @cached_property
    def operator_deposit_data_public_keys(self) -> Set[HexStr]:
        """Returns operator's deposit data public keys."""

        result: Set[HexStr] = set()
        if not self.deposit_data_ipfs_link:
            return result

        deposit_datum = ipfs_fetch(self.deposit_data_ipfs_link)
        for deposit_data in deposit_datum:
            public_key = deposit_data["public_key"]
            if public_key in result:
                raise click.ClickException(
                    f"Public key {public_key} is presented twice in {self.deposit_data_ipfs_link}"
                )
            result.add(public_key)

        return result

    def remove_exited_public_keys(self, keys: Dict[HexStr, SigningKey]) -> None:
        """Remove operator's public keys that have been exited."""

        # fetch validators in chunks of 100 keys
        for i in range(0, len(keys), 100):
            validators = get_validators(
                beacon=self.beacon,
                public_keys=list(keys.keys())[i : i + 100],
                state_id="finalized",
            )
            for validator in validators:
                if validator["status"] in EXITED_STATUSES:
                    public_key = validator["validator"]["pubkey"]
                    del keys[public_key]

    def process_transferred_keypairs(
        self, keypairs: Dict[HexStr, int]
    ) -> List[DatabaseKeyRecord]:
        """
        Returns prepared database key records from the transferred private keys.
        """
        key_records: List[DatabaseKeyRecord] = list()
        index = len(self.keys)
        with click.progressbar(
            length=len(keypairs),
            label="Processing transferred key pairs:\t\t",
            show_percent=False,
            show_pos=True,
        ) as bar:
            for public_key, private_key in keypairs.items():
                is_registered = is_validator_registered(
                    gql_client=self.eth_gql_client, public_key=public_key
                )
                if not is_registered:
                    raise click.ClickException(
                        f"Public key {public_key} is not registered"
                    )

                encrypted_private_key, nonce = self.encoder.encrypt(str(private_key))

                key_record = DatabaseKeyRecord(
                    public_key=public_key,
                    private_key=bytes_to_str(encrypted_private_key),
                    nonce=bytes_to_str(nonce),
                    validator_index=index // self.validator_capacity,
                )
                key_records.append(key_record)
                index += 1
                bar.update(1)

        return key_records
