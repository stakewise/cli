from base64 import b64encode
from functools import cached_property
from typing import List, Set
from urllib.parse import urlparse

import click
import psycopg2
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from eth_typing import ChecksumAddress, HexStr
from eth_utils import add_0x_prefix
from psycopg2.extras import execute_values
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3

from stakewise_cli.eth1 import get_operator_deposit_data_ipfs_link
from stakewise_cli.eth2 import get_mnemonic_signing_key
from stakewise_cli.ipfs import ipfs_fetch
from stakewise_cli.networks import NETWORKS
from stakewise_cli.queries import get_stakewise_gql_client
from stakewise_cli.settings import IS_LEGACY
from stakewise_cli.typings import DatabaseKeyRecord

CIPHER_KEY_LENGTH = 32


class Database:
    def __init__(
        self,
        db_url: str,
        operator: ChecksumAddress,
        network: str,
        mnemonic: str,
    ):
        self.db_url = db_url
        self.sw_gql_client = get_stakewise_gql_client(network)
        self.network = network
        self.mnemonic = mnemonic
        self.max_keys_per_validator = NETWORKS[network]["MAX_KEYS_PER_VALIDATOR"]
        self.operator_address = operator

    @cached_property
    def cipher_key(self) -> bytes:
        return get_random_bytes(CIPHER_KEY_LENGTH)

    @cached_property
    def cipher_key_str(self) -> str:
        return b64encode(self.cipher_key).decode("ascii")

    @cached_property
    def keys(self) -> List[DatabaseKeyRecord]:
        """
        Returns prepared database key records that are in the latest deposit data.
        """
        keystores: List[DatabaseKeyRecord] = []
        keys_count = len(self.operator_deposit_data_public_keys)
        index = 0

        with click.progressbar(
            length=keys_count,
            label="Syncing key pairs\t\t",
            show_percent=False,
            show_pos=True,
        ) as bar:
            while index < keys_count:
                private_key = get_mnemonic_signing_key(self.mnemonic, index, IS_LEGACY)
                public_key = Web3.toHex(G2ProofOfPossession.SkToPk(private_key.key))

                public_key = add_0x_prefix(public_key)

                if public_key not in self.operator_deposit_data_public_keys:
                    index += 1
                    continue

                data = bytes(str(private_key), "ascii")
                cipher = self.generate_cipher()
                encrypted_private_key = cipher.encrypt(data)
                keystores.append(
                    DatabaseKeyRecord(
                        public_key=public_key,
                        private_key=self._bytes_to_str(encrypted_private_key),
                        nonce=self._bytes_to_str(cipher.nonce),
                        validator_index=index // self.max_keys_per_validator,
                    )
                )
                index += 1

                bar.update(1)
        return keystores

    @cached_property
    def validators_count(self) -> int:
        return len(self.keys) // self.max_keys_per_validator

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

    def apply_changes(self) -> None:
        """Updates database records to new state."""
        self.init_db()
        self.save_to_db()

    def init_db(self) -> None:
        conn = get_db_connection(self.db_url)
        cur = conn.cursor()
        cur.execute(
            """
            DROP TABLE IF EXISTS keys;
            CREATE TABLE keys (
                public_key TEXT UNIQUE NOT NULL,
                private_key TEXT UNIQUE NOT NULL,
                nonce TEXT NOT NULL,
                validator_index TEXT NOT NULL)
            ;"""
        )

        conn.commit()
        cur.close()
        conn.close()

    def save_to_db(self) -> None:
        conn = get_db_connection(self.db_url)
        cur = conn.cursor()
        execute_values(
            cur,
            "INSERT INTO keys (public_key, private_key, nonce, validator_index) VALUES %s",
            [
                (x["public_key"], x["private_key"], x["nonce"], x["validator_index"])
                for x in self.keys
            ],
        )
        conn.commit()
        cur.close()
        conn.close()

    def generate_cipher(self) -> AES.MODE_EAX:
        return AES.new(self.cipher_key, AES.MODE_EAX)

    def _bytes_to_str(self, value: bytes) -> str:
        return b64encode(value).decode("ascii")


def get_db_connection(db_url):
    result = urlparse(db_url)
    return psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
    )
