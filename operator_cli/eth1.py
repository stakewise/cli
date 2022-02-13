from typing import Dict, Union

import backoff
import click
from eth_typing import ChecksumAddress, HexStr
from eth_utils import is_address, to_checksum_address
from gql import Client as GqlClient
from web3 import Web3

from operator_cli.queries import (
    OPERATOR_QUERY,
    VALIDATORS_QUERY,
    get_stakewise_gql_client,
)


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def check_operator_exists(gql_client: GqlClient, operator: ChecksumAddress) -> bool:
    """Checks whether address has an operator role."""

    result: Dict = gql_client.execute(
        document=OPERATOR_QUERY,
        variable_values=dict(address=operator.lower()),
    )
    operators_count = len(result["operators"])
    assert operators_count in (0, 1)
    return operators_count == 1


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def get_operator_deposit_data_ipfs_link(
    gql_client: GqlClient,
    operator: ChecksumAddress,
) -> Union[str, None]:
    """Fetches deposit data of the operator."""
    result: Dict = gql_client.execute(
        document=OPERATOR_QUERY,
        variable_values=dict(address=operator.lower()),
    )
    operators = result["operators"]
    if not operators:
        return None
    return operators[0]["depositDataMerkleProofs"]


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def get_validator_operator_address(
    gql_client: GqlClient, public_key: HexStr
) -> Union[ChecksumAddress, None]:
    """Fetches operator address of the validator. If such does not exist returns `None`."""
    result: Dict = gql_client.execute(
        document=VALIDATORS_QUERY,
        variable_values=dict(public_key=public_key),
    )
    validators = result["validators"]
    if not validators:
        return None

    return Web3.toChecksumAddress(validators[0]["operator"]["id"])


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


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def is_validator_registered(gql_client: GqlClient, public_key: HexStr) -> bool:
    """Checks whether validator is registered."""
    result: Dict = gql_client.execute(
        document=VALIDATORS_QUERY,
        variable_values=dict(public_key=public_key),
    )
    validators = result["validators"]
    return bool(validators)


def validate_operator_address(value):
    try:
        if is_address(value):
            return to_checksum_address(value)
    except ValueError:
        pass

    raise click.BadParameter("Invalid Ethereum address")


def generate_specification(network: str, merkle_root: HexStr, ipfs_url: str) -> str:
    operator = click.prompt(
        "Enter the wallet address that will receive rewards."
        " If you already run StakeWise validators, please re-use the same wallet address",
        value_proc=validate_operator_address,
    )

    specification = f"""
    ## Specification

    - DAO calls `addOperator` function of `PoolValidators` contract with the following parameters:
        * operator: `{operator}`
        * depositDataMerkleRoot: `{merkle_root}`
        * depositDataMerkleProofs: `{ipfs_url}`
    """

    stakewise_gql_client = get_stakewise_gql_client(network)
    operator_is_registered = check_operator_exists(stakewise_gql_client, operator)
    if not operator_is_registered:
        share_percentage = click.prompt(
            "Enter the % of the rewards you would like to receive from the protocol fees",
            default=50.00,
            value_proc=validate_share_percentage,
        )
        if share_percentage > 0:
            specification += f"""

    - DAO calls `setOperator` function of `Roles` contract with the following parameters:
        * account: `{operator}`
        * revenueShare: `{share_percentage}`
    """

    specification += f"""

    - If the proposal will be approved, the operator must perform the following steps:
        * Call `operator-cli sync-vault` or `operator-cli sync-local` with the same mnemonic as used for generating the proposal
        * Create or update validators and make sure the new keys are added
        * Call `commitOperator` from the `{operator}` address
    """

    return specification
