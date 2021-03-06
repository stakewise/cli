from web3 import Web3


def generate_referrals_swise_specification(
    from_block,
    to_block,
    total_amount,
    token_address,
    swise_price,
    eth_price,
    ipfs_url,
    referral_share,
) -> str:
    specification = f"""
# Referral Rewards Distribution

Distribute {Web3.fromWei(total_amount, "ether")} SWISE to referrers specified in {ipfs_url}.

The rewards distribution was calculated with the following parameters:
* From block number: {from_block}
* To block number: {to_block}
* Distributed token: {token_address}
* Distributed token price (USD): {swise_price}
* ETH price (USD): {eth_price}
* Referral share (%): {referral_share}
"""

    return specification
