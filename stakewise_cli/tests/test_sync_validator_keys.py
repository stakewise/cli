import os
import unittest
from unittest.mock import patch

from click.testing import CliRunner
from py_ecc.bls import G2ProofOfPossession
from staking_deposit.key_handling.key_derivation.mnemonic import get_mnemonic
from web3 import Web3

from stakewise_cli.commands.sync_validator_keys import sync_validator_keys
from stakewise_cli.eth2 import WORD_LISTS_PATH, get_mnemonic_signing_key
from stakewise_cli.networks import MAINNET, NETWORKS

from .factories import faker

w3 = Web3()

mnemonic = get_mnemonic(language="english", words_path=WORD_LISTS_PATH)
keys_count = 3
web3_signer_url = "http://web3signer:6174"


def get_public_keys(mnemonic, keys_count):
    result = []
    for i in range(keys_count):
        signing_key = get_mnemonic_signing_key(mnemonic, i, is_legacy=False)
        public_key = w3.toHex(G2ProofOfPossession.SkToPk(signing_key.key))
        result.append(public_key)
    return result


public_keys = get_public_keys(mnemonic=mnemonic, keys_count=keys_count)


@patch("stakewise_cli.commands.sync_validator_keys.check_db_connection")
@patch(
    "stakewise_cli.commands.sync_validator_keys.Database.fetch_public_keys_by_validator_index",
    return_value=public_keys,
)
@patch.dict(os.environ, {"WEB3SIGNER_URL": web3_signer_url})
class TestCommand(unittest.TestCase):
    def test_sync_validator_keys(self, *mocks):
        db_url = "postgresql://username:pass@hostname/dbname"
        network = MAINNET
        index = 1
        runner = CliRunner()
        solo_pub_key, solo_address = faker.public_key(), faker.eth_address()
        args = [
            "--network",
            network,
            "--index",
            index,
            "--db-url",
            db_url,
            "--output-dir",
            "./valdata",
            "--solo-fees-file",
            "./solo-fees.json",
        ]
        with runner.isolated_filesystem():
            with open("./solo-fees.json", "w") as f:
                f.writelines('{"%s":"%s"}' % (solo_pub_key, solo_address))
            result = runner.invoke(sync_validator_keys, args)
            assert result.exit_code == 0

            assert (
                f"The validator now uses {keys_count} public keys."
                == result.output.strip()
            )

            with open("./valdata/validator_definitions.yml") as f:
                s = """---"""
                for public_key in public_keys:
                    s += f"""
- enabled: true
  suggested_fee_recipient: \'{NETWORKS[network]["FEE_DISTRIBUTION_CONTRACT_ADDRESS"]}\'
  type: web3signer
  url: {web3_signer_url}
  voting_public_key: \'{public_key}\'"""
                s += "\n"
                assert f.read() == s

            with open("./valdata/signer_keys.yml") as f:
                s = f"""validators-external-signer-public-keys: ["{public_keys[0]}","{public_keys[1]}","{public_keys[2]}"]"""
                ff = f.read()
                assert ff == s, (ff, s)

            with open("./valdata/proposerConfig.json") as f:
                s = (
                    '{"proposer_config": {"%s": {"fee_recipient": "%s", "builder": {"enabled": true}}}, "default_config": {"fee_recipient": "%s", "builder": {"enabled": true}}}'
                    % (
                        solo_pub_key,
                        solo_address,
                        NETWORKS[network]["FEE_DISTRIBUTION_CONTRACT_ADDRESS"],
                    )
                )
                ff = f.read()

                assert ff == s, (ff, s)

            result = runner.invoke(sync_validator_keys, args)
            assert result.exit_code == 0
            assert "Keys already synced to the last version." == result.output.strip()
