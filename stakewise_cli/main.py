import warnings

import click

warnings.filterwarnings("ignore")

from stakewise_cli.commands.create_deposit_data import create_deposit_data  # noqa: E402
from stakewise_cli.commands.create_shard_pubkeys import (  # noqa: E402
    create_shard_pubkeys,
)
from stakewise_cli.commands.get_mnemonic_pubkey import get_mnemonic_pubkey  # noqa: E402
from stakewise_cli.commands.get_pubkey_index import get_pubkey_index  # noqa: E402
from stakewise_cli.commands.sync_local import sync_local  # noqa: E402
from stakewise_cli.commands.sync_vault import sync_vault  # noqa: E402
from stakewise_cli.commands.upload_deposit_data import upload_deposit_data  # noqa: E402
from stakewise_cli.commands.verify_deposit_data import verify_deposit_data  # noqa: E402
from stakewise_cli.commands.verify_shard_pubkeys import (  # noqa: E402
    verify_shard_pubkeys,
)


@click.group()
def cli() -> None:
    pass


cli.add_command(create_deposit_data)
cli.add_command(upload_deposit_data)
cli.add_command(verify_deposit_data)
cli.add_command(sync_vault)
cli.add_command(sync_local)
cli.add_command(create_shard_pubkeys)
cli.add_command(verify_shard_pubkeys)
cli.add_command(get_mnemonic_pubkey)
cli.add_command(get_pubkey_index)

if __name__ == "__main__":
    cli()
