import re

import click
import psycopg2
from eth_typing import ChecksumAddress
from eth_utils import is_address, to_checksum_address

from stakewise_cli.eth2 import validate_mnemonic
from stakewise_cli.networks import (
    GNOSIS_CHAIN,
    GOERLI,
    HARBOUR_GOERLI,
    HARBOUR_MAINNET,
    MAINNET,
)
from stakewise_cli.storages.database import Database, get_db_connection


def validate_operator_address(ctx, param, value):
    try:
        if is_address(value):
            return to_checksum_address(value)
    except ValueError:
        pass

    raise click.BadParameter("Invalid Ethereum address")


def validate_db_uri(ctx, param, value):
    pattern = re.compile(r".+:\/\/.+:.*@.+\/.+")
    if not pattern.match(value):
        raise click.BadParameter("Invalid database connection string")
    return value


@click.command(help="Synchronizes validator keystores in the database for web3signer")
@click.option(
    "--network",
    default=MAINNET,
    help="The network you are targeting.",
    prompt="Please choose the network name",
    type=click.Choice(
        [MAINNET, GOERLI, HARBOUR_MAINNET, HARBOUR_GOERLI, GNOSIS_CHAIN],
        case_sensitive=False,
    ),
)
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
def sync_db(network: str, operator: ChecksumAddress, db_url: str) -> None:

    # check connection
    connection = get_db_connection(db_url=db_url)
    try:
        cur = connection.cursor()
        cur.execute("SELECT 1")
    except psycopg2.OperationalError as e:
        raise click.ClickException(
            f"Error: failed to connect to the database server with provided URL. Error details: {e}",
        )

    mnemonic = click.prompt(
        'Enter your mnemonic separated by spaces (" ")',
        value_proc=validate_mnemonic,
        type=click.STRING,
        hide_input=True,
    )

    click.clear()
    database = Database(
        db_url=db_url,
        operator=operator,
        network=network,
        mnemonic=mnemonic,
    )

    click.confirm(
        f"Synced {len(database.keys)} key pairs, apply changes to database?",
        default=True,
        abort=True,
    )
    database.apply_changes()

    click.secho(
        f"The database contains {len(database.keys)} validator keys.\n"
        f'Please upgrade the "validators" helm chart with "validatorsCount" set to {database.validators_count}\n'
        f'and "reimportKeystores" set to "true".\n'
        f'Set "decryptionKey" to "{database.cipher_key_str}"',
        bold=True,
        fg="green",
    )
