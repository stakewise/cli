import click
from eth2deposit.settings import MAINNET
from hvac import Client as VaultClient
from requests.exceptions import ConnectionError, HTTPError
from web3.beacon import Beacon

from operatorcli.eth2 import validate_mnemonic
from operatorcli.settings import SUPPORTED_CHAINS
from operatorcli.vault import Vault


def get_vault_client() -> VaultClient:
    token = click.prompt("Please enter the vault token", type=click.STRING)
    url = click.prompt("Please enter the vault URL", type=click.STRING)
    return VaultClient(url=url, token=token)


def get_beacon_client() -> Beacon:
    url = click.prompt("Please enter the ETH2 node URL", type=click.STRING)
    return Beacon(base_url=url)


@click.command(help="Synchronizes validator keystores in the vault")
@click.option(
    "--chain",
    default=MAINNET,
    help="The network of ETH2 you are targeting.",
    prompt="Choose the (mainnet or testnet) network/chain name",
    type=click.Choice(SUPPORTED_CHAINS.keys(), case_sensitive=False),
)
def sync_vault(chain: str) -> None:
    while True:
        try:
            vault_client = get_vault_client()
            if vault_client.is_authenticated():
                break
        except ConnectionError:
            pass

        click.echo(
            "Error: failed to connect to the vault server with provided URL and token"
        )

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

    vault = Vault(
        vault_client=vault_client, beacon=beacon_client, chain=chain, mnemonic=mnemonic
    )

    click.confirm(
        "I confirm that provided mnemonic is not used for any other vault",
        abort=True,
    )
    click.confirm(
        "I confirm that only one mnemonic is used for the vault",
        abort=True,
    )

    vault.apply_vault_changes()
    vault.verify_vault_keystores()
