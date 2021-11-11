import json
from typing import Any, Dict, List

import backoff
import click
import ipfshttpclient
import requests

from operator_cli.settings import (
    IPFS_ENDPOINT,
    IPFS_PINATA_API_KEY,
    IPFS_PINATA_PIN_ENDPOINT,
    IPFS_PINATA_SECRET_KEY,
)
from operator_cli.typings import MerkleDepositData


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def upload_deposit_datum(deposit_datum: List[MerkleDepositData]) -> str:
    """Submits deposit datum to the IPFS and pins the file."""
    try:
        with ipfshttpclient.connect(IPFS_ENDPOINT) as client:
            ipfs_id1 = client.add_json(deposit_datum)
            client.pin.add(ipfs_id1)
    except:  # noqa: E722
        click.echo(f"Failed to submit deposit data to ${IPFS_ENDPOINT}")
        ipfs_id1 = None

    if not (IPFS_PINATA_API_KEY and IPFS_PINATA_SECRET_KEY):
        if not ipfs_id1:
            raise click.ClickException("Failed to submit deposit data to IPFS")
        return ipfs_id1

    headers = {
        "pinata_api_key": IPFS_PINATA_API_KEY,
        "pinata_secret_api_key": IPFS_PINATA_SECRET_KEY,
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            headers=headers,
            url=IPFS_PINATA_PIN_ENDPOINT,
            data=json.dumps({"pinataContent": deposit_datum}, sort_keys=True),
        )
        response.raise_for_status()
        ipfs_id2 = response.json()["IpfsHash"]
    except:  # noqa: E722
        click.echo("Failed to submit deposit data to Pinata")
        ipfs_id2 = None

    if not (ipfs_id1 or ipfs_id2):
        raise click.ClickException("Failed to submit deposit data to IPFS")

    if ipfs_id1 and not ipfs_id1.startswith("/ipfs/"):
        ipfs_id1 = "/ipfs/" + ipfs_id1

    if ipfs_id2 and not ipfs_id2.startswith("/ipfs/"):
        ipfs_id2 = "/ipfs/" + ipfs_id2

    if (ipfs_id1 and ipfs_id2) and not ipfs_id1 == ipfs_id2:
        raise click.ClickException(
            f"Received different ipfs IDs: {ipfs_id1}, {ipfs_id2}"
        )

    return ipfs_id1


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def get_operator_deposit_datum(ipfs_id: str) -> List[Dict[Any, Any]]:
    """Fetches the deposit datum of the operator."""
    ipfs_id = ipfs_id.replace("ipfs://", "").replace("/ipfs/", "")
    with ipfshttpclient.connect(IPFS_ENDPOINT) as client:
        return client.get_json(ipfs_id)
