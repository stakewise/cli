import json
from os import listdir
from os.path import basename, isfile, join
from typing import Dict, List, Set, Tuple

import click
from eth_typing import BLSPubkey, BLSSignature, HexStr
from eth_utils import add_0x_prefix
from gql import Client
from web3 import Web3

from operator_cli.eth1 import generate_specification
from operator_cli.eth2 import verify_deposit_data
from operator_cli.ipfs import upload_deposit_data_to_ipfs
from operator_cli.merkle_tree import MerkleTree
from operator_cli.networks import (
    ETHEREUM_GOERLI,
    ETHEREUM_MAINNET,
    GNOSIS_CHAIN,
    NETWORKS,
)
from operator_cli.queries import REGISTRATIONS_QUERY, get_ethereum_gql_client
from operator_cli.typings import Bytes4, Bytes32, Gwei, MerkleDepositData

w3 = Web3()

deposit_amount = Web3.toWei(32, "ether")
deposit_amount_gwei = Gwei(int(w3.fromWei(deposit_amount, "gwei")))


def process_deposit_data(
    deposit_data: dict, withdrawal_credentials: HexStr, fork_version: Bytes4
) -> Tuple[bytes, MerkleDepositData]:
    public_key = deposit_data["pubkey"]
    signature = deposit_data["signature"]
    deposit_data_root = deposit_data["deposit_data_root"]
    is_correct = verify_deposit_data(
        signature=BLSSignature(Web3.toBytes(hexstr=signature)),
        public_key=BLSPubkey(Web3.toBytes(hexstr=public_key)),
        withdrawal_credentials=Bytes32(Web3.toBytes(hexstr=withdrawal_credentials)),
        amount=deposit_amount_gwei,
        hash_tree_root=Bytes32(Web3.toBytes(hexstr=deposit_data_root)),
        fork_version=fork_version,
    )
    if not is_correct:
        raise click.ClickException(f"Invalid deposit data for public key: {public_key}")

    merkle_deposit_data = MerkleDepositData(
        public_key=w3.toHex(hexstr=public_key),
        signature=w3.toHex(hexstr=signature),
        amount=str(deposit_amount),
        withdrawal_credentials=withdrawal_credentials,
        deposit_data_root=w3.toHex(hexstr=deposit_data_root),
        proof=[],
    )
    encoded_data: bytes = w3.codec.encode_abi(
        ["bytes", "bytes32", "bytes", "bytes32"],
        [
            public_key,
            withdrawal_credentials,
            signature,
            deposit_data_root,
        ],
    )
    return w3.keccak(primitive=encoded_data), merkle_deposit_data


def process_file(
    file_path: str,
    merkle_nodes: List[bytes],
    merkle_deposit_datum: List[MerkleDepositData],
    seen_public_keys: Set[HexStr],
    withdrawal_credentials: HexStr,
    fork_version: Bytes4,
):
    with open(file_path, "r") as f:
        deposit_data = json.load(f)

    if isinstance(deposit_data, dict):
        click.echo(f"Processing {basename(file_path)} file...")
        public_key = deposit_data["pubkey"]
        if public_key in seen_public_keys:
            raise click.ClickException(
                f"Public key {deposit_data['pubkey']} is repeated"
            )
        seen_public_keys.add(public_key)

        merkle_node, merkle_deposit_data = process_deposit_data(
            deposit_data=deposit_data,
            withdrawal_credentials=withdrawal_credentials,
            fork_version=fork_version,
        )
        merkle_nodes.append(merkle_node)
        merkle_deposit_datum.append(merkle_deposit_data)
    elif isinstance(deposit_data, list):
        with click.progressbar(
            deposit_data,
            label=f"Processing {basename(file_path)} file...\t\t",
            show_percent=False,
            show_pos=True,
        ) as deposit_datum:
            for _deposit_data in deposit_datum:
                public_key = _deposit_data["pubkey"]
                if public_key in seen_public_keys:
                    raise click.ClickException(f"Public key {public_key} is repeated")
                seen_public_keys.add(public_key)

                merkle_node, merkle_deposit_data = process_deposit_data(
                    deposit_data=_deposit_data,
                    withdrawal_credentials=withdrawal_credentials,
                    fork_version=fork_version,
                )
                merkle_nodes.append(merkle_node)
                merkle_deposit_datum.append(merkle_deposit_data)


def check_public_keys_not_registered(
    gql_client: Client, seen_public_keys: List[HexStr]
) -> None:
    keys_count = len(seen_public_keys)
    verified_public_keys: List[HexStr] = []
    with click.progressbar(
        length=keys_count,
        label="Verifying validators are not registered...\t\t",
        show_percent=False,
        show_pos=True,
    ) as bar:
        from_index = 0
        while len(verified_public_keys) < keys_count:
            curr_progress = len(verified_public_keys)
            chunk_size = min(100, keys_count - curr_progress)

            # verify keys in chunks
            public_keys_chunk: List[HexStr] = []
            while len(public_keys_chunk) != chunk_size:
                public_key = add_0x_prefix(HexStr(seen_public_keys[from_index].lower()))
                verified_public_keys.append(public_key)
                public_keys_chunk.append(public_key)
                from_index += 1

            # check keys are not registered in beacon chain
            result: Dict = gql_client.execute(
                document=REGISTRATIONS_QUERY,
                variable_values=dict(public_keys=public_keys_chunk),
            )
            registrations = result["validatorRegistrations"]
            registered_keys = ",".join(r["publicKey"] for r in registrations)
            if registered_keys:
                raise click.ClickException(
                    f"Public keys already registered in beacon chain: {registered_keys}"
                )

            bar.update(len(verified_public_keys) - curr_progress)


@click.command(
    help="Uploads deposit data to IPFS and generates a forum post specification"
)
@click.option(
    "--network",
    default=ETHEREUM_MAINNET,
    help="The network of ETH2 you are targeting.",
    prompt="Please choose the network name",
    type=click.Choice(
        [ETHEREUM_MAINNET, ETHEREUM_GOERLI, GNOSIS_CHAIN], case_sensitive=False
    ),
)
@click.option(
    "--path",
    help="The folder or file path from where to read deposit data",
    prompt="Enter the folder or file path with deposit data",
    type=click.Path(exists=True, file_okay=True, dir_okay=True),
)
def upload_deposit_data(network: str, path: str) -> None:
    withdrawal_credentials = NETWORKS[network]["WITHDRAWAL_CREDENTIALS"]
    fork_version = NETWORKS[network]["GENESIS_FORK_VERSION"]

    merkle_nodes: List[bytes] = []
    merkle_deposit_datum: List[MerkleDepositData] = []
    seen_public_keys: Set[HexStr] = set()

    if isfile(path):
        process_file(
            file_path=path,
            merkle_nodes=merkle_nodes,
            merkle_deposit_datum=merkle_deposit_datum,
            seen_public_keys=seen_public_keys,
            withdrawal_credentials=withdrawal_credentials,
            fork_version=fork_version,
        )
    else:
        for file in listdir(path):
            file_path = join(path, file)
            if not isfile(file_path):
                click.secho(f"Skipping {file} as it is not a file", fg="red", bold=True)
                continue

            process_file(
                file_path=file_path,
                merkle_nodes=merkle_nodes,
                merkle_deposit_datum=merkle_deposit_datum,
                seen_public_keys=seen_public_keys,
                withdrawal_credentials=withdrawal_credentials,
                fork_version=fork_version,
            )

    click.secho(
        f"Extracted {len(merkle_nodes)} deposit data entries", fg="green", bold=True
    )
    merkle_tree = MerkleTree(merkle_nodes)

    # check whether public keys are not registered in beacon chain
    check_public_keys_not_registered(
        gql_client=get_ethereum_gql_client(network),
        seen_public_keys=list(seen_public_keys),
    )

    # collect proofs
    for i, merkle_deposit_data in enumerate(merkle_deposit_datum):
        proof: List[HexStr] = merkle_tree.get_hex_proof(merkle_nodes[i])
        merkle_deposit_data["proof"] = proof

    # calculate merkle root
    merkle_root: HexStr = merkle_tree.get_hex_root()

    # upload deposit data to IPFS
    ipfs_url = upload_deposit_data_to_ipfs(merkle_deposit_datum)

    specification = generate_specification(network, merkle_root, ipfs_url)
    click.clear()
    click.secho(
        "Submit the post to https://forum.stakewise.io with the following specification section:",
        bold=True,
        fg="green",
    )
    click.echo(specification)
