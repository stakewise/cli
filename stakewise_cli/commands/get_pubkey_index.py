import click
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3

from stakewise_cli.eth2 import get_mnemonic_signing_key, validate_mnemonic
from stakewise_cli.settings import IS_LEGACY


@click.command(help="Gets index of the public key")
@click.option(
    "--pubkey",
    help="Public key to get the index for",
    prompt="Enter public key to get the index for",
)
def get_pubkey_index(pubkey: str) -> None:
    mnemonic = click.prompt(
        'Enter your mnemonic separated by spaces (" ")',
        value_proc=validate_mnemonic,
        type=click.STRING,
    )

    with click.progressbar(
        range(10000),
        label="Getting index of the public key\t\t",
        show_percent=False,
        show_pos=True,
    ) as indexes:
        for index in indexes:
            signing_key = get_mnemonic_signing_key(mnemonic, index, IS_LEGACY)
            public_key = Web3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))
            if public_key == pubkey:
                click.echo(f"\nPublic key {pubkey} index is {index}")
                return

    click.secho(
        f"Failed to find index for the public key {pubkey}. Is it legacy derivation?",
        bold=True,
        fg="red",
    )
