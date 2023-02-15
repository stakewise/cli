import click
from eth_typing import ChecksumAddress

from stakewise_cli.storages.database import Database, check_db_connection
from stakewise_cli.transfers import decrypt_transferred_keys
from stakewise_cli.validators import validate_db_uri
from stakewise_cli.web3signer import Web3SignerManager


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
@click.option(
    "--decrypt-key",
    help="The file holding the password for the keystore-m files",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def sync_db(
    network: str,
    operator: ChecksumAddress,
    db_url: str,
    validator_capacity: int,
    private_keys_dir: str,
    decrypt_key: str,
) -> None:
    check_db_connection(db_url)

    web3signer = Web3SignerManager(
        operator=operator,
        network=network,
        mnemonic=mnemonic,
        validator_capacity=validator_capacity,
        beacon=beacon_client,
    )
    database = Database(
        db_url=db_url,
    )

    keys = web3signer.keys
    if private_keys_dir and decrypt_key:
        click.secho("Decrypting private keys...", bold=True)
        transferred_keypairs = decrypt_transferred_keys(
            keys_dir=private_keys_dir, decrypt_key=decrypt_key
        )
        keys.extend(web3signer.process_transferred_keypairs(transferred_keypairs))
        click.confirm(
            f"Synced {len(transferred_keypairs)} transferred key pairs, apply changes to the database?",
            default=True,
            abort=True,
        )
    database.update_keys(keys=keys)

    click.secho(
        f"The database contains {len(web3signer.keys)} validator keys.\n"
        f"Please upgrade the 'validators' helm chart with 'validatorsCount' set to {web3signer.validators_count}\n"
        f"Set 'DECRYPTION_KEY' env to '{web3signer.encoder.cipher_key_str}'",
        bold=True,
        fg="green",
    )
