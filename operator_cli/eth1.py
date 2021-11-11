from typing import Dict, Union

import backoff
from eth_typing import ChecksumAddress, HexStr
from gql import Client as GqlClient
from web3 import Web3

from operator_cli.queries import OPERATOR_QUERY, OPERATORS_QUERY, VALIDATORS_QUERY


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def check_operator_exists(gql_client: GqlClient, operator: ChecksumAddress) -> bool:
    """Checks whether address has an operator role."""

    result: Dict = gql_client.execute(
        document=OPERATOR_QUERY,
        variable_values=dict(address=operator.lower()),
    )
    return len(result["operators"]) >= 1


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def get_operators_init_merkle_proofs(
    gql_client: GqlClient,
) -> Dict[ChecksumAddress, str]:
    """Fetches initialize merkle proofs of the operators."""
    result: Dict = gql_client.execute(OPERATORS_QUERY)
    operators = result["operators"]
    init_merkle_proofs = {}
    for operator in operators:
        proofs = operator["initializeMerkleProofs"]
        if proofs:
            init_merkle_proofs[Web3.toChecksumAddress(operator["id"])] = proofs

    return init_merkle_proofs


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


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def is_validator_registered(gql_client: GqlClient, public_key: HexStr) -> bool:
    """Checks whether validator is registered."""
    result: Dict = gql_client.execute(
        document=VALIDATORS_QUERY,
        variable_values=dict(public_key=public_key),
    )
    validators = result["validators"]
    return bool(validators)
