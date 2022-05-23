import decimal

import click
from web3 import Web3

from stakewise_cli.coingecko import get_average_range_price
from stakewise_cli.eth1 import get_block_timestamp, get_referrals, get_web3_client
from stakewise_cli.ipfs import upload_to_ipfs
from stakewise_cli.networks import (
    GNOSIS_CHAIN,
    GOERLI,
    HARBOUR_GOERLI,
    HARBOUR_MAINNET,
    MAINNET,
    NETWORKS,
)
from stakewise_cli.proposals import generate_referrals_swise_specification
from stakewise_cli.queries import get_ethereum_gql_client, get_stakewise_gql_client

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
        [MAINNET, GOERLI, HARBOUR_MAINNET, HARBOUR_GOERLI, GNOSIS_CHAIN],
        case_sensitive=False,
    ),
)
@click.option(
    "--from-block",
    required=True,
    help="The block number to start collecting referrals from",
    prompt="Enter the block number to start collecting referrals from",
    type=int,
)
@click.option(
    "--to-block",
    required=True,
    help="The block number to collect referrals up to",
    prompt="Enter the block number to collect referrals up to",
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
    help="Average SWISE price in USD for the period",
    type=decimal.Decimal,
)
@click.option(
    "--eth-price",
    help="Average ETH price in USD for the period",
    type=decimal.Decimal,
)
@click.option(
    "--whitelist-path",
    help="The file path from where to read whitelisted accounts",
    prompt="Enter the file path from where to read whitelisted accounts. One address per line",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def create_referrals_proposal(
    network: str,
    from_block: int,
    to_block: int,
    referrals_share: decimal.Decimal,
    swise_price: decimal.Decimal,
    eth_price: decimal.Decimal,
    whitelist_path: str,
) -> None:
    if not from_block < to_block:
        raise click.ClickException(
            "The block number to start should be more the block number to collect referrals up to"
        )

    w3 = get_web3_client(network)

    ethereum_gql_client = get_ethereum_gql_client(network)
    from_date = get_block_timestamp(
        gql_client=ethereum_gql_client, block_number=from_block
    )
    to_date = get_block_timestamp(gql_client=ethereum_gql_client, block_number=to_block)

    if not from_date:
        raise click.ClickException(
            "Invalid block number to start collecting referrals from"
        )
    if not to_date:
        raise click.ClickException("Invalid block number to collect referrals up to")

    # check whitelists
    whitelisted_addresses = []
    with open(whitelist_path, "r") as f:
        for line in f:
            address = line.strip()
            if not w3.isAddress(address):
                raise click.ClickException(f"Invalid address '{address}'")
            whitelisted_addresses.append(Web3.toChecksumAddress(address))

    if not swise_price:
        swise_price = click.prompt(
            "Enter SWISE price (USD)",
            default=get_average_range_price("stakewise", from_date, to_date),
            type=decimal.Decimal,
        )
    if not eth_price:
        eth_price = click.prompt(
            "Enter ETH price (USD)",
            default=get_average_range_price("ethereum", from_date, to_date),
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
        referrer = Web3.toChecksumAddress(item["referrer"])
        if referrer not in whitelisted_addresses:
            continue

        amount = int(
            (int(item["amount"]) * eth_price * referrals_share) / (100 * swise_price)
        )
        total_amount += amount
        referrals.setdefault(referrer, {}).setdefault(token_address, 0)
        referrals[referrer][token_address] += amount

    if not referrals:
        raise click.ClickException("No referrals for the specified period. Exiting...")

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
