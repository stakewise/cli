from os import getcwd
from os.path import join
from pathlib import Path
from typing import Dict, List, Tuple

import click
from eth_typing import HexStr
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3

from stakewise_cli.committee_shares import rsa_encrypt
from stakewise_cli.eth1 import is_validator_registered
from stakewise_cli.eth2 import get_mnemonic_signing_key, validate_mnemonic
from stakewise_cli.migration_keys import MIGRATION_KEYS
from stakewise_cli.networks import AVAILABLE_NETWORKS, MAINNET
from stakewise_cli.queries import get_ethereum_gql_client
from stakewise_cli.settings import IS_LEGACY
from stakewise_cli.typings import SigningKey


@click.command(help="Export registered private keys from the mnemonic")
@click.option(
    "--network",
    default=MAINNET,
    help="The network of ETH2 you are targeting.",
    prompt="Please choose the network name",
    type=click.Choice(
        AVAILABLE_NETWORKS,
        case_sensitive=False,
    ),
)
@click.option(
    "--output-dir",
    default=join(getcwd(), "exported_keys"),
    help="The folder where private keys will be saved.",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
def export_validator_keys(network: str, output_dir: str) -> None:
    mnemonic = click.prompt(
        'Enter your mnemonic separated by spaces (" ")',
        value_proc=validate_mnemonic,
        type=click.STRING,
    )

    eth_gql_client = get_ethereum_gql_client(network)

    click.secho(
        "Processing registered validators...\n",
        fg="green",
    )
    keypairs: List[Tuple[HexStr, SigningKey]] = []
    index = 0
    while True:
        signing_key = get_mnemonic_signing_key(mnemonic, index, IS_LEGACY)
        public_key = Web3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))

        is_registered = is_validator_registered(
            gql_client=eth_gql_client, public_key=public_key
        )
        if not is_registered:
            break

        keypairs.append((public_key, signing_key))
        index += 1

        if not (index % 100):
            click.clear()
            click.secho(f"Exported {index} key pairs...", bold=True)

    if not keypairs:
        raise click.ClickException("No registered validators private keys")

    migration_keys: Dict = MIGRATION_KEYS.get(network, {})

    total_validators_count = sum(
        [migration_key["validators_count"] for migration_key in migration_keys.values()]
    )
    if len(keypairs) != total_validators_count:
        raise click.ClickException(
            f"Not enough keys to distribute:"
            f" expected={len(keypairs)}, actual={total_validators_count}"
        )

    index = 0
    for operator_name, migration_key in migration_keys.items():
        validators_count = migration_key["validators_count"]
        key_folder = Path(output_dir) / network / operator_name
        key_folder.mkdir(parents=True, exist_ok=True)

        with click.progressbar(
            length=validators_count,
            label=f"Encrypting private keys for {operator_name}\t\t",
            show_percent=False,
            show_pos=True,
        ) as bar:
            for (public_key, signing_key) in keypairs[index : index + validators_count]:
                secret = str(signing_key.key)
                enc_session_key, nonce, tag, ciphertext = rsa_encrypt(
                    recipient_public_key=migration_key["public_key"],
                    data=secret,
                )
                with open(key_folder / f"{public_key}.enc", "wb") as f:
                    for data in (enc_session_key, nonce, tag, ciphertext):
                        f.write(data)
                bar.update(1)
        index = index + validators_count

    click.secho(
        f"Exported {total_validators_count} encrypted private keys to {output_dir} folder.\n",
        bold=True,
        fg="green",
    )
