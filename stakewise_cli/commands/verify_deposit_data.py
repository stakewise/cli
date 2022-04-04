from typing import List, Set

import click
from eth_typing import BLSPubkey, BLSSignature, HexStr
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3

from stakewise_cli.eth2 import get_deposit_data_roots, get_registered_public_keys
from stakewise_cli.ipfs import ipfs_fetch
from stakewise_cli.merkle_tree import MerkleTree
from stakewise_cli.networks import GNOSIS_CHAIN, GOERLI, MAINNET, NETWORKS, PERM_GOERLI
from stakewise_cli.queries import get_ethereum_gql_client
from stakewise_cli.typings import Bytes32, Gwei

w3 = Web3()

deposit_amount = Web3.toWei(32, "ether")
deposit_amount_gwei = Gwei(int(w3.fromWei(deposit_amount, "gwei")))


@click.command(help="Verify deposit data")
@click.option(
    "--network",
    default=MAINNET,
    help="The network deposit data was generated for.",
    prompt="Please choose the network name",
    type=click.Choice(
        [MAINNET, GOERLI, PERM_GOERLI, GNOSIS_CHAIN], case_sensitive=False
    ),
)
@click.option(
    "--ipfs-hash",
    help="The IPFS hash with the deposit data",
    prompt="Enter the IPFS hash of the file with the deposit data",
)
@click.option(
    "--merkle-root",
    help="The expected merkle root of the deposit data",
    prompt="Enter the expected merkle root of the deposit data",
)
@click.option(
    "--keys-count",
    help="The expected number of keys",
    prompt="Enter the expected number of keys in deposit data",
    type=int,
)
def verify_deposit_data(
    network: str, ipfs_hash: str, merkle_root: HexStr, keys_count: int
) -> None:
    withdrawal_credentials = Bytes32(
        Web3.toBytes(hexstr=NETWORKS[network]["WITHDRAWAL_CREDENTIALS"])
    )
    fork_version = NETWORKS[network]["GENESIS_FORK_VERSION"]

    merkle_nodes: List[bytes] = []
    seen_public_keys: Set[HexStr] = set()

    deposit_datum = ipfs_fetch(ipfs_hash)
    with click.progressbar(
        deposit_datum,
        label=f"Verifying deposit data from {ipfs_hash}...\t\t",
        show_percent=False,
        show_pos=True,
    ) as deposit_datum:
        for deposit_data in deposit_datum:
            signature = deposit_data["signature"]
            deposit_data_root = deposit_data["deposit_data_root"]
            public_key = deposit_data["public_key"]
            if public_key in seen_public_keys:
                raise click.ClickException(f"Public key {public_key} is repeated")

            # verify deposit data root
            expected_signing_root, expected_deposit_data_root = get_deposit_data_roots(
                public_key=BLSPubkey(Web3.toBytes(hexstr=public_key)),
                withdrawal_credentials=withdrawal_credentials,
                signature=BLSSignature(Web3.toBytes(hexstr=signature)),
                amount=deposit_amount_gwei,
                fork_version=fork_version,
            )
            if expected_deposit_data_root != Web3.toBytes(hexstr=deposit_data_root):
                raise click.ClickException(
                    f"Invalid deposit data root for public key {public_key}"
                )

            if (
                G2ProofOfPossession.Verify(public_key, expected_signing_root, signature)
                == expected_deposit_data_root
            ):
                raise click.ClickException(
                    f"Invalid deposit data root for public key {public_key}"
                )

            seen_public_keys.add(public_key)
            encoded_data: bytes = w3.codec.encode_abi(
                ["bytes", "bytes32", "bytes", "bytes32"],
                [public_key, withdrawal_credentials, signature, deposit_data_root],
            )
            merkle_nodes.append(w3.keccak(primitive=encoded_data))

    # check registered public keys in beacon chain
    registered_pub_keys = get_registered_public_keys(
        gql_client=get_ethereum_gql_client(network),
        seen_public_keys=list(seen_public_keys),
    )

    if len(registered_pub_keys) == len(seen_public_keys):
        raise click.ClickException(
            "All the deposit data public keys are already registered"
        )
    elif registered_pub_keys:
        click.secho(
            f"The deposit data has {len(registered_pub_keys)} out of {len(seen_public_keys)}"
            f" public keys already registered",
            bold=True,
            fg="blue",
        )

    # check proofs
    merkle_tree = MerkleTree(merkle_nodes)
    for i, deposit_data in enumerate(deposit_datum):
        proof: List[HexStr] = merkle_tree.get_hex_proof(merkle_nodes[i])
        if proof != deposit_data["proof"]:
            raise click.ClickException(
                f"Invalid deposit data proof for public key {public_key}"
            )

    if merkle_tree.get_hex_root() != merkle_root:
        raise click.ClickException(
            f"Merkle roots does not match:"
            f" expected={merkle_root},"
            f" actual={merkle_tree.get_hex_root()}"
        )

    if keys_count != len(seen_public_keys):
        raise click.ClickException(
            f"Invalid number of keys: expected={keys_count}, actual={len(seen_public_keys)}"
        )

    click.secho(
        f"The deposit data from {ipfs_hash} has been successfully verified",
        bold=True,
        fg="green",
    )
