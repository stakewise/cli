import click
from eth_typing import BLSPubkey
from web3 import Web3

from stakewise_cli.committee_shares import reconstruct_shared_bls_public_key
from stakewise_cli.ipfs import ipfs_fetch


@click.command(help="Verifies public keys for operator shards")
@click.option(
    "--deposit-data-ipfs-hash",
    help="IPFS hash for operator deposit data to verify.",
    prompt="Enter IPFS hash for operator deposit data to verify",
)
@click.option(
    "--shards-count",
    help="Total number of shards to verify. With 5 committee members, the number must be at least 3.",
    prompt="Enter total number of shards to verify",
    type=int,
)
def verify_shard_pubkeys(deposit_data_ipfs_hash: str, shards_count: int) -> None:
    submitted = 0
    shards = {}
    while True:
        if submitted == shards_count:
            break

        index = click.prompt(
            text=(
                "Enter committee member position number "
                "(index in stakewise.eth ENS record)"
            ),
            type=click.INT,
        )
        if index in shards:
            click.echo("The IPFS hash for such index was already submitted")
            continue

        public_keys_ipfs_hash = click.prompt(
            text=(
                f"Enter the shard public keys IPFS hash for {index} committee member"
                f" ({submitted + 1}/{shards_count})"
            ),
            type=click.STRING,
        ).strip()

        try:
            pub_keys = ipfs_fetch(public_keys_ipfs_hash)
            shards[index] = [Web3.toBytes(hexstr=k) for k in pub_keys]
        except:  # noqa: E722
            click.secho(
                f"Failed to fetch IPFS data at {public_keys_ipfs_hash}. Please try again.",
                fg="red",
            )
            continue

        submitted += 1

    try:
        deposit_data = ipfs_fetch(deposit_data_ipfs_hash)
        deposit_data_pub_keys = [
            Web3.toBytes(hexstr=d["public_key"]) for d in deposit_data
        ]
    except:  # noqa: E722
        raise click.ClickException(
            f"Failed to fetch IPFS data at {deposit_data_ipfs_hash}. Please try again."
        )

    with click.progressbar(
        enumerate(deposit_data_pub_keys),
        label="Reconstructing public keys from shards\t\t",
        show_percent=False,
        show_pos=True,
    ) as _deposit_data_pub_keys:
        for i, pub_key in _deposit_data_pub_keys:
            pub_key_shards = {}
            for committee_index in shards:
                pub_key_shards[committee_index] = BLSPubkey(shards[committee_index][i])

            reconstructed_pub_key = reconstruct_shared_bls_public_key(pub_key_shards)
            if reconstructed_pub_key != pub_key:
                raise click.ClickException(
                    f"Failed to reconstruct public key with index {i}"
                )

    click.secho("Successfully verified operator shards", fg="green")
