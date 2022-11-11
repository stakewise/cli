import json
import os
from os import mkdir
from os.path import exists, join
from typing import Dict, List

import click
import yaml

from stakewise_cli.networks import AVAILABLE_NETWORKS, MAINNET, NETWORKS
from stakewise_cli.storages.database import Database, check_db_connection
from stakewise_cli.utils import is_lists_equal
from stakewise_cli.validators import validate_db_uri, validate_env_name

PUBLIC_KEYS_CSV_FILENAME = "validator_keys.csv"
LIGHTHOUSE_CONFIG_FILENAME = "validator_definitions.yml"
SIGNER_CONFIG_FILENAME = "signer_keys.yml"
SIGNER_PROPOSER_CONFIG_FILENAME = "proposerConfig.json"
WEB3SIGNER_URL_ENV = "WEB3SIGNER_URL"


@click.command(help="Synchronizes validator public keys from the database")
@click.option(
    "--network",
    default=MAINNET,
    help="The network to generate the deposit data for",
    prompt="Enter the network name",
    type=click.Choice(
        AVAILABLE_NETWORKS,
        case_sensitive=False,
    ),
)
@click.option(
    "--db-url",
    help="The database connection address.",
    prompt="Enter the database connection string, ex. 'postgresql://username:pass@hostname/dbname'",
    callback=validate_db_uri,
)
@click.option(
    "--index",
    help="The validator index.",
    prompt="Enter the validator index.",
)
@click.option(
    "--output-dir",
    help="The folder where validator keys will be saved.",
    type=click.Path(exists=False, file_okay=False, dir_okay=True),
)
@click.option(
    "--web3signer-url-env",
    help="The environment variable with web3signer url.",
    default=WEB3SIGNER_URL_ENV,
    callback=validate_env_name,
)
@click.option(
    "--solo-fees-file",
    help="The path to solo validator's fee distribution path",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
@click.option(
    "--proposal-builder-enabled",
    help="Enable proposal builder for Teku and Prysm clients.",
    default=True,
    type=click.BOOL,
)
def sync_validator_keys(
    network: str,
    db_url: str,
    index: int,
    output_dir: str,
    web3signer_url_env: str,
    solo_fees_file: str,
    proposal_builder_enabled: bool,
) -> None:
    """
    The command is running by the init container in validator pods.
    Fetch public keys for a specific validator index and store them in the output_dir
    """
    check_db_connection(db_url)

    database = Database(db_url=db_url)
    keys = database.fetch_public_keys_by_validator_index(validator_index=index)

    if not exists(output_dir):
        mkdir(output_dir)

    # check current public keys CSV
    lighthouse_filename = join(output_dir, LIGHTHOUSE_CONFIG_FILENAME)
    if exists(lighthouse_filename):
        with open(lighthouse_filename) as f:
            current_keys = _load_lighthouse_config(f)
        if is_lists_equal(keys, current_keys):
            click.secho(
                "Keys already synced to the last version.\n",
                bold=True,
                fg="green",
            )
            return

    default_fee_recipient = NETWORKS[network]["FEE_DISTRIBUTION_CONTRACT_ADDRESS"]
    solo_fee_mapping = {}
    if solo_fees_file:
        with open(solo_fees_file) as f:
            solo_fee_mapping = json.load(f)

    # save lighthouse config
    web3signer_url = os.environ[web3signer_url_env]
    lighthouse_config = _generate_lighthouse_config(
        public_keys=keys,
        web3signer_url=web3signer_url,
        default_fee_recipient=default_fee_recipient,
        solo_fee_mapping=solo_fee_mapping,
        builder_proposals=proposal_builder_enabled,
    )
    with open(join(output_dir, LIGHTHOUSE_CONFIG_FILENAME), "w") as f:
        f.write(lighthouse_config)

    # save teku/prysm config
    signer_keys_config = _generate_signer_keys_config(public_keys=keys)
    with open(join(output_dir, SIGNER_CONFIG_FILENAME), "w") as f:
        f.write(signer_keys_config)
    proposer_config = _generate_proposer_config(
        default_fee_recipient=default_fee_recipient,
        solo_fee_mapping=solo_fee_mapping,
        proposal_builder_enabled=proposal_builder_enabled,
    )
    with open(join(output_dir, SIGNER_PROPOSER_CONFIG_FILENAME), "w") as f:
        f.write(proposer_config)

    click.secho(
        f"The validator now uses {len(keys)} public keys.\n",
        bold=True,
        fg="green",
    )


def _generate_lighthouse_config(
    public_keys: List[str],
    web3signer_url: str,
    default_fee_recipient: str,
    solo_fee_mapping: Dict[str, str],
    proposal_builder_enabled: bool
) -> str:
    """
    Generate config for Lighthouse clients
    """
    items = [
        {
            "enabled": True,
            "voting_public_key": public_key,
            "type": "web3signer",
            "url": web3signer_url,
            "suggested_fee_recipient": solo_fee_mapping.get(
                public_key, default_fee_recipient
            ),
            "builder_proposals": proposal_builder_enabled,
        }
        for public_key in public_keys
    ]

    return yaml.dump(items, explicit_start=True)


def _load_lighthouse_config(file) -> List[str]:
    """
    Load config for Lighthouse clients
    """
    try:
        items = yaml.safe_load(file)
        return [item.get("voting_public_key") for item in items]
    except yaml.YAMLError:
        return []


def _generate_signer_keys_config(public_keys: List[str]) -> str:
    """
    Generate config for Teku and Prysm clients
    """
    keys = ",".join([f'"{public_key}"' for public_key in public_keys])
    return f"""validators-external-signer-public-keys: [{keys}]"""


def _generate_proposer_config(
    default_fee_recipient: str,
    solo_fee_mapping: Dict[str, str],
    proposal_builder_enabled: bool,
) -> str:
    """
    Generate config for Teku and Prysm clients
    """
    config = {
        "proposer_config": {
            **{
                public_key: {
                    "fee_recipient": fee_recipient,
                    "builder": {
                        "enabled": proposal_builder_enabled,
                    },
                }
                for public_key, fee_recipient in solo_fee_mapping.items()
            }
        },
        "default_config": {
            "fee_recipient": default_fee_recipient,
            "builder": {
                "enabled": proposal_builder_enabled,
            },
        },
    }
    return json.dumps(config)
