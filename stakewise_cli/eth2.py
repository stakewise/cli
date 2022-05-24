import os
import secrets
import string
from enum import Enum
from itertools import chain
from multiprocessing import Pool
from typing import Dict, List, Set, Tuple

import backoff
import click
from eth_typing import BLSPubkey, BLSSignature, HexStr
from eth_utils import add_0x_prefix
from gql import Client
from py_ecc.bls import G2ProofOfPossession
from staking_deposit.key_handling.key_derivation.mnemonic import (
    get_mnemonic,
    get_seed,
    verify_mnemonic,
)
from staking_deposit.key_handling.key_derivation.path import path_to_nodes
from staking_deposit.key_handling.key_derivation.tree import (
    derive_child_SK,
    derive_master_SK,
)
from staking_deposit.utils.constants import MNEMONIC_LANG_OPTIONS
from staking_deposit.utils.ssz import DepositData as SSZDepositData
from staking_deposit.utils.ssz import (
    DepositMessage,
    compute_deposit_domain,
    compute_signing_root,
)
from web3 import Web3
from web3.beacon import Beacon
from web3.types import Wei

from stakewise_cli.merkle_tree import MerkleTree
from stakewise_cli.queries import REGISTRATIONS_QUERY
from stakewise_cli.settings import IS_LEGACY
from stakewise_cli.typings import (
    BLSPrivkey,
    Bytes4,
    Bytes32,
    Gwei,
    KeyPair,
    MerkleDepositData,
    SigningKey,
)
from stakewise_cli.utils import chunkify

# TODO: find a way to import "from eth2deposit.utils.constants import WORD_LISTS_PATH"
WORD_LISTS_PATH = os.path.join(os.path.dirname(__file__), "word_lists")

LANGUAGES = MNEMONIC_LANG_OPTIONS.keys()

SPECIAL_CHARS = "!@#$%^&*()_"

# Set path as EIP-2334 format
# https://eips.ethereum.org/EIPS/eip-2334
PURPOSE = "12381"
COIN_TYPE = "3600"

w3 = Web3()
VALIDATOR_DEPOSIT_AMOUNT: Wei = w3.toWei(32, "ether")


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


def get_beacon_client(network: str) -> Beacon:
    url = click.prompt(f"Enter the beacon node URL for {network}", type=click.STRING)
    return Beacon(base_url=url)


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


def generate_keypairs(
    indexes: List[int], mnemonic: str, gql_client: Client
) -> List[KeyPair]:
    pub_key_to_priv_key: Dict[HexStr, BLSPrivkey] = {}

    # derive signing key
    public_keys: List[HexStr] = []
    for index in indexes:
        signing_key = get_mnemonic_signing_key(mnemonic, index, IS_LEGACY)
        # derive public key
        public_key = w3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))
        # store keypairs
        pub_key_to_priv_key[public_key] = signing_key.key
        public_keys.append(public_key)

    # remove keys that were already registered in beacon chain
    result: Dict = gql_client.execute(
        document=REGISTRATIONS_QUERY,
        variable_values=dict(public_keys=public_keys),
    )
    registrations = result["validatorRegistrations"]
    for registration in registrations:
        pub_key_to_priv_key.pop(registration["publicKey"], None)

    return [
        KeyPair(private_key=priv_key, public_key=pub_key)
        for pub_key, priv_key in pub_key_to_priv_key.items()
    ]


def generate_unused_validator_keys(
    gql_client: Client,
    mnemonic: str,
    keys_count: int,
) -> List[KeyPair]:
    """Generates specified number of unused validator key-pairs from the mnemonic."""
    with click.progressbar(
        length=keys_count,
        label="Creating validator keys:\t\t",
        show_percent=False,
        show_pos=True,
    ) as bar:
        with Pool() as pool:

            def bar_updated(result, *args, **kwargs):
                bar.update(len(result))

            results = []
            indexes = [i for i in range(keys_count)]
            for chunk in chunkify(indexes, 50):
                results.append(
                    pool.apply_async(
                        generate_keypairs,
                        [chunk, mnemonic, gql_client],
                        callback=bar_updated,
                    )
                )
            [result.wait() for result in results]
            return list(chain.from_iterable([result.get() for result in results]))


def get_mnemonic_signing_key(
    mnemonic: str, from_index: int, is_legacy: bool = False
) -> SigningKey:
    """Returns the signing key of the mnemonic at a specific index."""
    seed = get_seed(mnemonic=mnemonic, password="")
    private_key = BLSPrivkey(derive_master_SK(seed))
    signing_key_path = f"m/{PURPOSE}/{COIN_TYPE}/{from_index}/0/0"
    if is_legacy:
        nodes = path_to_nodes(f"m/{PURPOSE}/{COIN_TYPE}/0/0/{from_index}")
    else:
        nodes = path_to_nodes(signing_key_path)

    for node in nodes:
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
        if (
            upper_set.intersection(password_set)
            and lower_set.intersection(password_set)
            and special_set.intersection(password_set)
            and digits_set.intersection(password_set)
        ):
            return "".join(password)


def get_deposit_data_signature(
    private_key: BLSPrivkey,
    public_key: BLSPubkey,
    withdrawal_credentials: Bytes32,
    amount: Gwei,
    fork_version: Bytes4,
) -> Tuple[BLSSignature, Bytes32]:
    """:returns deposit data signature and root for Validator Registration Contract."""
    deposit_message = DepositMessage(
        pubkey=public_key, withdrawal_credentials=withdrawal_credentials, amount=amount
    )
    domain = compute_deposit_domain(fork_version=fork_version)
    signing_root = compute_signing_root(deposit_message, domain)
    signature = G2ProofOfPossession.Sign(private_key, signing_root)
    deposit_data = SSZDepositData(**deposit_message.as_dict(), signature=signature)

    return signature, deposit_data.hash_tree_root


def get_deposit_data_roots(
    public_key: BLSPubkey,
    withdrawal_credentials: Bytes32,
    signature: BLSSignature,
    amount: Gwei,
    fork_version: Bytes4,
) -> Tuple[Bytes32, Bytes32]:
    """:returns deposit data hash tree root."""
    deposit_message = DepositMessage(
        pubkey=public_key, withdrawal_credentials=withdrawal_credentials, amount=amount
    )
    domain = compute_deposit_domain(fork_version=fork_version)
    signing_root = compute_signing_root(deposit_message, domain)
    deposit_data = SSZDepositData(**deposit_message.as_dict(), signature=signature)

    return Bytes32(signing_root), deposit_data.hash_tree_root


def verify_deposit_data(
    signature: BLSSignature,
    public_key: BLSPubkey,
    withdrawal_credentials: Bytes32,
    amount: Gwei,
    hash_tree_root: Bytes32,
    fork_version: Bytes4,
) -> bool:
    """:returns verifies deposit data."""
    deposit_message = DepositMessage(
        pubkey=public_key, withdrawal_credentials=withdrawal_credentials, amount=amount
    )
    domain = compute_deposit_domain(fork_version=fork_version)
    signing_root = compute_signing_root(deposit_message, domain)
    if not G2ProofOfPossession.Verify(public_key, signing_root, signature):
        return False

    deposit_data = SSZDepositData(**deposit_message.as_dict(), signature=signature)
    return deposit_data.hash_tree_root == hash_tree_root


def generate_deposit_data(
    withdrawal_credentials: HexStr,
    deposit_amount: Wei,
    withdrawal_credentials_bytes: Bytes32,
    deposit_amount_gwei: Gwei,
    genesis_fork_version: bytes,
    keypair: KeyPair,
) -> (MerkleDepositData, bytes):
    private_key = keypair["private_key"]
    public_key = keypair["public_key"]
    signature, deposit_data_root = get_deposit_data_signature(
        private_key=private_key,
        public_key=BLSPubkey(w3.toBytes(hexstr=public_key)),
        withdrawal_credentials=withdrawal_credentials_bytes,
        amount=deposit_amount_gwei,
        fork_version=Bytes4(genesis_fork_version),
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
    return MerkleDepositData(
        public_key=public_key,
        signature=w3.toHex(signature),
        amount=str(deposit_amount),
        withdrawal_credentials=withdrawal_credentials,
        deposit_data_root=w3.toHex(deposit_data_root),
        proof=[],
    ), w3.keccak(primitive=encoded_data)


def generate_merkle_deposit_datum(
    genesis_fork_version: bytes,
    withdrawal_credentials: HexStr,
    deposit_amount: Wei,
    loading_label: str,
    validator_keypairs: List[KeyPair],
) -> Tuple[HexStr, List[MerkleDepositData]]:
    """Generates deposit data with merkle proofs for the validators."""
    withdrawal_credentials_bytes: Bytes32 = Bytes32(
        w3.toBytes(hexstr=withdrawal_credentials)
    )

    deposit_amount_gwei: Gwei = Gwei(int(w3.fromWei(deposit_amount, "gwei")))
    merkle_deposit_datum: List[MerkleDepositData] = []
    merkle_elements: List[bytes] = []
    with click.progressbar(
        validator_keypairs, label=loading_label, show_percent=False, show_pos=True
    ) as bar:
        with Pool() as pool:

            def bar_updated(*args, **kwargs):
                bar.update(1)

            results = [
                pool.apply_async(
                    generate_deposit_data,
                    [
                        withdrawal_credentials,
                        deposit_amount,
                        withdrawal_credentials_bytes,
                        deposit_amount_gwei,
                        genesis_fork_version,
                        keypair,
                    ],
                    callback=bar_updated,
                )
                for keypair in validator_keypairs
            ]
            [result.wait() for result in results]
            for deposit_data, merkle_element in [result.get() for result in results]:
                merkle_elements.append(merkle_element)
                merkle_deposit_datum.append(deposit_data)

    merkle_tree = MerkleTree(merkle_elements)

    # collect proofs
    for i, deposit_data in enumerate(merkle_deposit_datum):
        proof: List[HexStr] = merkle_tree.get_hex_proof(merkle_elements[i])
        deposit_data["proof"] = proof

    # calculate merkle root
    merkle_root: HexStr = merkle_tree.get_hex_root()

    return merkle_root, merkle_deposit_datum


def get_registered_public_keys(
    gql_client: Client, seen_public_keys: List[HexStr]
) -> Set[HexStr]:
    keys_count = len(seen_public_keys)
    verified_public_keys: List[HexStr] = []
    registered_public_keys: Set[HexStr] = set()
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
            for registration in registrations:
                registered_public_keys.add(registration["publicKey"])

            bar.update(len(verified_public_keys) - curr_progress)

    return registered_public_keys
