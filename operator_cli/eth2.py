import os
import secrets
import string
from enum import Enum
from typing import Dict, List, Tuple

import backoff
import click
from eth2deposit.key_handling.key_derivation.mnemonic import (
    get_languages,
    get_mnemonic,
    get_seed,
    verify_mnemonic,
)
from eth2deposit.key_handling.key_derivation.path import path_to_nodes
from eth2deposit.key_handling.key_derivation.tree import (
    derive_child_SK,
    derive_master_SK,
)
from eth2deposit.settings import BaseChainSetting
from eth2deposit.utils.ssz import DepositData as SSZDepositData
from eth2deposit.utils.ssz import (
    DepositMessage,
    compute_deposit_domain,
    compute_signing_root,
)
from eth_typing import BLSPubkey, BLSSignature, HexStr
from gql import Client as GqlClient
from py_ecc.bls import G2ProofOfPossession
from web3 import Web3
from web3.beacon import Beacon
from web3.types import Wei

from operator_cli.graphql import REGISTRATIONS_QUERY
from operator_cli.merkle_tree import MerkleTree
from operator_cli.settings import WITHDRAWAL_CREDENTIALS
from operator_cli.types import (
    BLSPrivkey,
    Bytes4,
    Bytes32,
    Gwei,
    KeyPair,
    MerkleDepositData,
    SigningKey,
)

# TODO: find a way to import "from eth2deposit.utils.constants import WORD_LISTS_PATH"
WORD_LISTS_PATH = os.path.join(os.path.dirname(__file__), "word_lists")

LANGUAGES = get_languages(WORD_LISTS_PATH)

SPECIAL_CHARS = "!@#$%^&*()_"

# Set path as EIP-2334 format
# https://eips.ethereum.org/EIPS/eip-2334
PURPOSE = "12381"
COIN_TYPE = "3600"

w3 = Web3()
INITIALIZE_DEPOSIT_AMOUNT: Wei = w3.toWei(1, "ether")
FINALIZE_DEPOSIT_AMOUNT: Wei = w3.toWei(31, "ether")


class ValidatorStatus(Enum):
    """Validator statuses in beacon chain"""

    PENDING_INITIALIZED = "pending_initialized"
    PENDING_QUEUED = "pending_queued"
    ACTIVE_ONGOING = "active_ongoing"
    ACTIVE_EXITING = "active_exiting"
    ACTIVE_SLASHED = "active_slashed"
    EXITED_UNSLASHED = "exited_unslashed"
    EXITED_SLASHED = "exited_slashed"
    WITHDRAWAL_POSSIBLE = "withdrawal_possible"
    WITHDRAWAL_DONE = "withdrawal_done"


EXITED_STATUSES = [
    ValidatorStatus.EXITED_UNSLASHED,
    ValidatorStatus.EXITED_SLASHED,
    ValidatorStatus.WITHDRAWAL_POSSIBLE,
    ValidatorStatus.WITHDRAWAL_DONE,
]


def validate_mnemonic(mnemonic) -> str:
    if verify_mnemonic(mnemonic, WORD_LISTS_PATH):
        return mnemonic
    else:
        raise click.BadParameter(
            "That is not a valid mnemonic, please check for typos."
        )


def create_new_mnemonic(mnemonic_language: str) -> str:
    mnemonic = get_mnemonic(language=mnemonic_language, words_path=WORD_LISTS_PATH)
    test_mnemonic = ""
    while mnemonic != test_mnemonic:
        click.clear()
        click.echo(
            "This is your seed phrase. Write it down and store it safely, it is the ONLY way to recover your validator keys."
        )  # noqa: E501
        click.echo("\n\n%s\n\n" % mnemonic)
        click.pause("Press any key when you have written down your mnemonic.")

        click.clear()
        test_mnemonic = click.prompt(
            "Please type your mnemonic (separated by spaces) to confirm you have written it down\n\n"
        )  # noqa: E501
        test_mnemonic = test_mnemonic.lower()
    click.clear()

    return mnemonic


def generate_unused_validator_keys(
    gql_client: GqlClient, mnemonic: str, keys_count: int
) -> List[KeyPair]:
    """Generates specified number of unused validator key-pairs from the mnemonic."""
    pub_key_to_priv_key: Dict[HexStr, BLSPrivkey] = {}
    with click.progressbar(
        length=keys_count,
        label="Creating validator keys:\t\t",
        show_percent=False,
        show_pos=True,
    ) as bar:
        from_index = 0
        while len(pub_key_to_priv_key) < keys_count:
            curr_progress = len(pub_key_to_priv_key)
            chunk_size = min(100, keys_count - curr_progress)

            # generate keys in chunks
            public_keys_chunk: List[HexStr] = []
            while len(public_keys_chunk) != chunk_size:
                # derive signing key
                signing_key = get_mnemonic_signing_key(mnemonic, from_index)

                # derive public key
                public_key = w3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))

                # store keypairs
                pub_key_to_priv_key[public_key] = signing_key.key
                public_keys_chunk.append(public_key)

                # increase index for generating other keys
                from_index += 1

            # remove keys that were already registered in beacon chain
            result: Dict = gql_client.execute(
                document=REGISTRATIONS_QUERY,
                variable_values=dict(public_keys=public_keys_chunk),
            )
            registrations = result["validatorRegistrations"]
            for registration in registrations:
                del pub_key_to_priv_key[registration["id"]]

            bar.update(len(pub_key_to_priv_key) - curr_progress)

    return [
        KeyPair(private_key=priv_key, public_key=pub_key)
        for pub_key, priv_key in pub_key_to_priv_key.items()
    ]


def get_mnemonic_signing_key(
    mnemonic: str, from_index: int, is_legacy: bool = False
) -> SigningKey:
    """Returns the signing key of the mnemonic at a specific index."""
    seed = get_seed(mnemonic=mnemonic, password="")
    private_key = BLSPrivkey(derive_master_SK(seed))
    if is_legacy:
        signing_key_path = f"m/{PURPOSE}/{COIN_TYPE}/0/0/{from_index}"
    else:
        signing_key_path = f"m/{PURPOSE}/{COIN_TYPE}/{from_index}/0/0"

    for node in path_to_nodes(signing_key_path):
        private_key = BLSPrivkey(derive_child_SK(parent_SK=private_key, index=node))

    return SigningKey(key=private_key, path=signing_key_path)


@backoff.on_exception(backoff.expo, Exception, max_time=180)
def get_validators(
    beacon: Beacon, public_keys: List[HexStr], state_id: str = "head"
) -> List[Dict]:
    """Fetches validators."""
    if not public_keys:
        return []

    endpoint = (
        f"/eth/v1/beacon/states/{state_id}/validators?id={'&id='.join(public_keys)}"
    )
    # noinspection PyProtectedMember
    return beacon._make_get_request(endpoint)["data"]


def generate_password() -> str:
    """Generates secure password."""
    alphabet = string.ascii_letters + string.digits + SPECIAL_CHARS
    lower_set = set(string.ascii_lowercase)
    upper_set = set(string.ascii_uppercase)
    digits_set = set(string.digits)
    special_set = set(SPECIAL_CHARS)
    while True:
        password = [secrets.choice(alphabet) for _ in range(20)]
        password_set = set(password)
        if not (
            upper_set.intersection(password_set)
            and lower_set.intersection(password_set)
            and special_set.intersection(password_set)
            and digits_set.intersection(password_set)
        ):
            continue

        return "".join(password)


def get_deposit_data_signature(
    private_key: BLSPrivkey,
    public_key: BLSPubkey,
    withdrawal_credentials: Bytes32,
    amount: Gwei,
    fork_version: Bytes4,
) -> Tuple[BLSSignature, Bytes32]:
    """:returns deposit data for Validator Registration Contract."""
    deposit_message = DepositMessage(
        pubkey=public_key, withdrawal_credentials=withdrawal_credentials, amount=amount
    )
    domain = compute_deposit_domain(fork_version=fork_version)
    signing_root = compute_signing_root(deposit_message, domain)
    signature = G2ProofOfPossession.Sign(private_key, signing_root)
    deposit_data = SSZDepositData(**deposit_message.as_dict(), signature=signature)

    return signature, deposit_data.hash_tree_root


def generate_merkle_deposit_datum(
    chain_setting: BaseChainSetting,
    deposit_amount: Wei,
    loading_label: str,
    validator_keypairs: List[KeyPair],
) -> Tuple[HexStr, List[MerkleDepositData]]:
    """Generates deposit data with merkle proofs for the validators."""
    withdrawal_credentials_bytes: Bytes32 = Bytes32(
        w3.toBytes(hexstr=WITHDRAWAL_CREDENTIALS)
    )
    deposit_amount_gwei: Gwei = Gwei(int(w3.fromWei(deposit_amount, "gwei")))
    merkle_deposit_datum: List[MerkleDepositData] = []
    merkle_elements: List[bytes] = []
    with click.progressbar(
        validator_keypairs, label=loading_label, show_percent=False, show_pos=True
    ) as keypairs:
        for keypair in keypairs:
            private_key = keypair["private_key"]
            public_key = keypair["public_key"]
            signature, deposit_data_root = get_deposit_data_signature(
                private_key=private_key,
                public_key=BLSPubkey(w3.toBytes(hexstr=public_key)),
                withdrawal_credentials=withdrawal_credentials_bytes,
                amount=deposit_amount_gwei,
                fork_version=Bytes4(chain_setting.GENESIS_FORK_VERSION),
            )
            encoded_data: bytes = w3.codec.encode_abi(
                ["bytes", "bytes32", "bytes", "bytes32"],
                [
                    public_key,
                    withdrawal_credentials_bytes,
                    signature,
                    deposit_data_root,
                ],
            )
            merkle_elements.append(w3.keccak(primitive=encoded_data))
            deposit_data = MerkleDepositData(
                public_key=public_key,
                signature=w3.toHex(signature),
                amount=str(deposit_amount),
                withdrawal_credentials=WITHDRAWAL_CREDENTIALS,
                deposit_data_root=w3.toHex(deposit_data_root),
                proof=[],
            )
            merkle_deposit_datum.append(deposit_data)

    merkle_tree = MerkleTree(merkle_elements)

    # collect proofs
    for i, deposit_data in enumerate(merkle_deposit_datum):
        proof: List[HexStr] = merkle_tree.get_hex_proof(merkle_elements[i])
        deposit_data["proof"] = proof

    # calculate merkle root
    merkle_root: HexStr = merkle_tree.get_hex_root()

    return merkle_root, merkle_deposit_datum
