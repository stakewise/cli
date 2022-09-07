import click
from eth_typing import ChecksumAddress
from hvac import Client as VaultClient
from hvac.exceptions import InvalidRequest
from requests.exceptions import ConnectionError

from stakewise_cli.eth2 import prompt_beacon_client, validate_mnemonic
from stakewise_cli.networks import AVAILABLE_NETWORKS, MAINNET
from stakewise_cli.settings import VAULT_VALIDATORS_MOUNT_POINT
from stakewise_cli.storages.vault import Vault
from stakewise_cli.validators import validate_operator_address


def get_vault_client() -> VaultClient:
    token = click.prompt("Enter the vault authentication token", type=click.STRING)
    url = click.prompt("Enter the vault API URL", type=click.STRING)
    return VaultClient(url=url, token=token)


def get_kubernetes_api_server() -> str:
    url = click.prompt(
        "Enter the Kubernetes API server URL",
        type=click.STRING,
    )
    return url


@click.command(help="Synchronizes validator keystores in the vault")
@click.option(
    "--network",
    default=MAINNET,
    help="The network of ETH2 you are targeting.",
    prompt="Please choose the network name",
    type=click.Choice(
        AVAILABLE_NETWORKS,
        case_sensitive=False,
    ),
)
@click.option(
    "--operator",
    help="The operator wallet address specified during deposit data generation.",
    prompt="Enter your operator wallet address",
    callback=validate_operator_address,
)
def sync_vault(network: str, operator: ChecksumAddress) -> None:
    while True:
        try:
            vault_client = get_vault_client()
            if vault_client.is_authenticated():
                break
        except ConnectionError:
            pass

        click.secho(
            "Error: failed to connect to the vault server with provided URL and token",
            bold=True,
            fg="red",
        )

    beacon_client = prompt_beacon_client(network)

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

        click.secho(
            "Error: failed to connect to the Kubernetes API host", bold=True, fg="red"
        )

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
    click.secho(
        "NB! Using the same mnemonic for multiple vaults will cause validators slashings!",
        bold=True,
        fg="red",
    )

    vault = Vault(
        vault_client=vault_client,
        beacon=beacon_client,
        operator=operator,
        network=network,
        mnemonic=mnemonic,
        namespace=namespace,
    )

    vault.apply_vault_changes()
    vault.verify_vault_keystores()
    click.secho(
        f"The vault contains {len(vault.vault_new_state)} validator keys."
        f' Please upgrade the "validators" helm chart with "validatorsCount" set to {len(vault.vault_validator_names)}'
        f' and "reimportKeystores" set to "true". Make sure you have the following validators running '
        f'in the "{namespace}" namespace: {",".join(sorted(vault.vault_validator_names))}.',
        bold=True,
        fg="green",
    )
