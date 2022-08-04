import os
import re

import click
from eth_utils import is_address, to_checksum_address


# click callbacks
def validate_operator_address(ctx, param, value):
    return validate_operator_address_prompt(value)


def validate_db_uri(ctx, param, value):
    pattern = re.compile(r".+:\/\/.+:.*@.+\/.+")
    if not pattern.match(value):
        raise click.BadParameter("Invalid database connection string")
    return value


def validate_env_name(ctx, param, value):
    if not os.getenv(value):
        raise click.BadParameter(f"Empty environment variable {value}")
    return value


# click prompts
def validate_operator_address_prompt(value):
    try:
        if is_address(value):
            return to_checksum_address(value)
    except ValueError:
        pass

    raise click.BadParameter("Invalid Ethereum address")
