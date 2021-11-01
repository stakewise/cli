from typing import Any, Dict, List

import backoff
import ipfshttpclient

from operator_cli.settings import IPFS_ENDPOINT
from operator_cli.types import MerkleDepositData


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def upload_deposit_datum(deposit_datum: List[MerkleDepositData]) -> str:
    """Submits deposit datum to the IPFS and pins the file."""
    with ipfshttpclient.connect(IPFS_ENDPOINT) as client:
        ipfs_id = client.add_json(deposit_datum)
        client.pin.add(ipfs_id)

    if not ipfs_id.startswith("/ipfs/"):
        ipfs_id = "/ipfs/" + ipfs_id

    return ipfs_id


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def get_operator_deposit_datum(ipfs_id: str) -> List[Dict[Any, Any]]:
    """Fetches the deposit datum of the operator."""
    ipfs_id = ipfs_id.replace("ipfs://", "").replace("/ipfs/", "")
    with ipfshttpclient.connect(IPFS_ENDPOINT) as client:
        return client.get_json(ipfs_id)
