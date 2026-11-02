"""Minimal, idempotent, database-agnostic schema upgrades.

``create_all`` creates missing tables; this adds columns introduced after a
table already existed. Each entry is (table, column, SQL type + default).
"""

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

log = logging.getLogger("credvault.migrations")

_ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("users", "totp_secret", "VARCHAR"),
    ("users", "totp_enabled", "INTEGER DEFAULT 0"),
    ("users", "must_change_password", "INTEGER DEFAULT 0"),
    ("users", "token_version", "INTEGER DEFAULT 0"),
    ("users", "totp_last_counter", "INTEGER DEFAULT 0"),
    ("users", "public_key", "VARCHAR"),
    ("users", "private_key_enc", "TEXT"),
    ("users", "private_key_nonce", "VARCHAR"),
    ("credentials", "category", "VARCHAR(64) DEFAULT ''"),
    ("credentials", "favorite", "INTEGER DEFAULT 0"),
    ("shared_credentials", "ephemeral_pub", "VARCHAR"),
]


def upgrade(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    existing = {t: {c["name"] for c in inspector.get_columns(t)} for t in tables}
    with engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            if table in tables and column not in existing[table]:
                # identifiers come from the constant list above, never from input
                conn.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {ddl}'))
                log.info("added column %s.%s", table, column)
