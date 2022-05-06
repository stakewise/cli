from os import getcwd
from os.path import join

import click

from stakewise_cli.committee_shares import create_committee_shares
from stakewise_cli.eth1 import generate_specification, validate_operator_address
from stakewise_cli.eth2 import (
    LANGUAGES,
    VALIDATOR_DEPOSIT_AMOUNT,
    create_new_mnemonic,
    generate_merkle_deposit_datum,
    generate_unused_validator_keys,
    validate_mnemonic,
)
from stakewise_cli.ipfs import upload_to_ipfs
from stakewise_cli.networks import GNOSIS_CHAIN, GOERLI, MAINNET, NETWORKS, PERM_GOERLI
from stakewise_cli.queries import get_ethereum_gql_client, get_stakewise_gql_client


@click.command(help="Creates deposit data and generates a forum post specification")
@click.option(
    "--network",
    default=MAINNET,
    help="The network to generate the deposit data for",
    prompt="Enter the network name",
    type=click.Choice(
        [MAINNET, GOERLI, PERM_GOERLI, GNOSIS_CHAIN], case_sensitive=False
    ),
)
@click.option(
    "--existing-mnemonic",
    is_flag=True,
    help="Indicates whether the deposit data is generated for the existing mnemonic.",
)
@click.option(
    "--committee-folder",
    default=join(getcwd(), "committee"),
    help="The folder where committee files will be saved.",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
def create_deposit_data(
    network: str, existing_mnemonic: bool, committee_folder: str
) -> None:
    if not existing_mnemonic:
        language = click.prompt(
            "Choose your mnemonic language",
            default="english",
            type=click.Choice(LANGUAGES, case_sensitive=False),
        )
        mnemonic = create_new_mnemonic(language)
    else:
        mnemonic = click.prompt(
            'Enter your mnemonic separated by spaces (" ")',
            value_proc=validate_mnemonic,
            type=click.STRING,
        )

    keys_count = click.prompt(
        "Enter the number of new validator keys you would like to generate",
        type=click.IntRange(1, 1000000),
    )

    # 1. Generate unused validator keys
    ethereum_gql_client = get_ethereum_gql_client(network)
    keypairs = generate_unused_validator_keys(
        gql_client=ethereum_gql_client, mnemonic=mnemonic, keys_count=keys_count
    )

    # 2. Generate and save deposit data
    (deposit_data_merkle_root, deposit_data,) = generate_merkle_deposit_datum(
        genesis_fork_version=NETWORKS[network]["GENESIS_FORK_VERSION"],
        withdrawal_credentials=NETWORKS[network]["WITHDRAWAL_CREDENTIALS"],
        deposit_amount=VALIDATOR_DEPOSIT_AMOUNT,
        loading_label="Creating deposit data:\t\t",
        validator_keypairs=keypairs,
    )

    # 3. Assign operator wallet address
    operator = click.prompt(
        "Enter the wallet address that will receive rewards."
        " If you already run StakeWise validators, please re-use the same wallet address",
        value_proc=validate_operator_address,
    )

    # 4. Generate private key shares for the committee
    sw_gql_client = get_stakewise_gql_client(network)
    if network != PERM_GOERLI:
        # no private key shares form permissioned network
        committee_paths = create_committee_shares(
            network=network,
            gql_client=sw_gql_client,
            operator=operator,
            committee_folder=committee_folder,
            keypairs=keypairs,
        )

    # 5. Upload deposit data to IPFS
    ipfs_url = upload_to_ipfs(deposit_data)

    # 6. Generate proposal specification part
    specification = generate_specification(
        merkle_root=deposit_data_merkle_root,
        ipfs_url=ipfs_url,
        gql_client=sw_gql_client,
        operator=operator,
    )
    click.clear()
    click.secho(
        "Submit the post to https://forum.stakewise.io with the following specification section:",
        bold=True,
        fg="green",
    )
    click.echo(specification)

    # 7. Generate committee message
    if network != PERM_GOERLI:
        # no private key shares form permissioned network
        click.secho(
            "Share the encrypted validator key shares with the committee members through Telegram:",
            bold=True,
            fg="green",
        )
        # noinspection PyUnboundLocalVariable
        for username, path in committee_paths.items():
            click.echo(f"- @{username}: {path}")
