import os

import click
from eth_typing import ChecksumAddress
from eth_utils import is_address, to_checksum_address
from requests.exceptions import ConnectionError, HTTPError
from web3 import Web3

from stakewise_cli.eth2 import get_beacon_client, validate_mnemonic
from stakewise_cli.networks import GNOSIS_CHAIN, GOERLI, MAINNET, NETWORKS, PERM_GOERLI
from stakewise_cli.storages.local import LocalStorage


def validate_operator_address(ctx, param, value):
    try:
        if is_address(value):
            return to_checksum_address(value)
    except ValueError:
        pass

    raise click.BadParameter("Invalid Ethereum address")


@click.command(help="Synchronizes validator keystores to the local folder")
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
@click.option(
    "--folder",
    default=os.path.join(os.getcwd(), "validator_keys"),
    help="The folder where validator keys will be saved.",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
def sync_local(network: str, operator: ChecksumAddress, folder: str) -> None:
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

    local_storage = LocalStorage(
        dst_folder=folder,
        operator=operator,
        network=network,
        mnemonic=mnemonic,
    )

    local_storage.apply_local_changes()
