from typing import List
from urllib.parse import urlparse

import click
import psycopg2
from psycopg2.extras import execute_values

from stakewise_cli.typings import DatabaseKeyRecord


class Database:
    def __init__(self, db_url: str):
        self.db_url = db_url

    def update_keys(self, keys: List[DatabaseKeyRecord]) -> None:
        """Updates database records to new state."""
        self.init_db()
        self.save_to_db(keys)

    def init_db(self) -> None:
        conn = _get_db_connection(self.db_url)
        cur = conn.cursor()
        cur.execute(
            """
            DROP TABLE IF EXISTS keys;
            CREATE TABLE keys (
                public_key TEXT UNIQUE NOT NULL,
                private_key TEXT UNIQUE NOT NULL,
                nonce TEXT NOT NULL,
                validator_index TEXT NOT NULL)
            ;"""
        )

        conn.commit()
        cur.close()
        conn.close()

    def save_to_db(self, keys: List[DatabaseKeyRecord]) -> None:
        conn = _get_db_connection(self.db_url)
        cur = conn.cursor()
        execute_values(
            cur,
            "INSERT INTO keys (public_key, private_key, nonce, validator_index) VALUES %s",
            [
                (x["public_key"], x["private_key"], x["nonce"], x["validator_index"])
                for x in keys
            ],
        )
        conn.commit()
        cur.close()
        conn.close()

    def fetch_public_keys_by_validator_index(self, validator_index: int) -> List[str]:
        conn = _get_db_connection(self.db_url)
        cur = conn.cursor()
        cur.execute(
            "select public_key from keys where validator_index= %s", (validator_index,)
        )
        rows = cur.fetchall()
        return [row[0] for row in rows]

    def fetch_keys(self) -> List[DatabaseKeyRecord]:
        conn = _get_db_connection(self.db_url)
        cur = conn.cursor()
        cur.execute("select * from keys")
        rows = cur.fetchall()
        return [
            DatabaseKeyRecord(
                public_key=row[0],
                private_key=row[1],
                nonce=row[2],
                validator_index=row[3],
            )
            for row in rows
        ]


def check_db_connection(db_url):
    connection = _get_db_connection(db_url=db_url)
    try:
        cur = connection.cursor()
        cur.execute("SELECT 1")
    except psycopg2.OperationalError as e:
        raise click.ClickException(
            f"Error: failed to connect to the database server with provided URL. Error details: {e}",
        )


def _get_db_connection(db_url):
    result = urlparse(db_url)
    return psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
    )
