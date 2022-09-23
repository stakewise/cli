import json
from typing import Any

import backoff
import click
import ipfshttpclient
import requests

from stakewise_cli.settings import (
    INFURA_IPFS_CLIENT_ENDPOINT,
    INFURA_IPFS_CLIENT_PASSWORD,
    INFURA_IPFS_CLIENT_USERNAME,
    IPFS_EXTRA_FETCH_ENDPOINTS,
    IPFS_PINATA_API_KEY,
    IPFS_PINATA_PIN_ENDPOINT,
    IPFS_PINATA_SECRET_KEY,
    LOCAL_IPFS_CLIENT_ENDPOINT,
)


def add_ipfs_prefix(ipfs_id: str) -> str:
    if ipfs_id.startswith("ipfs://"):
        ipfs_id = ipfs_id[len("ipfs://") :]

    if not ipfs_id.startswith("/ipfs/"):
        ipfs_id = "/ipfs/" + ipfs_id

    return ipfs_id


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def upload_to_ipfs(data: Any) -> str:
    """Submits data to IPFS."""
    ipfs_ids = []
    try:
        with ipfshttpclient.connect(
            INFURA_IPFS_CLIENT_ENDPOINT,
            username=INFURA_IPFS_CLIENT_USERNAME,
            password=INFURA_IPFS_CLIENT_PASSWORD,
        ) as client:
            ipfs_id = client.add_json(data)
            client.pin.add(ipfs_id)
            ipfs_ids.append(ipfs_id)
    except Exception as e:
        click.echo(e)
        click.echo(f"Failed to submit data to {INFURA_IPFS_CLIENT_ENDPOINT}")

    if LOCAL_IPFS_CLIENT_ENDPOINT:
        try:
            with ipfshttpclient.connect(LOCAL_IPFS_CLIENT_ENDPOINT) as client:
                ipfs_id = client.add_json(data)
                client.pin.add(ipfs_id)
                ipfs_ids.append(ipfs_id)
        except Exception as e:
            click.echo(e)
            click.echo(f"Failed to submit data to {LOCAL_IPFS_CLIENT_ENDPOINT}")

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
                data=json.dumps({"pinataContent": data}, sort_keys=True),
            )
            response.raise_for_status()
            ipfs_id = response.json()["IpfsHash"]
            ipfs_ids.append(ipfs_id)
        except Exception as e:  # noqa: E722
            click.echo(e)
            click.echo("Failed to submit data to Pinata")

    if not ipfs_ids:
        raise click.ClickException("Failed to submit data to IPFS")

    ipfs_ids = list(set(map(add_ipfs_prefix, ipfs_ids)))
    if len(ipfs_ids) != 1:
        raise click.ClickException(f"Received different ipfs IDs: {','.join(ipfs_ids)}")

    return ipfs_ids.pop()


@backoff.on_exception(backoff.expo, Exception, max_time=60)
def ipfs_fetch(ipfs_id: str) -> Any:
    """Fetches data from IPFS."""
    ipfs_id = ipfs_id.replace("ipfs://", "").replace("/ipfs/", "")
    try:
        with ipfshttpclient.connect(
            INFURA_IPFS_CLIENT_ENDPOINT,
            username=INFURA_IPFS_CLIENT_USERNAME,
            password=INFURA_IPFS_CLIENT_PASSWORD,
        ) as client:
            return client.get_json(ipfs_id)
    except:  # noqa: E722
        pass

    for endpoint in IPFS_EXTRA_FETCH_ENDPOINTS:
        try:
            response = requests.get(f"{endpoint.rstrip('/')}/ipfs/{ipfs_id}")
            response.raise_for_status()
            return response.json()
        except:  # noqa: E722
            pass

    raise click.ClickException(f"Failed to fetch IPFS data at {ipfs_id}")
