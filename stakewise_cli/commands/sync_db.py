import click
from eth_typing import ChecksumAddress
from requests.exceptions import ConnectionError, HTTPError
from web3 import Web3

from stakewise_cli.eth2 import get_beacon_client, validate_mnemonic
from stakewise_cli.networks import (
    GNOSIS_CHAIN,
    GOERLI,
    HARBOUR_GOERLI,
    HARBOUR_MAINNET,
    MAINNET,
    NETWORKS,
)
from stakewise_cli.storages.database import Database, check_db_connection
from stakewise_cli.validators import validate_db_uri, validate_operator_address
from stakewise_cli.web3signer import Web3SignerManager


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
@click.option(
    "--validator-capacity",
    help="Keys count per validator.",
    prompt="Enter keys count per validator",
    type=int,
    default=100,
)
def sync_db(
    network: str, operator: ChecksumAddress, db_url: str, validator_capacity: int
) -> None:
    check_db_connection(db_url)

    while True:
        try:
            beacon_client = get_beacon_client(network)
            genesis = beacon_client.get_genesis()
            if genesis["data"]["genesis_fork_version"] != Web3.toHex(
                NETWORKS[network]["GENESIS_FORK_VERSION"]
            ):
                click.secho(
                    "Error: invalid beacon node network",
                    bold=True,
                    fg="red",
                )
                continue
            break
        except (ConnectionError, HTTPError):
            pass

        click.secho(
            "Error: failed to connect to the ETH2 server with provided URL",
            bold=True,
            fg="red",
        )

    mnemonic = click.prompt(
        'Enter your mnemonic separated by spaces (" ")',
        value_proc=validate_mnemonic,
        type=click.STRING,
    )
    click.clear()

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

    click.confirm(
        f"Synced {len(web3signer.keys)} key pairs, apply changes to the database?",
        default=True,
        abort=True,
    )
    database.update_keys(keys=web3signer.keys)

    click.secho(
        f"The database contains {len(web3signer.keys)} validator keys.\n"
        f"Please upgrade the 'validators' helm chart with 'validatorsCount' set to {web3signer.validators_count}\n"
        f"Set 'DECRYPTION_KEY' env to '{web3signer.encoder.cipher_key_str}'",
        bold=True,
        fg="green",
    )
