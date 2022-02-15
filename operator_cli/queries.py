from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from operator_cli.networks import NETWORKS


def get_ethereum_gql_client(network: str) -> Client:
    network_config = NETWORKS[network]
    transport = RequestsHTTPTransport(
        url=network_config["ETHEREUM_SUBGRAPH_URL"],
        verify=True,
        retries=5,
    )
    return Client(transport=transport)


def get_stakewise_gql_client(network: str) -> Client:
    network_config = NETWORKS[network]
    transport = RequestsHTTPTransport(
        url=network_config["STAKEWISE_SUBGRAPH_URL"],
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
        depositDataMerkleProofs
        allocationsCount
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
