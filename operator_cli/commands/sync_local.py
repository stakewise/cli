import click
import os
from eth2deposit.settings import MAINNET
from requests.exceptions import ConnectionError, HTTPError

from operator_cli.eth2 import get_beacon_client, validate_mnemonic
from operator_cli.local_storage import LocalStorage
from operator_cli.settings import SUPPORTED_CHAINS


@click.command(help="Synchronizes validator keystores to the local folder")
@click.option(
    "--chain",
    default=MAINNET,
    help="The network of ETH2 you are targeting.",
    prompt="Choose the (mainnet or testnet) network/chain name",
    type=click.Choice(SUPPORTED_CHAINS.keys(), case_sensitive=False),
)
def sync_local(chain: str) -> None:
    while True:
        try:
            beacon_client = get_beacon_client()
            beacon_client.get_genesis()
            break
        except (ConnectionError, HTTPError):
            pass

        click.echo("Error: failed to connect to the ETH2 server with provided URL")

    mnemonic = click.prompt(
        'Enter your mnemonic separated by spaces (" ")',
        value_proc=validate_mnemonic,
        type=click.STRING,
    )

    folder = click.prompt(
        "The folder to place the generated keystores and passwords in",
        default=os.path.join(os.getcwd(), "validator_keys"),
        type=click.STRING,
    )

    click.clear()
    click.confirm(
        "I confirm that this mnemonic is used only in one staking setup",
        abort=True,
    )

    local_storage = LocalStorage(
        beacon=beacon_client,
        chain=chain,
        mnemonic=mnemonic,
        folder=folder,
    )

    local_storage.apply_local_changes()
