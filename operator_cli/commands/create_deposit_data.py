import click

from operator_cli.eth1 import generate_specification
from operator_cli.eth2 import (
    LANGUAGES,
    VALIDATOR_DEPOSIT_AMOUNT,
    create_new_mnemonic,
    generate_merkle_deposit_datum,
    generate_unused_validator_keys,
    validate_mnemonic,
)
from operator_cli.ipfs import upload_deposit_data_to_ipfs
from operator_cli.networks import (
    ETHEREUM_GOERLI,
    ETHEREUM_MAINNET,
    GNOSIS_CHAIN,
    NETWORKS,
)
from operator_cli.queries import get_ethereum_gql_client


@click.command(help="Creates deposit data and generates a forum post specification")
@click.option(
    "--network",
    default=ETHEREUM_MAINNET,
    help="The network to generate the deposit data for",
    prompt="Enter the network name",
    type=click.Choice(
        [ETHEREUM_MAINNET, ETHEREUM_GOERLI, GNOSIS_CHAIN], case_sensitive=False
    ),
)
@click.option(
    "--existing-mnemonic",
    is_flag=True,
    help="Indicates whether the deposit data is generated for the existing mnemonic.",
)
def create_deposit_data(network: str, existing_mnemonic: bool) -> None:
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

    # TODO: Generate and save exit signatures

    # 3. Upload deposit data to IPFS
    ipfs_url = upload_deposit_data_to_ipfs(deposit_data)
    click.clear()

    # 4. Generate proposal specification part
    specification = generate_specification(network, deposit_data_merkle_root, ipfs_url)
    click.clear()
    click.secho(
        "Submit the post to https://forum.stakewise.io with the following specification section:",
        bold=True,
        fg="green",
    )
    click.echo(specification)
