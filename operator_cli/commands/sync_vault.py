import click
from eth_typing import ChecksumAddress
from eth_utils import is_address, to_checksum_address
from hvac import Client as VaultClient
from hvac.exceptions import InvalidRequest
from requests.exceptions import ConnectionError, HTTPError
from web3 import Web3

from operator_cli.eth2 import get_beacon_client, validate_mnemonic
from operator_cli.networks import GNOSIS_CHAIN, GOERLI, MAINNET, NETWORKS, PERM_GOERLI
from operator_cli.settings import VAULT_VALIDATORS_MOUNT_POINT
from operator_cli.storages.vault import Vault


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


def validate_operator_address(ctx, param, value):
    try:
        if is_address(value):
            return to_checksum_address(value)
    except ValueError:
        pass

    raise click.BadParameter("Invalid Ethereum address")


@click.command(help="Synchronizes validator keystores in the vault")
@click.option(
    "--network",
    default=MAINNET,
    help="The network of ETH2 you are targeting.",
    prompt="Please choose the network name",
    type=click.Choice(
        [MAINNET, GOERLI, PERM_GOERLI, GNOSIS_CHAIN], case_sensitive=False
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
