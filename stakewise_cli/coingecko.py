import decimal
import statistics
from datetime import datetime, timedelta

import backoff
import click
import requests


@backoff.on_exception(backoff.expo, Exception, max_time=120)
def request_day_price(coin_id, date):
    r = requests.get(
        f"https://api.coingecko.com/api/v3/coins/{coin_id}/history?date={date}&localization=en",
        timeout=2,
    )
    price = r.json().get("market_data").get("current_price").get("usd")
    return decimal.Decimal(price)


def get_average_range_price(coin_id: str, from_timestamp: int, to_timestamp: int):
    from_date = datetime.fromtimestamp(from_timestamp)
    to_date = datetime.fromtimestamp(to_timestamp)

    days = []
    base = from_date
    while base < to_date:
        date = datetime.combine(base.date(), datetime.min.time())
        days.append(date.strftime("%d-%m-%Y"))
        base += timedelta(days=1)

    prices = []
    with click.progressbar(
        days,
        label=f"Fetching {coin_id} average token price\t\t",
        show_percent=False,
        show_pos=True,
    ) as _days:
        for day in _days:
            try:
                prices.append(request_day_price(coin_id, day))
            except AttributeError:
                click.secho(
                    f"Failed to fetch price at {day}",
                    bold=True,
                    fg="red",
                )

    if not prices:
        return 0

    return round(statistics.median(prices), 4)
