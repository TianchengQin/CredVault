"""Existing installs must keep working after the upgrade."""

from sqlalchemy import create_engine, inspect, text

from app import crypto, migrations
from app.database import SessionLocal
from app.models import SharedCredential, User

from .conftest import MASTER
from .test_api import CRED


def test_legacy_schema_gets_new_columns(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'old.db').as_posix()}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username VARCHAR, login_hash VARCHAR, is_admin INTEGER)"))
        conn.execute(text("CREATE TABLE credentials (id INTEGER PRIMARY KEY, user_id INTEGER, name VARCHAR, encrypted_payload TEXT, nonce VARCHAR)"))
    migrations.upgrade(engine)
    migrations.upgrade(engine)  # idempotent
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    assert {"token_version", "totp_last_counter", "public_key", "must_change_password"} <= cols
    assert "favorite" in {c["name"] for c in inspect(engine).get_columns("credentials")}


def test_legacy_share_is_resealed_on_unlock(client, alice, bob):
    """Old shares were encrypted with the recipient's vault key; unlocking upgrades them."""
    cid = alice.post("/api/vault/credentials", json=CRED).json()["id"]
    with SessionLocal() as db:
        b = db.query(User).filter_by(username="bob").one()
        bob_key = crypto.derive_key(MASTER, crypto.b64d(b.vault_salt))
        ct, nonce = crypto.encrypt_json({"secret": "legacy", "url": "", "username": "", "description": ""}, bob_key)
        a = db.query(User).filter_by(username="alice").one()
        db.add(SharedCredential(owner_user_id=a.id, recipient_user_id=b.id, source_credential_id=cid,
                                permission="read", name="old", encrypted_payload=ct, nonce=nonce))
        db.commit()

    assert bob.get("/api/vault/shared").json()[0]["secret"] == "legacy"  # legacy read path
    bob.post("/api/vault/lock")
    bob.vault_token = client.post("/api/vault/unlock", json={"master_password": MASTER}, headers=bob.auth).json()["vault_token"]
    with SessionLocal() as db:
        assert db.query(SharedCredential).one().ephemeral_pub is not None
    assert bob.get("/api/vault/shared").json()[0]["secret"] == "legacy"
