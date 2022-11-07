from typing import Dict

from .networks import GNOSIS_CHAIN, GOERLI, HARBOUR_GOERLI, HARBOUR_MAINNET, MAINNET
from .typings import MigrationKey

MIGRATION_KEYS: Dict[str, Dict[str, MigrationKey]] = {
    MAINNET: {
        "demo": MigrationKey(
            public_key="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQCnCO/z3trZQTh9PrOS/2//q6U+kzPhCMjkpAcaZJTFwsHbVhZa9Uo+Q1AEG4nipOH6eh4rq5KyMtGQuPEGnWaD8LRudwzXyDWB/8Cyap/11FgVYDStVyg800wV+CAx6L+O0xz4XO5ZaE9BQ9Tq8O7qwjYJGoQmRkhKy+4B/DpgSz8OirXp0cbBhk7+A3RGuYWaJSWOk5dJXgi9xVa/is44ZlLQWgHG10lLeTYy/3lSfEhfXKa6qte6sDAAXjTdJhL9TDURwS/DHPKI2HAg3aSgBUiZH6Ua3gWpbO3+uWDqTYCH7Kis6ImyL7gnLMsgGQ0A3Z5mrrh45VXh5py12oKwF+tqHM1LnYIJe+OKiMR/ktEQwematfBbL56nXTX9yqODsMPg1YCOxdzdTDG04Zl73ONexfUhmWLUFyNtQMT97C2484hqoj+b5Wa8ekRzr12FZQFwfpUrEIseu3rEBnc6armLUIIGi6ChXyLhfBabdSzPZo/PHH28PEczh+0suPl3CsCb5hc3NZi+UVwRDwLtxfluUpN68c7kh7GElqNM0ZBrdkWxKxxikdiTDeN49TjAL7YUtG35lK+ZRRRP6/27SKjoukQAZ116tGh7yFFcBlZ8/zHtF36I2ViPaWooXMutYbMvDMtJJhxD1erpxU8/D+FQvhw2GnAMS9miBT7PWw== example.com",
            validators_count=3,
        )
    },
    HARBOUR_MAINNET: {},
    GOERLI: {},
    HARBOUR_GOERLI: {},
    GNOSIS_CHAIN: {},
}
