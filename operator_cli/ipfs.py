import json
from typing import Any, List

import backoff
import click
import ipfshttpclient
import requests

from operator_cli.settings import (
    IPFS_FETCH_ENDPOINTS,
    IPFS_PIN_ENDPOINTS,
    IPFS_PINATA_API_KEY,
    IPFS_PINATA_PIN_ENDPOINT,
    IPFS_PINATA_SECRET_KEY,
)
from operator_cli.typings import MerkleDepositData


def add_ipfs_prefix(ipfs_id: str) -> str:
    if ipfs_id.startswith("ipfs://"):
        ipfs_id = ipfs_id[len("ipfs://") :]

    if not ipfs_id.startswith("/ipfs/"):
        ipfs_id = "/ipfs/" + ipfs_id

    return ipfs_id


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def upload_deposit_data_to_ipfs(deposit_datum: List[MerkleDepositData]) -> str:
    """Submits deposit datum to the IPFS and pins the file."""
    ipfs_ids = []
    for pin_endpoint in IPFS_PIN_ENDPOINTS:
        try:
            with ipfshttpclient.connect(pin_endpoint) as client:
                ipfs_id = client.add_json(deposit_datum)
                client.pin.add(ipfs_id)
                ipfs_ids.append(ipfs_id)
        except Exception as e:
            click.echo(e)
            click.echo(f"Failed to submit deposit data to {pin_endpoint}")

    if IPFS_PINATA_API_KEY and IPFS_PINATA_SECRET_KEY:
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
            ipfs_id = response.json()["IpfsHash"]
            ipfs_ids.append(ipfs_id)
        except Exception as e:  # noqa: E722
            click.echo(e)
            click.echo("Failed to submit deposit data to Pinata")

    if not ipfs_ids:
        raise click.ClickException("Failed to submit claims to IPFS")

    ipfs_ids = set(map(add_ipfs_prefix, ipfs_ids))
    if len(ipfs_ids) != 1:
        raise click.ClickException(f"Received different ipfs IDs: {','.join(ipfs_ids)}")

    return ipfs_ids.pop()


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def ipfs_fetch(ipfs_id: str) -> Any:
    """Fetches data from IPFS."""
    ipfs_id = ipfs_id.replace("ipfs://", "").replace("/ipfs/", "")
    for ipfs_endpoint in IPFS_PIN_ENDPOINTS:
        try:
            with ipfshttpclient.connect(ipfs_endpoint) as client:
                return client.get_json(ipfs_id)
        except:  # noqa: E722
            pass

    for endpoint in IPFS_FETCH_ENDPOINTS:
        try:
            response = requests.get(f"{endpoint.rstrip('/')}/ipfs/{ipfs_id}")
            response.raise_for_status()
            return response.json()
        except:  # noqa: E722
            pass

    raise click.ClickException(f"Failed to fetch IPFS data at {ipfs_id}")
