import os
from typing import Dict

from decouple import config
from eth2deposit.settings import (
    MAINNET,
    PRATER,
    BaseChainSetting,
    MainnetSetting,
    PraterSetting,
)

# supported networks
SUPPORTED_CHAINS: Dict[str, BaseChainSetting] = {
    MAINNET: MainnetSetting,
    PRATER: PraterSetting,
}

OUTPUT_DIR = config("OUTPUT_DIR", default=os.path.join(os.getcwd(), "output"))

WITHDRAWAL_CREDENTIALS = config(
    "WITHDRAWAL_CREDENTIALS",
    default="0x0100000000000000000000002296e122c1a20fca3cac3371357bdad3be0df079",
)
IPFS_ENDPOINT = config("IPFS_ENDPOINT", default="/dns/ipfs.infura.io/tcp/5001/https")

# extra pins to pinata for redundancy
IPFS_PINATA_PIN_ENDPOINT = config(
    "IPFS_PINATA_ENDPOINT", default="https://api.pinata.cloud/pinning/pinJSONToIPFS"
)
IPFS_PINATA_API_KEY = config("IPFS_PINATA_API_KEY", default="")
IPFS_PINATA_SECRET_KEY = config(
    "IPFS_PINATA_SECRET_KEY",
    default="",
)

VAULT_VALIDATORS_MOUNT_POINT = config(
    "VAULT_VALIDATORS_MOUNT_POINT", default="validators"
)
VALIDATORS_NAMESPACE = config("VALIDATORS_NAMESPACE", default="validators")

ETHEREUM_MAINNET_SUBGRAPH_URL = config(
    "ETHEREUM_MAINNET_SUBGRAPH_URL",
    default="https://api.thegraph.com/subgraphs/name/stakewise/ethereum-mainnet",
)
ETHEREUM_GOERLI_SUBGRAPH_URL = config(
    "ETHEREUM_GOERLI_SUBGRAPH_URL",
    default="https://api.thegraph.com/subgraphs/name/stakewise/ethereum-goerli",
)

STAKEWISE_MAINNET_SUBGRAPH_URL = config(
    "ETHEREUM_MAINNET_SUBGRAPH_URL",
    default="https://api.thegraph.com/subgraphs/name/stakewise/stakewise-mainnet",
)
STAKEWISE_GOERLI_SUBGRAPH_URL = config(
    "ETHEREUM_GOERLI_SUBGRAPH_URL",
    default="https://api.thegraph.com/subgraphs/name/stakewise/stakewise-goerli",
)

# The legacy key derivation path will be used and new vault will be populated with 1000 keys.
# Skip this flag in case you are not migrating from the legacy system.
MIGRATE_LEGACY = config("MIGRATE_LEGACY", cast=bool, default=False)
