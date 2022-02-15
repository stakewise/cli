from os import mkdir
from os.path import exists, join
from secrets import randbits
from typing import Dict, List, Tuple, cast

import click
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.Cipher._mode_eax import EaxMode
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from eth_typing import ChecksumAddress
from gql import Client
from py_ecc.bls.ciphersuites import G2ProofOfPossession
from py_ecc.optimized_bls12_381.optimized_curve import curve_order

from operator_cli.eth1 import get_operator_allocation_id, get_operators_committee
from operator_cli.typings import BLSPrivkey, KeyPair

PRIME = curve_order


def get_polynomial_points(coefficients: List[int], num_points: int) -> List[BLSPrivkey]:
    """Calculates polynomial points."""
    points = []
    for x in range(1, num_points + 1):
        # start with x=1 and calculate the value of y
        y = coefficients[0]
        # calculate each term and add it to y, using modular math
        for i in range(1, len(coefficients)):
            exponentiation = (x**i) % PRIME
            term = (coefficients[i] * exponentiation) % PRIME
            y = (y + term) % PRIME
        # add the point to the list of points
        points.append(y)
    return points


def generate_bls_priv_key() -> BLSPrivkey:
    seed = randbits(256).to_bytes(32, "big")
    return BLSPrivkey(G2ProofOfPossession.KeyGen(seed))


def get_bls_secret_shares(
    private_key: BLSPrivkey, total: int, threshold: int
) -> List[BLSPrivkey]:
    """Generates Shamir's secrets for the BLS keypair."""
    if threshold < 2:
        raise click.ClickException(f"Invalid shares threshold: {threshold}")
    elif total < 2:
        raise click.ClickException(f"Invalid total shares: {total}")

    coefficients = [generate_bls_priv_key() for _ in range(threshold - 1)]
    coefficients = [private_key] + coefficients
    private_key_secrets = get_polynomial_points(coefficients, total)
    return private_key_secrets


def rsa_encrypt(
    recipient_public_key: str, data: str
) -> Tuple[bytes, bytes, bytes, bytes]:
    """Encrypts data with rsa public key."""
    public_key = RSA.import_key(recipient_public_key)
    cipher_rsa = PKCS1_OAEP.new(public_key)
    session_key = get_random_bytes(32)

    # Encrypt the session key with the public RSA key
    enc_session_key = cipher_rsa.encrypt(session_key)

    # Encrypt the data with the AES session key
    cipher_aes = cast(EaxMode, AES.new(session_key, AES.MODE_EAX))
    ciphertext, tag = cipher_aes.encrypt_and_digest(data.encode("utf-8"))
    return enc_session_key, cipher_aes.nonce, tag, ciphertext


def create_committee_shares(
    network: str,
    gql_client: Client,
    operator: ChecksumAddress,
    committee_folder: str,
    keypairs: List[KeyPair],
) -> Dict[str, str]:
    if not exists(committee_folder):
        mkdir(committee_folder)

    committee = get_operators_committee(network)
    committee_final_shares = [
        [[] for _ in range(len(committee[i]))] for i in range(len(committee))
    ]
    for keypair in keypairs:
        committee_shares_total = len(committee)
        committee_shares = get_bls_secret_shares(
            private_key=keypair["private_key"],
            total=committee_shares_total,
            threshold=committee_shares_total,
        )
        for i, committee_share in enumerate(committee_shares):
            members_shares_total = len(committee[i])
            members_shares_threshold = (members_shares_total // 2) + 1
            members_shares = get_bls_secret_shares(
                private_key=committee_share,
                total=members_shares_total,
                threshold=members_shares_threshold,
            )
            for j, member_share in enumerate(members_shares):
                committee_final_shares[i][j].append(member_share)

    allocation_id = get_operator_allocation_id(gql_client, operator)
    allocation_name = f"{operator.lower()[2:10]}-{allocation_id}"

    committee_paths = {}
    members_count = sum([len(committee[i]) for i in range(len(committee))])
    with click.progressbar(
        length=members_count,
        label="Creating validator key shares\t\t",
        show_percent=False,
        show_pos=True,
    ) as bar:
        for i in range(len(committee)):
            for j in range(len(committee[i])):
                secret = ",".join(str(share) for share in committee_final_shares[i][j])
                rsa_pub_key = committee[i][j]
                member_handler = rsa_pub_key.split(" ")[-1]
                filename = f"{member_handler}-{allocation_name}.bin"
                enc_session_key, nonce, tag, ciphertext = rsa_encrypt(
                    recipient_public_key=rsa_pub_key,
                    data=secret,
                )
                file_path = join(committee_folder, filename)
                with open(file_path, "wb") as f:
                    for data in (enc_session_key, nonce, tag, ciphertext):
                        f.write(data)

                committee_paths[member_handler] = file_path
                bar.update(1)

    return committee_paths
