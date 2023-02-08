from decouple import Csv, config

# extra pins to pinata for redundancy
LOCAL_IPFS_CLIENT_ENDPOINT = config("LOCAL_IPFS_CLIENT_ENDPOINT", default="")

# infura
INFURA_IPFS_CLIENT_ENDPOINT = config(
    "INFURA_IPFS_CLIENT_ENDPOINT",
    default="/dns/ipfs.infura.io/tcp/5001/https",
)
INFURA_IPFS_CLIENT_USERNAME = config("INFURA_IPFS_CLIENT_USERNAME", default="")
INFURA_IPFS_CLIENT_PASSWORD = config("INFURA_IPFS_CLIENT_PASSWORD", default="")

# pinata
IPFS_PINATA_PIN_ENDPOINT = config(
    "IPFS_PINATA_ENDPOINT", default="https://api.pinata.cloud/pinning/pinJSONToIPFS"
)
IPFS_PINATA_API_KEY = config("IPFS_PINATA_API_KEY", default="")
IPFS_PINATA_SECRET_KEY = config(
    "IPFS_PINATA_SECRET_KEY",
    default="",
)

IPFS_EXTRA_FETCH_ENDPOINTS = config(
    "IPFS_FETCH_ENDPOINTS",
    cast=Csv(),
    default="https://gateway.pinata.cloud,http://cloudflare-ipfs.com,https://ipfs.io",
)

VAULT_VALIDATORS_MOUNT_POINT = config(
    "VAULT_VALIDATORS_MOUNT_POINT", default=""
)

IS_LEGACY = config("IS_LEGACY", default=False, cast=bool)
