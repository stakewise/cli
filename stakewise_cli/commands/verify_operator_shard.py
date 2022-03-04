from os import getcwd
from os.path import isfile, join

import click
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3


@click.command(help="Command for verifying operator shard")
@click.option(
    "--shard",
    help="Path to the operator shard file.",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
)
@click.option(
    "--private-key",
    help="Path to the committee private key file.",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
)
def verify_operator_shard(shard: str, private_key: str) -> None:
    while not isfile(shard):
        click.secho(
            "Error: operator shard not found",
            bold=True,
            fg="red",
        )
        shard = input("Enter path to the operator shard file: ")

    while not isfile(private_key):
        click.secho(
            "Error: private key file not found",
            bold=True,
            fg="red",
        )
        private_key = input("Enter path to the committee private key file: ")

    file_in = open(shard, "rb")

    try:
        private_key = RSA.import_key(open(private_key).read())
    except (AttributeError, ValueError):
        print("Private key is invalid.")

    enc_session_key, nonce, tag, ciphertext = [
        file_in.read(x) for x in (private_key.size_in_bytes(), 16, 16, -1)
    ]

    # Decrypt the session key with the private RSA key
    cipher_rsa = PKCS1_OAEP.new(private_key)
    try:
        session_key = cipher_rsa.decrypt(enc_session_key)
    except (UnboundLocalError, ValueError):  # noqa: E722
        raise click.ClickException(
            "Failed to decrypt the session key. Please check whether the paths to private key and shard are correct"
        )

    # Decrypt the data with the AES session key
    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    try:
        private_keys = cipher_aes.decrypt_and_verify(ciphertext, tag)
    except (UnboundLocalError, ValueError, TypeError):
        raise click.ClickException(
            "Failed to decrypt the session key. Please check whether the paths to private key and shard are correct"
        )

    public_keys = [G2ProofOfPossession.SkToPk(key) for key in private_keys]
    agg_public_key = G2ProofOfPossession._AggregatePKs(public_keys)

    click.secho(
        "Please submit the following post to https://forum.stakewise.io for the operator who sent the shard file:",
        bold=True,
        fg="green",
    )
    click.echo(f"Shard Aggregated Public Key: {Web3.toHex(agg_public_key)}")
