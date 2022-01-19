import click
from eth2deposit.settings import MAINNET
from hvac import Client as VaultClient
from hvac.exceptions import InvalidRequest
from requests.exceptions import ConnectionError, HTTPError

from operator_cli.eth2 import validate_mnemonic, get_beacon_client
from operator_cli.settings import SUPPORTED_CHAINS, VAULT_VALIDATORS_MOUNT_POINT
from operator_cli.vault import Vault


def get_vault_client() -> VaultClient:
    token = click.prompt("Please enter the vault token", type=click.STRING)
    url = click.prompt("Please enter the vault URL", type=click.STRING)
    return VaultClient(url=url, token=token)


def get_kubernetes_api_server() -> str:
    url = click.prompt(
        "Please enter host string, a host:port pair, or a URL to the base of the Kubernetes API server",
        type=click.STRING,
    )
    return url


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

    vault_client.secrets.kv.default_kv_version = 1
    try:
        vault_client.sys.enable_secrets_engine(
            backend_type="kv",
            path=VAULT_VALIDATORS_MOUNT_POINT,
        )
    except InvalidRequest:
        pass

    try:
        vault_client.sys.enable_auth_method("kubernetes")
    except InvalidRequest:
        pass

    while True:
        try:
            response = vault_client.auth.kubernetes.configure(
                kubernetes_host=get_kubernetes_api_server()
            )
            response.raise_for_status()
            break
        except:  # noqa: E722
            pass

        click.echo("Error: failed to connect to the Kubernetes API host")

    namespace = click.prompt(
        "Enter the validators kubernetes namespace",
        default="validators",
        type=click.STRING,
    )
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

    vault = Vault(
        vault_client=vault_client,
        beacon=beacon_client,
        chain=chain,
        mnemonic=mnemonic,
        namespace=namespace,
    )

    vault.apply_vault_changes()
    vault.verify_vault_keystores()
    click.echo(
        f"Make sure you have the following validators"
        f" running in the {namespace} namespace: {','.join(sorted(vault.vault_validator_names))}."
        f" Restart them if they were updated."
    )
