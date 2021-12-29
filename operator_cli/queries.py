from eth2deposit.settings import MAINNET
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from operator_cli.settings import (
    ETHEREUM_GOERLI_SUBGRAPH_URL,
    ETHEREUM_MAINNET_SUBGRAPH_URL,
    STAKEWISE_GOERLI_SUBGRAPH_URL,
    STAKEWISE_MAINNET_SUBGRAPH_URL,
)


def get_ethereum_gql_client(chain: str) -> Client:
    if chain == MAINNET:
        transport = RequestsHTTPTransport(
            url=ETHEREUM_MAINNET_SUBGRAPH_URL,
            verify=True,
            retries=5,
        )
    else:
        transport = RequestsHTTPTransport(
            url=ETHEREUM_GOERLI_SUBGRAPH_URL,
            verify=True,
            retries=5,
        )
    return Client(transport=transport)


def get_stakewise_gql_client(chain: str) -> Client:
    if chain == MAINNET:
        transport = RequestsHTTPTransport(
            url=STAKEWISE_MAINNET_SUBGRAPH_URL,
            verify=True,
            retries=5,
        )
    else:
        transport = RequestsHTTPTransport(
            url=STAKEWISE_GOERLI_SUBGRAPH_URL,
            verify=True,
            retries=5,
        )
    return Client(transport=transport)


REGISTRATIONS_QUERY = gql(
    """
    query getValidatorRegistrations($public_keys: [Bytes!]) {
      validatorRegistrations(
        where: { publicKey_in: $public_keys }
      ) {
        publicKey
      }
    }
"""
)

OPERATOR_QUERY = gql(
    """
    query getOperators($address: ID) {
      operators(
        where: { id: $address }
      ) {
        id
      }
    }
"""
)

OPERATORS_QUERY = gql(
    """
    query getOperators {
      operators {
        id
        depositDataMerkleProofs
      }
    }
"""
)

VALIDATORS_QUERY = gql(
    """
    query getValidators($public_key: ID) {
      validators(where: { id: $public_key }) {
        operator {
          id
        }
      }
    }
"""
)
