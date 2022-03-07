from decouple import config

MAINNET = "mainnet"
GOERLI = "goerli"
PERM_GOERLI = "perm_goerli"
GNOSIS_CHAIN = "gnosis"

NETWORKS = {
    MAINNET: dict(
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
        ETH1_ENDPOINT=config(
            "ETH1_ENDPOINT",
            default="https://mainnet.infura.io/v3/84842078b09946638c03157f83405213",
        ),
        GENESIS_FORK_VERSION=bytes.fromhex("00000000"),
        MAX_KEYS_PER_VALIDATOR=100,
        DAO_ENS_NAME="stakewise.eth",
        ENS_RESOLVER_CONTRACT_ADDRESS="0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41",
        OPERATORS_COMMITTEE_ENS_KEY="operators_committee",
        IS_POA=False,
    ),
    GOERLI: dict(
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
        ETH1_ENDPOINT=config(
            "ETH1_ENDPOINT",
            default="https://goerli.infura.io/v3/84842078b09946638c03157f83405213",
        ),
        DAO_ENS_NAME="stakewise.eth",
        ENS_RESOLVER_CONTRACT_ADDRESS="0x4B1488B7a6B320d2D721406204aBc3eeAa9AD329",
        OPERATORS_COMMITTEE_ENS_KEY="operators_committee",
        IS_POA=True,
    ),
    PERM_GOERLI: dict(
        STAKEWISE_SUBGRAPH_URL=config(
            "STAKEWISE_SUBGRAPH_URL",
            default="https://api.thegraph.com/subgraphs/name/stakewise/stakewise-perm-goerli",
        ),
        ETHEREUM_SUBGRAPH_URL=config(
            "ETHEREUM_SUBGRAPH_URL",
            default="https://api.thegraph.com/subgraphs/name/stakewise/ethereum-goerli",
        ),
        WITHDRAWAL_CREDENTIALS=config(
            "WITHDRAWAL_CREDENTIALS",
            default="0x0100000000000000000000006dfc9682e3c3263758ad96e2b2ba9822167f81ee",
        ),
        GENESIS_FORK_VERSION=bytes.fromhex("00001020"),
        MAX_KEYS_PER_VALIDATOR=100,
        ETH1_ENDPOINT=config(
            "ETH1_ENDPOINT",
            default="https://goerli.infura.io/v3/84842078b09946638c03157f83405213",
        ),
        DAO_ENS_NAME="",
        ENS_RESOLVER_CONTRACT_ADDRESS="0x4B1488B7a6B320d2D721406204aBc3eeAa9AD329",
        OPERATORS_COMMITTEE_ENS_KEY="",
        IS_POA=True,
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
            default="0x010000000000000000000000fc9b67b6034f6b306ea9bd8ec1baf3efa2490394",
        ),
        GENESIS_FORK_VERSION=bytes.fromhex("00000064"),
        MAX_KEYS_PER_VALIDATOR=500,
        # MAINNET ENS record is used as ENS is not deployed to gnosis chain
        ETH1_ENDPOINT="",
        DAO_ENS_NAME="",
        ENS_RESOLVER_CONTRACT_ADDRESS="",
        OPERATORS_COMMITTEE_ENS_KEY="",
        IS_POA=True,
    ),
}
