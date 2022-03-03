from os import getcwd
from os.path import isfile, join

import click
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from py_ecc.bls import G2ProofOfPossession


@click.command(help="Verify committee file")
@click.option(
    "--committee-file",
    default=join(getcwd()),
    help="Path to committee file.",
    type=click.Path(exists=False, file_okay=True, dir_okay=True),
)
@click.option(
    "--private-key",
    default=join(getcwd()),
    help="Path to private key file.",
    type=click.Path(exists=False, file_okay=True, dir_okay=True),
)
def verify_committee_file(committee_file, private_key) -> None:
    while not isfile(committee_file):
        print("Committee file not found")
        committee_file = input("Enter path to committee file: ")

    while not isfile(private_key):
        print("Private key file not found")
        private_key = input("Enter path to private key file: ")

    file_in = open(committee_file, "rb")

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
        print("Verify failed")

    # Decrypt the data with the AES session key
    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    try:
        private_keys = cipher_aes.decrypt_and_verify(ciphertext, tag)
    except (UnboundLocalError, ValueError, TypeError):
        print("Verify failed")

    message = b"\xab" * 32
    public_keys = [G2ProofOfPossession.SkToPk(key) for key in private_keys]
    signatures = [G2ProofOfPossession.Sign(key, message) for key in private_keys]
    agg_sig = G2ProofOfPossession.Aggregate(signatures)
    assert G2ProofOfPossession.FastAggregateVerify(public_keys, message, agg_sig)

    click.secho(
        "Submit the post to https://forum.stakewise.io with the following aggregated signature:",
        bold=True,
        fg="green",
    )
    click.echo(agg_sig)
