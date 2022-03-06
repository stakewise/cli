from web3 import Web3
from web3.contract import Contract
from web3.middleware import geth_poa_middleware

from stakewise_cli.networks import NETWORKS


def get_web3_client(network: str) -> Web3:
    """Returns instance of the Web3 client."""
    network_config = NETWORKS[network]
    endpoint = network_config["ETH1_ENDPOINT"]

    # Prefer WS over HTTP
    if endpoint.startswith("ws"):
        w3 = Web3(Web3.WebsocketProvider(endpoint, websocket_timeout=60))
    elif endpoint.startswith("http"):
        w3 = Web3(Web3.HTTPProvider(endpoint))
    else:
        w3 = Web3(Web3.IPCProvider(endpoint))

    if network_config["IS_POA"]:
        w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    return w3


def get_ens_node_id(ens_name: str) -> bytes:
    """Calculates ENS node ID based on the domain name."""
    if not ens_name:
        return b"\0" * 32

    label, _, remainder = ens_name.partition(".")
    return Web3.keccak(primitive=get_ens_node_id(remainder) + Web3.keccak(text=label))


def get_ens_resolver(network: str, w3: Web3) -> Contract:
    return w3.eth.contract(
        abi=[
            {
                "constant": True,
                "inputs": [
                    {"internalType": "bytes32", "name": "node", "type": "bytes32"},
                    {"internalType": "string", "name": "key", "type": "string"},
                ],
                "name": "text",
                "outputs": [{"internalType": "string", "name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function",
            }
        ],
        address=NETWORKS[network]["ENS_RESOLVER_CONTRACT_ADDRESS"],
    )
