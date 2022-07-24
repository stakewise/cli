import unittest
from unittest.mock import patch

from click.testing import CliRunner
from py_ecc.bls import G2ProofOfPossession
from staking_deposit.key_handling.key_derivation.mnemonic import get_mnemonic
from web3 import Web3

from stakewise_cli.commands.sync_db import sync_db
from stakewise_cli.eth2 import (
    WORD_LISTS_PATH,
    ValidatorStatus,
    get_mnemonic_signing_key,
)
from stakewise_cli.networks import MAINNET

from .factories import faker

w3 = Web3()

ipfs_url = "/ipfs/" + faker.text(max_nb_chars=20)

mnemonic = get_mnemonic(language="english", words_path=WORD_LISTS_PATH)
keys_count = 5


def get_public_keys(mnemonic, keys_count):
    result = []
    for i in range(keys_count):
        signing_key = get_mnemonic_signing_key(mnemonic, i, is_legacy=False)
        public_key = w3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))
        result.append(public_key)
    return result


public_keys = get_public_keys(mnemonic=mnemonic, keys_count=keys_count)

validators = [
    {"validator": {"pubkey": public_key}, "status": ValidatorStatus.ACTIVE_ONGOING}
    for public_key in public_keys
]

ipfs_response = [
    {
        "amount": "32000000000000000000",
        "deposit_data_root": faker.eth_address(),
        "proof": [faker.eth_address() for i in range(5)],
        "public_key": public_key,
        "signature": faker.eth_signature(),
        "withdrawal_credentials": faker.eth_address(),
    }
    for public_key in public_keys
]


@patch("stakewise_cli.commands.sync_db.check_db_connection")
@patch("stakewise_cli.commands.sync_db.prompt_beacon_client")
@patch("stakewise_cli.web3signer.get_validators", return_value=validators)
@patch(
    "stakewise_cli.web3signer.get_operator_deposit_data_ipfs_link",
    return_value=ipfs_url,
)
@patch("stakewise_cli.web3signer.ipfs_fetch", return_value=ipfs_response)
class TestCommand(unittest.TestCase):
    @patch(
        "stakewise_cli.commands.sync_db.Database.update_keys",
        return_value=None,
    )
    def test_sync_db(self, insert_mock, *mocks):
        network = MAINNET
        operator = faker.eth_address()
        db_url = "postgresql://username:pass@hostname/dbname"
        validator_capacity = 2
        runner = CliRunner()
        args = [
            "--network",
            network,
            "--operator",
            operator,
            "--db-url",
            db_url,
            "--validator-capacity",
            validator_capacity,
        ]

        result = runner.invoke(sync_db, args, input=f"{mnemonic}\nY\n")

        assert result.exit_code == 0
        insert_mock.assert_called_once()
        results = insert_mock.call_args.kwargs["keys"]

        assert [x["public_key"] for x in results] == public_keys
        assert [x["validator_index"] for x in results] == [0, 0, 1, 1, 2]
        assert (
            f"Synced {keys_count} key pairs, apply changes to the database?"
            in result.output.strip()
        )
        assert (
            f"The database contains {keys_count} validator keys."
            in result.output.strip()
        )
        assert (
            f"Please upgrade the 'validators' helm chart with 'validatorsCount' set to {3}"
            in result.output.strip()
        )
