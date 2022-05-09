import decimal

import click
from web3 import Web3

from stakewise_cli.coinbase import get_coinbase_price
from stakewise_cli.eth1 import get_referrals
from stakewise_cli.ipfs import upload_to_ipfs
from stakewise_cli.networks import GNOSIS_CHAIN, GOERLI, MAINNET, NETWORKS, PERM_GOERLI
from stakewise_cli.proposals import generate_referrals_swise_specification
from stakewise_cli.queries import get_stakewise_gql_client

w3 = Web3()


@click.command(
    help="Creates referral proposal and generates a forum post specification"
)
@click.option(
    "--network",
    default=MAINNET,
    help="The network to generate the referral proposal for",
    prompt="Enter the network name",
    type=click.Choice(
        [MAINNET, GOERLI, PERM_GOERLI, GNOSIS_CHAIN], case_sensitive=False
    ),
)
@click.option(
    "--from-block",
    required=True,
    help="The block number to start collecting referrals from",
    type=int,
)
@click.option(
    "--to-block",
    required=True,
    help="The block number to collect referrals up to",
    type=int,
)
@click.option(
    "--referrals-share",
    required=True,
    prompt="Enter referrals share (%), ex. 1.5 = 1.5%",
    help="Referrals share (%), ex. 1.5 = 1.5%",
    type=decimal.Decimal,
)
@click.option(
    "--swise-price",
    help="SWISE price in USD",
    type=decimal.Decimal,
)
@click.option(
    "--eth-price",
    help="ETH price in USD",
    type=decimal.Decimal,
)
def create_referrals_proposal(
    network: str,
    from_block: int,
    to_block: int,
    referrals_share: decimal.Decimal,
    swise_price: decimal.Decimal,
    eth_price: decimal.Decimal,
) -> None:
    if not swise_price:
        swise_price = click.prompt(
            "Enter SWISE price (USD)",
            default=get_coinbase_price("swise"),
            type=decimal.Decimal,
        )
    if not eth_price:
        eth_price = click.prompt(
            "Enter ETH price (USD)",
            default=get_coinbase_price("eth"),
            type=decimal.Decimal,
        )
    # 1. Query referrals fee
    sw_gql_client = get_stakewise_gql_client(network)
    referrals_data = get_referrals(
        gql_client=sw_gql_client, from_block=from_block, to_block=to_block
    )
    token_address = NETWORKS[network]["SWISE_TOKEN_CONTRACT_ADDRESS"]
    referrals = {}
    total_amount = 0
    for item in referrals_data:
        amount = round(
            (eth_price / swise_price) * (referrals_share / 100) * int(item["amount"])
        )

        total_amount += amount
        referrer = Web3.toChecksumAddress(item["referrer"])
        referrals.setdefault(referrer, {}).setdefault(token_address, 0)
        referrals[referrer][token_address] += amount
    # 2. Upload referrals data to IPFS
    ipfs_url = upload_to_ipfs(referrals)

    # 3. Generate proposal specification text
    specification = generate_referrals_swise_specification(
        from_block=from_block,
        to_block=to_block,
        total_amount=total_amount,
        token_address=token_address,
        swise_price=swise_price,
        eth_price=eth_price,
        ipfs_url=ipfs_url,
        referral_share=referrals_share,
    )
    click.clear()
    click.secho(
        "Submit the post to https://forum.stakewise.io with the following specification section:",
        bold=True,
        fg="green",
    )
    click.echo(specification)
