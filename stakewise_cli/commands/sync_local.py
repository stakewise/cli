import os

import click
from eth_typing import ChecksumAddress

from stakewise_cli.eth2 import validate_mnemonic
from stakewise_cli.networks import AVAILABLE_NETWORKS, MAINNET
from stakewise_cli.storages.local import LocalStorage
from stakewise_cli.validators import validate_operator_address


@click.command(help="Synchronizes validator keystores to the local folder")
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
@click.option(
    "--folder",
    default=os.path.join(os.getcwd(), "validator_keys"),
    help="The folder where validator keys will be saved.",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
def sync_local(network: str, operator: ChecksumAddress, folder: str) -> None:
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
