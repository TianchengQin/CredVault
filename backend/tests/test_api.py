import time

from app import crypto
from app.models import User

from .conftest import MASTER, PASSWORD, Account, login_admin

CRED = {"name": "db", "secret": "s3cret", "url": "https://db.local", "username": "root", "category": "infra"}


# ---------------------------------------------------------------- auth

def test_login_and_me(client, alice):
    r = client.post("/api/auth/login", json={"username": "ALICE", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {r.json()['token']}"})
    assert me.json()["username"] == "alice"


def test_wrong_password_and_unknown_user_look_the_same(client, alice):
    a = client.post("/api/auth/login", json={"username": "alice", "password": "nope"})
    b = client.post("/api/auth/login", json={"username": "ghost", "password": "nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_login_lockout(client, alice):
    for _ in range(5):
        client.post("/api/auth/login", json={"username": "alice", "password": "bad"})
    r = client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD})
    assert r.status_code == 429 and "Retry-After" in r.headers


def test_registration_validates_input(client):
    assert client.post("/api/auth/register", json={"username": "x", "password": PASSWORD}).status_code == 422
    assert client.post("/api/auth/register", json={"username": "<script>", "password": PASSWORD}).status_code == 422
    assert client.post("/api/auth/register", json={"username": "carol", "password": "short"}).status_code == 400


def test_duplicate_username_case_insensitive(client, alice):
    r = client.post("/api/auth/register", json={"username": "Alice", "password": PASSWORD})
    assert r.status_code == 409


def _enable_2fa(client, acct: Account) -> str:
    secret = client.post("/api/auth/2fa/setup", headers=acct.auth).json()["secret"]
    code = crypto._hotp(secret, int(time.time()) // 30)
    assert client.post("/api/auth/2fa/verify", json={"code": code}, headers=acct.auth).status_code == 200
    return secret


def test_mfa_ticket_is_not_a_session(client, alice):
    """Regression: the password-only MFA ticket used to be accepted as a full session."""
    _enable_2fa(client, alice)
    r = client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD})
    body = r.json()
    assert body["mfa_required"] and body["token"] == ""
    ticket = {"Authorization": f"Bearer {body['mfa_token']}"}
    assert client.get("/api/auth/me", headers=ticket).status_code == 401
    assert client.get("/api/vault/status", headers=ticket).status_code == 401


def test_totp_code_cannot_be_replayed(client, alice):
    secret = _enable_2fa(client, alice)
    used = crypto._hotp(secret, int(time.time()) // 30)  # already burned by /verify
    ticket = client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}).json()["mfa_token"]
    r = client.post("/api/auth/2fa/confirm", json={"mfa_token": ticket, "code": used})
    assert r.status_code == 401


def test_2fa_setup_does_not_leak_active_secret(client, alice):
    _enable_2fa(client, alice)
    assert client.post("/api/auth/2fa/setup", headers=alice.auth).status_code == 400


def test_mfa_confirm_is_rate_limited(client, alice):
    _enable_2fa(client, alice)
    ticket = client.post("/api/auth/login", json={"username": "alice", "password": PASSWORD}).json()["mfa_token"]
    for _ in range(5):
        client.post("/api/auth/2fa/confirm", json={"mfa_token": ticket, "code": "000000"})
    assert client.post("/api/auth/2fa/confirm", json={"mfa_token": ticket, "code": "000000"}).status_code == 429


def test_password_change_revokes_sessions_and_vault(client, alice):
    old = alice.h
    r = client.post("/api/auth/change-password", headers=alice.auth,
                    json={"current_password": PASSWORD, "new_password": "a-brand-new-password"})
    assert r.status_code == 200 and r.json()["token"]
    expired = client.get("/api/auth/me", headers=old)
    assert expired.status_code == 401 and expired.headers.get("X-Session-Expired") == "1"
    fresh = {"Authorization": f"Bearer {r.json()['token']}", "X-Vault-Token": alice.vault_token}
    assert client.get("/api/vault/credentials", headers=fresh).status_code == 401  # vault re-locked


# ---------------------------------------------------------------- vault + credentials

def test_vault_requires_strong_master(client):
    acct = Account(client, "dave", unlock=False)
    r = client.post("/api/vault/setup", json={"master_password": "short"}, headers=acct.auth)
    assert r.status_code == 400


def test_credential_crud(alice):
    created = alice.post("/api/vault/credentials", json=CRED)
    assert created.status_code == 201
    cid = created.json()["id"]
    assert alice.get("/api/vault/credentials").json()[0]["secret"] == "s3cret"

    r = alice.patch(f"/api/vault/credentials/{cid}", json={"favorite": True})
    assert r.json()["favorite"] is True and r.json()["secret"] == "s3cret"

    r = alice.put(f"/api/vault/credentials/{cid}", json={**CRED, "secret": "new"})
    assert r.json()["secret"] == "new"

    assert alice.delete(f"/api/vault/credentials/{cid}").status_code == 200
    assert alice.get(f"/api/vault/credentials/{cid}").status_code == 404


def test_secrets_are_encrypted_at_rest(client, alice):
    alice.post("/api/vault/credentials", json=CRED)
    from app.database import SessionLocal
    from app.models import Credential
    with SessionLocal() as db:
        row = db.query(Credential).one()
        assert "s3cret" not in row.encrypted_payload


def test_vault_token_is_bound_to_its_user(alice, bob):
    """Regression: any user's vault token used to work with any session."""
    r = alice.client.get("/api/vault/credentials", headers={**alice.auth, "X-Vault-Token": bob.vault_token})
    assert r.status_code == 401 and r.headers.get("X-Vault-Locked") == "1"


def test_users_cannot_touch_each_others_credentials(alice, bob):
    cid = alice.post("/api/vault/credentials", json=CRED).json()["id"]
    assert bob.get(f"/api/vault/credentials/{cid}").status_code == 404
    assert bob.delete(f"/api/vault/credentials/{cid}").status_code == 404


def test_lock_and_unlock(alice):
    alice.post("/api/vault/credentials", json=CRED)
    alice.post("/api/vault/lock")
    assert alice.get("/api/vault/credentials").status_code == 401
    wrong = alice.client.post("/api/vault/unlock", json={"master_password": "wrong-wrong-wrong"}, headers=alice.auth)
    assert wrong.status_code == 401 and "X-Session-Expired" not in wrong.headers  # must not sign the UI out
    r = alice.client.post("/api/vault/unlock", json={"master_password": MASTER}, headers=alice.auth)
    alice.vault_token = r.json()["vault_token"]
    assert len(alice.get("/api/vault/credentials").json()) == 1


def test_input_limits(alice):
    assert alice.post("/api/vault/credentials", json={**CRED, "name": "x" * 201}).status_code == 422
    assert alice.post("/api/vault/credentials", json={**CRED, "evil": 1}).status_code == 422


def test_export_import_roundtrip(alice):
    alice.post("/api/vault/credentials", json=CRED)
    dump = alice.post("/api/vault/export").json()
    assert dump["items"][0]["secret"] == "s3cret"
    r = alice.post("/api/vault/import", json={"items": dump["items"]})
    assert r.json()["imported"] == 1
    assert len(alice.get("/api/vault/credentials").json()) == 2


# ---------------------------------------------------------------- API tokens

def _token(acct: Account, permission: str) -> dict:
    r = acct.post("/api/tokens", json={"name": f"agent-{permission}", "permission": permission})
    assert r.status_code == 201
    return {"X-API-Token": r.json()["token"]}


def test_api_tokens(client, alice):
    alice.post("/api/vault/credentials", json=CRED)
    read, write = _token(alice, "read"), _token(alice, "write")

    assert client.get("/api/vault/credentials", headers=read).json()[0]["secret"] == "s3cret"
    assert client.post("/api/vault/credentials", json=CRED, headers=read).status_code == 403
    assert client.post("/api/vault/credentials", json=CRED, headers=write).status_code == 201

    # tokens can't manage tokens or export the vault
    tid = alice.get("/api/tokens").json()[1]["id"]
    assert client.delete(f"/api/tokens/{tid}", headers=read).status_code == 403
    assert client.get("/api/tokens", headers=write).status_code == 403
    assert client.post("/api/vault/export", headers=write).status_code == 403
    assert client.get("/api/vault/credentials", headers={"X-API-Token": "bogus"}).status_code == 401


def test_revoked_token_stops_working(client, alice):
    tok = _token(alice, "read")
    tid = alice.get("/api/tokens").json()[0]["id"]
    alice.delete(f"/api/tokens/{tid}")
    assert client.get("/api/vault/credentials", headers=tok).status_code == 401


# ---------------------------------------------------------------- sharing

def test_share_with_offline_recipient(client, alice, bob):
    cid = alice.post("/api/vault/credentials", json=CRED).json()["id"]
    bob.post("/api/vault/lock")  # recipient no longer needs to be unlocked

    r = alice.post(f"/api/vault/credentials/{cid}/share", json={"username": "bob", "permission": "read"})
    assert r.status_code == 201, r.text
    share_id = r.json()["id"]

    bob.vault_token = client.post("/api/vault/unlock", json={"master_password": MASTER}, headers=bob.auth).json()["vault_token"]
    shared = bob.get("/api/vault/shared").json()
    assert shared[0]["secret"] == "s3cret" and shared[0]["owner"] == "alice"

    # read-only share can't be edited; upgrading permission allows it
    assert bob.put(f"/api/vault/shared/{share_id}", json={**CRED, "secret": "x"}).status_code == 403
    alice.patch(f"/api/vault/credentials/{cid}/shares/{share_id}", json={"permission": "write"})
    assert bob.put(f"/api/vault/shared/{share_id}", json={**CRED, "secret": "x"}).json()["secret"] == "x"

    # a third party can't see it
    carol = Account(client, "carol")
    assert carol.get(f"/api/vault/shared/{share_id}").status_code == 404


def test_share_survives_source_deletion(alice, bob):
    cid = alice.post("/api/vault/credentials", json=CRED).json()["id"]
    alice.post(f"/api/vault/credentials/{cid}/share", json={"username": "bob", "permission": "read"})
    alice.delete(f"/api/vault/credentials/{cid}")
    assert bob.get("/api/vault/shared").json()[0]["secret"] == "s3cret"


def test_cannot_share_to_user_without_vault(client, alice):
    Account(client, "erin", unlock=False)
    cid = alice.post("/api/vault/credentials", json=CRED).json()["id"]
    r = alice.post(f"/api/vault/credentials/{cid}/share", json={"username": "erin", "permission": "read"})
    assert r.status_code == 400


# ---------------------------------------------------------------- admin

def test_non_admin_is_forbidden(alice):
    assert alice.get("/api/users").status_code == 403
    assert alice.get("/api/users/audit-log").status_code == 403


def test_admin_reset_password_revokes_sessions(client, alice):
    admin = login_admin(client)
    uid = next(u["id"] for u in client.get("/api/users", headers=admin).json() if u["username"] == "alice")
    temp = client.post(f"/api/users/{uid}/reset-password", headers=admin).json()["temp_password"]
    assert client.get("/api/auth/me", headers=alice.auth).status_code == 401
    r = client.post("/api/auth/login", json={"username": "alice", "password": temp})
    assert r.json()["must_change_password"] is True


def test_admin_delete_user_with_shares(client, alice, bob):
    cid = alice.post("/api/vault/credentials", json=CRED).json()["id"]
    alice.post(f"/api/vault/credentials/{cid}/share", json={"username": "bob", "permission": "read"})
    admin = login_admin(client)
    uid = next(u["id"] for u in client.get("/api/users", headers=admin).json() if u["username"] == "alice")
    assert client.delete(f"/api/users/{uid}", headers=admin).status_code == 200
    assert bob.get("/api/vault/shared").json() == []
    assert client.get("/api/auth/me", headers=alice.auth).status_code == 401
    assert any(e["action"] == "user_delete" for e in client.get("/api/users/audit-log", headers=admin).json())


def test_admin_reset_vault(client, alice, bob):
    cid = bob.post("/api/vault/credentials", json=CRED).json()["id"]
    bob.post(f"/api/vault/credentials/{cid}/share", json={"username": "alice", "permission": "read"})
    admin = login_admin(client)
    uid = next(u["id"] for u in client.get("/api/users", headers=admin).json() if u["username"] == "alice")
    client.post(f"/api/users/{uid}/reset-vault", headers=admin)
    assert alice.get("/api/vault/credentials").status_code == 401  # unlocked key revoked
    assert client.get("/api/vault/status", headers=alice.auth).json()["setup_required"] is True


def test_admin_cannot_target_self(client):
    admin = login_admin(client)
    me = next(u for u in client.get("/api/users", headers=admin).json() if u["is_admin"])
    assert client.delete(f"/api/users/{me['id']}", headers=admin).status_code == 400


# ---------------------------------------------------------------- http hardening

def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert r.headers["Cache-Control"] == "no-store"


def test_no_wildcard_cors(client):
    r = client.get("/api/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_spa_blocks_path_traversal(client):
    assert client.get("/").status_code == 200
    for path in ("/..%2Foutside-secret.txt", "/%2e%2e/outside-secret.txt", "/assets/../../outside-secret.txt"):
        assert "TOP-SECRET" not in client.get(path).text


def test_unknown_api_route_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.json()["detail"] == "Not found"


def test_docs_disabled_by_default(client):
    assert client.get("/docs").headers.get("content-type", "").startswith("text/html")  # SPA, not swagger
    assert "swagger" not in client.get("/docs").text.lower()
