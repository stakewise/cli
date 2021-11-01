import warnings

import click

warnings.filterwarnings("ignore")

from operator_cli.cli.generate_proposal import generate_proposal  # noqa: E402
from operator_cli.cli.sync_vault import sync_vault  # noqa: E402


@click.group()
def cli() -> None:
    pass


cli.add_command(generate_proposal)
cli.add_command(sync_vault)

if __name__ == "__main__":
    cli()
