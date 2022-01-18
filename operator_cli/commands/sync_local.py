import click
from eth2deposit.settings import MAINNET
from requests.exceptions import ConnectionError, HTTPError
from web3.beacon import Beacon

from operator_cli.eth2 import validate_mnemonic
from operator_cli.settings import SUPPORTED_CHAINS
from operator_cli.local_storage import LocalStorage


def get_beacon_client() -> Beacon:
    url = click.prompt("Please enter the ETH2 node URL", type=click.STRING)
    return Beacon(base_url=url)


@click.command(help="Synchronizes validator keystores in the local storage")
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

    click.clear()
    click.confirm(
        "I confirm that this mnemonic is used only for one vault",
        abort=True,
    )

    local_storage = LocalStorage(
        beacon=beacon_client,
        chain=chain,
        mnemonic=mnemonic,
    )

    local_storage.apply_local_changes()
    local_storage.verify_local_keystores()
