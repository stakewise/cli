import warnings

import click

warnings.filterwarnings("ignore")

from operator_cli.commands.generate_proposal import generate_proposal  # noqa: E402
from operator_cli.commands.sync_local import sync_local  # noqa: E402
from operator_cli.commands.sync_vault import sync_vault  # noqa: E402


@click.group()
def cli() -> None:
    pass


cli.add_command(generate_proposal)
cli.add_command(sync_vault)
cli.add_command(sync_local)

if __name__ == "__main__":
    cli()
