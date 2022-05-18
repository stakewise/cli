from typing import Dict, List, Union

import backoff
import click
from eth_typing import ChecksumAddress, HexStr
from eth_utils import is_address, to_checksum_address
from gql import Client as GqlClient
from web3 import Web3

from stakewise_cli.contracts import get_ens_node_id, get_ens_resolver, get_web3_client
from stakewise_cli.ipfs import ipfs_fetch
from stakewise_cli.networks import GNOSIS_CHAIN, MAINNET, NETWORKS
from stakewise_cli.queries import (
    BLOCK_TIMESTAMP_QUERY,
    OPERATOR_QUERY,
    REFERRALS_QUERY,
    REGISTRATIONS_QUERY,
    VALIDATORS_QUERY,
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


@backoff.on_exception(backoff.expo, Exception, max_time=30)
def get_referrals(
    gql_client: GqlClient, from_block: int, to_block: int
) -> Dict[ChecksumAddress, int]:
    """Fetches referrals fee from graph"""
    last_id = ""
    result: Dict = gql_client.execute(
        document=REFERRALS_QUERY,
        variable_values=dict(from_block=from_block, to_block=to_block, last_id=last_id),
    )
    referrals_chunk = result.get("referrals", [])
    referrals = referrals_chunk

    # accumulate chunks
    while len(referrals_chunk) >= 1000:
        last_id = referrals_chunk[-1]["id"]
        result: Dict = gql_client.execute(
            document=REFERRALS_QUERY,
            variable_values=dict(
                from_block=from_block, to_block=to_block, last_id=last_id
            ),
        )
        referrals_chunk = result.get("referrals", [])
        referrals.extend(referrals_chunk)

    return referrals


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def get_operators_committee(network: str) -> List[List[str]]:
    """Fetches committee config from the DAO's ENS text record."""
    # XXX: ENS does not support gnosis chain
    if network == GNOSIS_CHAIN:
        network = MAINNET

    w3 = get_web3_client(network)
    ens_resolver = get_ens_resolver(network, w3)

    # fetch IPFS URL
    node_id = get_ens_node_id(NETWORKS[network]["DAO_ENS_NAME"])
    ens_text_record = NETWORKS[network]["OPERATORS_COMMITTEE_ENS_KEY"]

    # TODO: remove once committee approved by DAO to mainnet ENS record
    if network == MAINNET:
        committee_config_url = "ipfs://QmVp3QMpKCrnSwACzWVJbNrVQYAZSRwoNNWh7c4XcHb1St"
    else:
        committee_config_url = ens_resolver.functions.text(
            node_id, ens_text_record
        ).call(block_identifier="latest")

    return ipfs_fetch(committee_config_url)


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def get_operator_allocation_id(gql_client: GqlClient, operator: ChecksumAddress) -> int:
    """Fetches next operator allocation ID"""
    result: Dict = gql_client.execute(
        document=OPERATOR_QUERY,
        variable_values=dict(address=operator.lower()),
    )
    operators = result["operators"]
    if not operators:
        return 1

    return int(operators[0]["allocationsCount"]) + 1


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
        document=REGISTRATIONS_QUERY,
        variable_values=dict(public_keys=[public_key]),
    )
    validators = result["validatorRegistrations"]
    return bool(validators)


@backoff.on_exception(backoff.expo, Exception, max_time=1)
def get_block_timestamp(gql_client: GqlClient, block_number: int) -> bool:
    """Checks whether validator is registered."""
    result: Dict = gql_client.execute(
        document=BLOCK_TIMESTAMP_QUERY,
        variable_values=dict(block_number=block_number),
    )
    blocks = result["blocks"]
    if not blocks:
        return

    return int(blocks[0]["timestamp"])


def validate_operator_address(value):
    try:
        if is_address(value):
            return to_checksum_address(value)
    except ValueError:
        pass

    raise click.BadParameter("Invalid Ethereum address")


def generate_specification(
    merkle_root: HexStr, ipfs_url: str, gql_client: GqlClient, operator: ChecksumAddress
) -> str:
    specification = f"""
## Specification

- DAO calls `addOperator` function of `PoolValidators` contract with the following parameters:
    * operator: `{operator}`
    * depositDataMerkleRoot: `{merkle_root}`
    * depositDataMerkleProofs: `{ipfs_url}`
"""

    operator_is_registered = check_operator_exists(gql_client, operator)
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
