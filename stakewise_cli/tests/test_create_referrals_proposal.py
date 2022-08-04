import decimal
import random
import unittest
from typing import Any, Dict, List
from unittest.mock import patch

from click.testing import CliRunner

from stakewise_cli.commands.create_referrals_proposal import (  # noqa: E402
    create_referrals_proposal,
)
from stakewise_cli.networks import MAINNET, NETWORKS

from .factories import faker

from_date_timestamp = random.randint(1000000, 2000000)
to_date_timestamp = random.randint(from_date_timestamp, from_date_timestamp + 1000000)

ipfs_url = "/ipfs/" + faker.text(max_nb_chars=20)


@patch(
    "stakewise_cli.commands.create_referrals_proposal.get_block_timestamp",
    return_value=[from_date_timestamp, to_date_timestamp],
)
class TestCommand(unittest.TestCase):
    @patch(
        "stakewise_cli.commands.create_referrals_proposal.upload_to_ipfs",
        return_value=ipfs_url,
    )
    def test_create_referrals_proposal(self, upload_mock, *mocks):
        referrals = [
            {
                "id": faker.public_key(),
                "referrer": faker.eth_address(),
                "amount": 10**18,
            }
        ]

        network = MAINNET
        from_block = faker.random_int(100000000, 150000000)
        to_block = faker.random_int(150000000, 160000000)
        referral_share = 1
        runner = CliRunner()
        args = [
            "--network",
            network,
            "--from-block",
            from_block,
            "--to-block",
            to_block,
            "--referral-share",
            referral_share,
            "--whitelist-path",
            "whitelisted.txt",
        ]
        swise_price = decimal.Decimal(0.04)
        eth_price = decimal.Decimal(1020)
        args.extend(["--swise-price", swise_price])
        args.extend(["--eth-price", eth_price])
        token_address = NETWORKS[network]["SWISE_TOKEN_CONTRACT_ADDRESS"]

        with runner.isolated_filesystem(), patch(
            "stakewise_cli.commands.create_referrals_proposal.get_referrals",
            return_value=referrals,
        ):
            with open("whitelisted.txt", "w") as f:
                for referrer in referrals:
                    f.writelines(referrer["referrer"])

            result = runner.invoke(create_referrals_proposal, args)

            assert result.exit_code == 0

            referrals_data = {
                referrals[0]["referrer"]: {f"{token_address}": 250 * 10**18}
            }

            upload_mock.assert_called_once_with(referrals_data)

            output = f"""
Submit the post to https://forum.stakewise.io with the following specification section:

# Referral Rewards Distribution

Distribute 250 SWISE to referrers specified in {ipfs_url}.

The rewards distribution was calculated with the following parameters:
* From block number: {from_block}
* To block number: {to_block}
* Distributed token: {token_address}
* Distributed token price (USD): {swise_price}
* ETH price (USD): {eth_price}
* Referral share (%): {referral_share}
"""
            assert result.output.strip() == output.strip()


@patch(
    "stakewise_cli.commands.create_referrals_proposal.get_block_timestamp",
    return_value=[from_date_timestamp, to_date_timestamp],
)
class TestSwiseAmount(unittest.TestCase):
    token_address = NETWORKS[MAINNET]["SWISE_TOKEN_CONTRACT_ADDRESS"]

    @patch(
        "stakewise_cli.commands.create_referrals_proposal.upload_to_ipfs",
        return_value=ipfs_url,
    )
    def test_referrals_proposal_regular(self, upload_mock, *mocks):
        referrals = [
            {
                "id": faker.public_key(),
                "referrer": faker.eth_address(),
                "amount": 10**18,
            },
            {
                "id": faker.public_key(),
                "referrer": faker.eth_address(),
                "amount": 0.5 * 10**18,
            },
        ]
        swise_price = decimal.Decimal(0.50)
        eth_price = decimal.Decimal(1000)
        referrals_data = {
            referrals[0]["referrer"]: {f"{self.token_address}": 20 * 10**18},
            referrals[1]["referrer"]: {f"{self.token_address}": 10 * 10**18},
        }

        self._call_command(referrals, swise_price, eth_price)
        upload_mock.assert_called_once_with(referrals_data)

    @patch(
        "stakewise_cli.commands.create_referrals_proposal.upload_to_ipfs",
        return_value=ipfs_url,
    )
    def test_referrals_proposal_min_swise(self, upload_mock, *mocks):
        referrals = [
            {
                "id": faker.public_key(),
                "referrer": faker.eth_address(),
                "amount": 10**18,
            }
        ]

        swise_price = decimal.Decimal(5.50)
        eth_price = decimal.Decimal(1000)
        referrals_data = {
            referrals[0]["referrer"]: {f"{self.token_address}": 5 * 10**18},
        }

        self._call_command(referrals, swise_price, eth_price)
        upload_mock.assert_called_once_with(referrals_data)

    @patch(
        "stakewise_cli.commands.create_referrals_proposal.upload_to_ipfs",
        return_value=ipfs_url,
    )
    def test_referrals_proposal_max_swise(self, upload_mock, *mocks):
        referrals = [
            {
                "id": faker.public_key(),
                "referrer": faker.eth_address(),
                "amount": 10**18,
            }
        ]

        swise_price = decimal.Decimal(0.01)
        eth_price = decimal.Decimal(1000)
        referrals_data = {
            referrals[0]["referrer"]: {f"{self.token_address}": 250 * 10**18},
        }

        self._call_command(referrals, swise_price, eth_price)
        upload_mock.assert_called_once_with(referrals_data)

    def _call_command(
        self,
        referrals: List[Dict[str, Any]],
        swise_price: decimal.Decimal,
        eth_price: decimal.Decimal,
    ):
        network = MAINNET
        from_block = faker.random_int(100000000, 150000000)
        to_block = faker.random_int(150000000, 160000000)
        referral_share = 1
        runner = CliRunner()
        args = [
            "--network",
            network,
            "--from-block",
            from_block,
            "--to-block",
            to_block,
            "--referral-share",
            referral_share,
            "--whitelist-path",
            "whitelisted.txt",
        ]
        args.extend(["--swise-price", swise_price])
        args.extend(["--eth-price", eth_price])

        with runner.isolated_filesystem(), patch(
            "stakewise_cli.commands.create_referrals_proposal.get_referrals",
            return_value=referrals,
        ):
            with open("whitelisted.txt", "w") as f:
                for referrer in referrals:
                    f.writelines(referrer["referrer"] + "\n")
            result = runner.invoke(create_referrals_proposal, args)
            print(result.output)
            assert result.exit_code == 0
