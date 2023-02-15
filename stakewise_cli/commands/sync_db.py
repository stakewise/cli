import os
from sys import exit
import math

from typing import Dict

import click
import glob
from eth_typing import ChecksumAddress, HexStr

from stakewise_cli.storages.database import Database, check_db_connection
from stakewise_cli.validators import validate_db_uri
from stakewise_cli.web3signer import Web3SignerManager

from staking_deposit.key_handling.keystore import Keystore

@click.command(help="Synchronizes validator keystores in the database for web3signer")
@click.option(
    "--db-url",
    help="The database connection address.",
    prompt="Enter the database connection string, ex. 'postgresql://username:pass@hostname/dbname'",
    callback=validate_db_uri,
)
@click.option(
    "--validator-capacity",
    help="Keys count per validator.",
    prompt="Enter keys count per validator",
    type=int,
    default=100,
)
@click.option(
    "--private-keys-dir",
    help="The folder with private keys.",
    prompt="Enter the folder holding keystore-m files",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
def sync_db(
    db_url: str,
    validator_capacity: int,
    private_keys_dir: str,
) -> None:
    check_db_connection(db_url)

    decrypt_key = click.prompt(
        'Enter the password to decrypt validators private keys',
        type=click.STRING,
        hide_input=True
    )

    web3signer = Web3SignerManager(
        validator_capacity=validator_capacity,
    )

    database = Database(
        db_url=db_url,
    )

    keypairs: Dict[HexStr, int] = dict()

    click.secho("Decrypting private keys...", bold=True)

    for filename in glob.glob(os.path.join(private_keys_dir, "*.json")):
        keystore = Keystore.from_file(filename)

        try:
            secret_bytes = keystore.decrypt(decrypt_key)
        except Exception:
            click.secho(
                f"Unable to decrypt {filename} with the provided password",
                bold=True,
                err=True,
                fg="red"
            )

            exit("Password incorrect")

        keypairs['0x'+keystore.pubkey] = int.from_bytes(secret_bytes, 'big')

    click.confirm(
        f"Found {len(keypairs)} key pairs, apply changes to the database?",
        default=True,
        abort=True,
    )
        
    keys = web3signer.process_transferred_keypairs(keypairs)

    validators_count = math.ceil(len(keypairs) / validator_capacity)

    database.update_keys(keys=keys)

    click.secho(
        f"The database contains {len(keypairs)} validator keys.\n"
        f"Please upgrade the 'validators' helm chart with 'validatorsCount' set to {validators_count}\n"
        f"Set 'DECRYPTION_KEY' env to '{web3signer.encoder.cipher_key_str}'",
        bold=True,
        fg="green",
    )
