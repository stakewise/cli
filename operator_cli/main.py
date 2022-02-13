import warnings

import click

warnings.filterwarnings("ignore")

from operator_cli.commands.create_deposit_data import create_deposit_data  # noqa: E402
from operator_cli.commands.sync_vault import sync_vault  # noqa: E402
from operator_cli.commands.upload_deposit_data import upload_deposit_data  # noqa: E402


@click.group()
def cli() -> None:
    pass


cli.add_command(create_deposit_data)
cli.add_command(upload_deposit_data)
cli.add_command(sync_vault)

if __name__ == "__main__":
    cli()
