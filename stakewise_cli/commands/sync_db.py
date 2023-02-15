import os
import json

from typing import Dict

import click
import glob
from eth_typing import ChecksumAddress, HexStr

from stakewise_cli.eth2 import prompt_beacon_client, validate_mnemonic
from stakewise_cli.networks import AVAILABLE_NETWORKS, MAINNET
from stakewise_cli.storages.database import Database, check_db_connection
from stakewise_cli.transfers import decrypt_transferred_keys
from stakewise_cli.validators import validate_db_uri, validate_operator_address
from stakewise_cli.web3signer import Web3SignerManager

from staking_deposit.key_handling.keystore import Keystore

@click.command(help="Synchronizes validator keystores in the database for web3signer")
@click.option(
    "--operator",
    help="The operator wallet address specified during deposit data generation.",
    prompt="Enter your operator wallet address",
    callback=validate_operator_address,
)
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
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
def sync_db(
    operator: ChecksumAddress,
    db_url: str,
    validator_capacity: int,
    private_keys_dir: str,
) -> None:
    # check_db_connection(db_url)

    # beacon_client = prompt_beacon_client(network)

    # mnemonic = click.prompt(
    #     'Enter your mnemonic separated by spaces (" ")',
    #     value_proc=validate_mnemonic,
    #     type=click.STRING,
    # )
    decrypt_key = click.prompt(
        'Enter the password to decrypt validators private keys',
        type=click.STRING,
        hide_input=True
    )
    # click.clear()

    # web3signer = Web3SignerManager(
    #     operator=operator,
    #     network=MAINNET,
    #     # mnemonic=mnemonic,
    #     validator_capacity=validator_capacity,
    #     # beacon=beacon_client,
    # )
    # database = Database(
    #     db_url=db_url,
    # )

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

            quit()

        keypairs[keystore.pubkey] = int.from_bytes(secret_bytes, 'big')

    click.confirm(
        f"Found {len(keypairs)} key pairs, apply changes to the database?",
        default=True,
        abort=True,
    )
    
    # keys = web3signer.keys
    # if private_keys_dir and decrypt_key:
    #     
    #     transferred_keypairs = decrypt_transferred_keys(
    #         keys_dir=private_keys_dir, decrypt_key=decrypt_key
    #     )
    #     keys.extend(web3signer.process_transferred_keypairs(transferred_keypairs))
    #     click.confirm(
    #         f"Synced {len(transferred_keypairs)} transferred key pairs, apply changes to the database?",
    #         default=True,
    #         abort=True,
    #     )
        
    # database.update_keys(keys=keys)

    click.secho(
        f"The database contains {len(keypairs)} validator keys.\n"
        # f"Please upgrade the 'validators' helm chart with 'validatorsCount' set to {web3signer.validators_count}\n"
        # f"Set 'DECRYPTION_KEY' env to '{private_key}'",
        bold=True,
        fg="green",
    )
