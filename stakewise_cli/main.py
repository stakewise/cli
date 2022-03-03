import warnings

import click

warnings.filterwarnings("ignore")

from stakewise_cli.commands.create_deposit_data import create_deposit_data  # noqa: E402
from stakewise_cli.commands.sync_local import sync_local  # noqa: E402
from stakewise_cli.commands.sync_vault import sync_vault  # noqa: E402
from stakewise_cli.commands.upload_deposit_data import upload_deposit_data  # noqa: E402
from stakewise_cli.commands.verify_committee_file import (  # noqa: E402
    verify_committee_file,
)


@click.group()
def cli() -> None:
    pass


cli.add_command(create_deposit_data)
cli.add_command(upload_deposit_data)
cli.add_command(sync_vault)
cli.add_command(sync_local)
cli.add_command(verify_committee_file)

if __name__ == "__main__":
    cli()