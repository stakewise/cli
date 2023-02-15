import warnings

import click

warnings.filterwarnings("ignore")

from stakewise_cli.commands.sync_db import sync_db  # noqa: E402


@click.group()
def cli() -> None:
    pass


cli.add_command(sync_db)

if __name__ == "__main__":
    cli()
