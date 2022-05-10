import decimal
from datetime import datetime, timedelta

import backoff
import click
import requests


@backoff.on_exception(backoff.expo, Exception, max_time=5)
def request_day_price(coin_id, date):
    r = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/history?date={date}&localization=en",
        timeout=2,
    )
    if r and r.status_code == 200:
        price = r.json().get("market_data").get("current_price").get("usd")
        return decimal.Decimal(price)


def get_average_range_price(coin_id: str, from_date: int, to_date: int):
    try:
        from_date = datetime.fromtimestamp(from_date)
        to_date = datetime.fromtimestamp(to_date)

        days = []
        base = from_date
        while base < to_date:
            date = datetime.combine(base.date(), datetime.min.time())
            days.append(date.strftime("%d-%m-%Y"))
            base += timedelta(days=1)
        daily_prices = []
        for day in days:
            daily_prices.append(request_day_price(coin_id, day))
        return sum(daily_prices) / len(daily_prices)
    except BaseException as e:
        click.echo(e)
