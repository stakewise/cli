import click
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3

from stakewise_cli.ipfs import upload_public_keys_to_ipfs


def validate_private_key(ctx, param, value) -> str:
    try:
        with open(value, "r") as f:
            RSA.import_key(f.read())

        return value
    except:  # noqa: E722
        pass

    raise click.BadParameter("Invalid Private Key")


@click.command(help="Creates public keys for operator shard")
@click.option(
    "--private-key",
    help="Path to the committee member private key file.",
    prompt="Enter path to the committee member private key",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    callback=validate_private_key,
)
@click.option(
    "--shard",
    help="Path to the operator shard file.",
    prompt="Enter path to operator shard file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def create_shard_pubkeys(shard: str, private_key: str) -> None:
    try:
        with open(private_key, "r") as f:
            private_key = RSA.import_key(f.read())
        with open(shard, "rb") as f:
            enc_session_key, nonce, tag, ciphertext = [
                f.read(x) for x in (private_key.size_in_bytes(), 16, 16, -1)
            ]
    except:  # noqa: E722
        raise click.ClickException("Invalid operator shard file")

    # Decrypt the session key with the private RSA key
    try:
        cipher_rsa = PKCS1_OAEP.new(private_key)
        session_key = cipher_rsa.decrypt(enc_session_key)
    except:  # noqa: E722
        raise click.ClickException(
            "Failed to decrypt the session key. Please check whether the paths to private key and shard"
        )

    # Decrypt the data with the AES session key
    cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
    try:
        private_keys = cipher_aes.decrypt_and_verify(ciphertext, tag).split(b",")
    except:  # noqa: E722
        raise click.ClickException("Failed to decrypt the shard file. Is it corrupted?")

    public_keys = []
    with click.progressbar(
        private_keys,
        label="Deriving public keys for operator shard\t\t",
        show_percent=False,
        show_pos=True,
    ) as _private_keys:
        for priv_key in _private_keys:
            public_keys.append(Web3.toHex(G2ProofOfPossession.SkToPk(int(priv_key))))

    ipfs_hash = upload_public_keys_to_ipfs(public_keys)
    click.echo(
        f'Please share the IPFS hash in "operators" Discord chat:'
        f" {click.style(ipfs_hash, fg='green')}",
    )
