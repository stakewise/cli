import decimal

import requests


def get_coinbase_price(token):
    try:
        r = requests.get(
            f"https://api.coinbase.com/v2/exchange-rates?currency={token}", timeout=3
        )
        if r and r.status_code == 200:
            price = r.json().get("data").get("rates").get("USDT")
            return decimal.Decimal(price)
    except BaseException:
        pass
