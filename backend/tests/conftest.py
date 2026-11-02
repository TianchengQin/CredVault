import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="credvault-test-"))
STATIC = _TMP / "static"
(STATIC / "assets").mkdir(parents=True)
(STATIC / "index.html").write_text("<!doctype html><title>CredVault</title>")
(_TMP / "outside-secret.txt").write_text("TOP-SECRET")

os.environ.update({
    "DATABASE_URL": f"sqlite:///{(_TMP / 'test.db').as_posix()}",
    "SECRET_KEY": "x" * 64,
    "STATIC_DIR": str(STATIC),
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "admin-password-123",
    "ALLOW_REGISTRATION": "1",
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app import security  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.vault_keys import vault_keys  # noqa: E402

PASSWORD = "correct-horse-battery"
MASTER = "master-password-staple"


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    for limiter in security.ALL_LIMITERS:
        limiter.clear()
    vault_keys.clear()
    with TestClient(app) as c:
        yield c


class Account:
    """A signed-in user with an unlocked vault."""

    def __init__(self, client: TestClient, username: str, *, unlock: bool = True):
        self.client = client
        self.username = username
        r = client.post("/api/auth/register", json={"username": username, "password": PASSWORD})
        assert r.status_code == 201, r.text
        self.token = r.json()["token"]
        self.vault_token = ""
        if unlock:
            r = client.post("/api/vault/setup", json={"master_password": MASTER}, headers=self.auth)
            assert r.status_code == 200, r.text
            self.vault_token = r.json()["vault_token"]

    @property
    def auth(self) -> dict:
        return {"Authorization": f"Bearer {self.token}"}

    @property
    def h(self) -> dict:
        return {**self.auth, "X-Vault-Token": self.vault_token}

    def get(self, url, **kw):
        return self.client.get(url, headers=self.h, **kw)

    def post(self, url, **kw):
        return self.client.post(url, headers=self.h, **kw)

    def put(self, url, **kw):
        return self.client.put(url, headers=self.h, **kw)

    def patch(self, url, **kw):
        return self.client.patch(url, headers=self.h, **kw)

    def delete(self, url, **kw):
        return self.client.delete(url, headers=self.h, **kw)


@pytest.fixture()
def alice(client):
    return Account(client, "alice")


@pytest.fixture()
def bob(client):
    return Account(client, "bob")


def login_admin(client: TestClient) -> dict:
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin-password-123"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}
