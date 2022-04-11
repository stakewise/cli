import click
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3

from stakewise_cli.eth2 import get_mnemonic_signing_key, validate_mnemonic


@click.command(help="Gets public key of the mnemonic at index")
@click.option(
    "--index",
    help="Get public key of the mnemonic at specific index",
    default=0,
    type=int,
)
def get_mnemonic_pubkey(index: int) -> None:
    mnemonic = click.prompt(
        'Enter your mnemonic separated by spaces (" ")',
        value_proc=validate_mnemonic,
        type=click.STRING,
    )

    signing_key = get_mnemonic_signing_key(mnemonic, index)
    public_key = Web3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))
    click.echo(f"Public key with {index} index: {public_key}")

    legacy_signing_key = get_mnemonic_signing_key(mnemonic, index, True)
    public_key = Web3.toHex(G2ProofOfPossession.SkToPk(legacy_signing_key.key))
    click.echo(f"Legacy public key with {index} index: {public_key}")
