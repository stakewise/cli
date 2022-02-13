from decouple import config

ETHEREUM_MAINNET = "mainnet"
ETHEREUM_GOERLI = "goerli"
GNOSIS_CHAIN = "gnosis"

NETWORKS = {
    ETHEREUM_MAINNET: dict(
        STAKEWISE_SUBGRAPH_URL=config(
            "STAKEWISE_SUBGRAPH_URL",
            default="https://api.thegraph.com/subgraphs/name/stakewise/stakewise-mainnet",
        ),
        ETHEREUM_SUBGRAPH_URL=config(
            "ETHEREUM_SUBGRAPH_URL",
            default="https://api.thegraph.com/subgraphs/name/stakewise/ethereum-mainnet",
        ),
        WITHDRAWAL_CREDENTIALS=config(
            "WITHDRAWAL_CREDENTIALS",
            default="0x0100000000000000000000002296e122c1a20fca3cac3371357bdad3be0df079",
        ),
        GENESIS_FORK_VERSION=bytes.fromhex("00000000"),
        MAX_KEYS_PER_VALIDATOR=100,
    ),
    ETHEREUM_GOERLI: dict(
        STAKEWISE_SUBGRAPH_URL=config(
            "STAKEWISE_SUBGRAPH_URL",
            default="https://api.thegraph.com/subgraphs/name/stakewise/stakewise-goerli",
        ),
        ETHEREUM_SUBGRAPH_URL=config(
            "ETHEREUM_SUBGRAPH_URL",
            default="https://api.thegraph.com/subgraphs/name/stakewise/ethereum-goerli",
        ),
        WITHDRAWAL_CREDENTIALS=config(
            "WITHDRAWAL_CREDENTIALS",
            default="0x010000000000000000000000040f15c6b5bfc5f324ecab5864c38d4e1eef4218",
        ),
        GENESIS_FORK_VERSION=bytes.fromhex("00001020"),
        MAX_KEYS_PER_VALIDATOR=100,
    ),
    GNOSIS_CHAIN: dict(
        STAKEWISE_SUBGRAPH_URL=config(
            "STAKEWISE_SUBGRAPH_URL",
            default="https://api.thegraph.com/subgraphs/name/stakewise/stakewise-gnosis",
        ),
        ETHEREUM_SUBGRAPH_URL=config(
            "ETHEREUM_SUBGRAPH_URL",
            default="https://api.thegraph.com/subgraphs/name/stakewise/ethereum-gnosis",
        ),
        WITHDRAWAL_CREDENTIALS=config(
            "WITHDRAWAL_CREDENTIALS",
            default="",
        ),
        GENESIS_FORK_VERSION="",
        MAX_KEYS_PER_VALIDATOR=1000,
    ),
}
