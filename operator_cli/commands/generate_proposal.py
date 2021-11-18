import click
from eth2deposit.settings import MAINNET, get_chain_setting
from eth_utils import is_address, to_checksum_address

from operator_cli.eth1 import check_operator_exists
from operator_cli.eth2 import (
    FINALIZE_DEPOSIT_AMOUNT,
    INITIALIZE_DEPOSIT_AMOUNT,
    LANGUAGES,
    create_new_mnemonic,
    generate_merkle_deposit_datum,
    generate_unused_validator_keys,
    validate_mnemonic,
)
from operator_cli.ipfs import upload_deposit_datum
from operator_cli.queries import get_ethereum_gql_client, get_stakewise_gql_client
from operator_cli.settings import SUPPORTED_CHAINS


def validate_operator_address(value):
    try:
        if is_address(value):
            return to_checksum_address(value)
    except ValueError:
        pass

    raise click.BadParameter("Invalid Ethereum address")


def validate_share_percentage(value) -> int:
    try:
        percent = float(value)
        if not (0 <= percent <= 100):
            raise click.BadParameter(
                "Invalid share percentage. Must be between 0 and 100.00"
            )

        if (percent * 100).is_integer():
            return int(percent * 100)
        else:
            raise click.BadParameter("Share percent cannot have more than 2 decimals")
    except ValueError:
        pass

    raise click.BadParameter("Invalid share percentage. Must be between 0 and 100.00")


@click.command(help="Creates deposit data and generates a forum post specification")
@click.option(
    "--chain",
    default=MAINNET,
    help="The network of ETH2 you are targeting.",
    prompt="Choose the (mainnet or testnet) network/chain name",
    type=click.Choice(SUPPORTED_CHAINS.keys(), case_sensitive=False),
)
@click.option(
    "--existing-vault",
    is_flag=True,
    help="Indicates whether the proposal is created for the existing keys vault."
    " For every new keys vault, the new mnemonic must be generated.",
)
def generate_proposal(chain: str, existing_vault: bool) -> None:
    if not existing_vault:
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

    click.confirm(
        "I confirm that this mnemonic will be used only for one vault",
        abort=True,
    )

    keys_count = click.prompt(
        "Enter the number of new validator keys you would like to generate",
        type=click.IntRange(1, 1000000),
    )

    # 1. Generate unused validator keys
    ethereum_gql_client = get_ethereum_gql_client(chain)
    keypairs = generate_unused_validator_keys(
        gql_client=ethereum_gql_client, mnemonic=mnemonic, keys_count=keys_count
    )

    # 2. Generate and save deposit data
    chain_setting = get_chain_setting(chain)
    (
        initialize_merkle_root,
        initialize_merkle_deposit_datum,
    ) = generate_merkle_deposit_datum(
        chain_setting=chain_setting,
        deposit_amount=INITIALIZE_DEPOSIT_AMOUNT,
        loading_label="Creating initialize deposit data:\t\t",
        validator_keypairs=keypairs,
    )
    finalize_merkle_root, finalize_merkle_deposit_datum = generate_merkle_deposit_datum(
        chain_setting=chain_setting,
        deposit_amount=FINALIZE_DEPOSIT_AMOUNT,
        loading_label="Creating finalize deposit data:\t\t",
        validator_keypairs=keypairs,
    )

    # TODO: Generate and save exit signatures

    # 3. Upload deposit data to IPFS
    initialize_ipfs_url = upload_deposit_datum(initialize_merkle_deposit_datum)
    finalize_ipfs_url = upload_deposit_datum(finalize_merkle_deposit_datum)
    click.clear()

    # 4. Generate proposal specification part
    operator = click.prompt(
        "Enter the wallet address that will receive rewards."
        " If you already run StakeWise validators, please re-use the same wallet address",
        value_proc=validate_operator_address,
    )

    specification = f"""
## Specification

- DAO calls `addOperator` function of `PoolValidators` contract with the following parameters:
    * operator: `{operator}`
    * initializeMerkleRoot: `{initialize_merkle_root}`
    * initializeMerkleProofs: `{initialize_ipfs_url}`
    * finalizeMerkleRoot: `{finalize_merkle_root}`
    * finalizeMerkleProofs: `{finalize_ipfs_url}`
"""

    stakewise_gql_client = get_stakewise_gql_client(chain)
    operator_is_registered = check_operator_exists(stakewise_gql_client, operator)
    if not operator_is_registered:
        share_percentage = click.prompt(
            "Enter the % of the rewards you would like to receive from the protocol fees",
            default=50.00,
            value_proc=validate_share_percentage,
        )
        specification += f"""

- DAO calls `setOperator` function of `Roles` contract with the following parameters:
    * account: `{operator}`
    * revenueShare: `{share_percentage}`


- If the proposal will be approved, the operator must perform the following steps:
    * Call `operator-cli sync-vault` with the same mnemonic as used for the proposal
    * Create or update validators and make sure the new keys are added
    * Call `commitOperator` from the `{operator}` address together with 1 ETH collateral
"""
    else:
        specification += f"""

- If the proposal will be approved, the operator must perform the following steps:
    * Call `operator-cli sync-vault` with the same mnemonic as used for generating the proposal
    * Create or update validators and make sure the new keys are added
    * Call `commitOperator` from the `{operator}` address
"""

    click.clear()
    click.echo(
        "Submit the post to https://forum.stakewise.io with the following specification section:"
    )
    click.echo(specification)
