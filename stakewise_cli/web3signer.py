import math
from collections import OrderedDict
from functools import cached_property
from typing import Dict, List, Set

import click
from eth_typing import HexStr

from stakewise_cli.encoder import Encoder
from stakewise_cli.typings import DatabaseKeyRecord, SigningKey
from stakewise_cli.utils import bytes_to_str


class Web3SignerManager:
    def __init__(
        self,
        validator_capacity: int,
    ):
        self.validator_capacity = validator_capacity
        self.encoder = Encoder()

    def process_transferred_keypairs(
        self, keypairs: Dict[HexStr, int]
    ) -> List[DatabaseKeyRecord]:
        """
        Returns prepared database key records from the transferred private keys.
        """

        # exited_pubkeys = self.check_exited_public_keys(list(keypairs.keys()))
        # if exited_pubkeys:
        #     raise click.ClickException(
        #         f"Validators with public keys {','.join(exited_pubkeys)} are exited"
        #     )

        key_records: List[DatabaseKeyRecord] = list()
        index = 0

        with click.progressbar(
            length=len(keypairs),
            label="Processing transferred key pairs:\t\t",
            show_percent=False,
            show_pos=True,
        ) as bar:
            for public_key, private_key in keypairs.items():
                # is_registered = is_validator_registered(
                #     gql_client=self.eth_gql_client, public_key=public_key
                # )
                # if not is_registered:
                #     raise click.ClickException(
                #         f"Public key {public_key} is not registered"
                #     )
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
