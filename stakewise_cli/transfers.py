import glob
import os
from typing import Dict

import click
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from eth_typing import HexStr
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3


def decrypt_transferred_keys(keys_dir: str, decrypt_key: str) -> Dict[HexStr, int]:
    keypairs: Dict[HexStr, int] = dict()

    with open(decrypt_key, "r") as f:
        rsa_key = RSA.import_key(f.read())

    for filename in glob.glob(os.path.join(keys_dir, "*.enc")):
        with open(os.path.join(os.getcwd(), filename), "rb") as f:
            try:
                enc_session_key, nonce, tag, ciphertext = [
                    f.read(x) for x in (rsa_key.size_in_bytes(), 16, 16, -1)
                ]
            except:  # noqa: E722
                raise click.ClickException(
                    f"Invalid encrypted private key file: {filename}"
                )

        try:
            cipher_rsa = PKCS1_OAEP.new(rsa_key)
            session_key = cipher_rsa.decrypt(enc_session_key)
        except:  # noqa: E722
            raise click.ClickException("Failed to decrypt the private key.")

        # Decrypt the data with the AES session key
        cipher_aes = AES.new(session_key, AES.MODE_EAX, nonce)
        try:
            private_key = int(cipher_aes.decrypt_and_verify(ciphertext, tag))
            public_key = Web3.toHex(G2ProofOfPossession.SkToPk(private_key))
            keypairs[public_key] = private_key
        except:  # noqa: E722
            raise click.ClickException(
                "Failed to decrypt the private key file. Is it corrupted?"
            )

    return keypairs
