"""Vault lifecycle: set up, unlock, lock. Session-only (never via API token)."""

from typing import Annotated

from fastapi import APIRouter, Header, Request

from .. import audit, schemas
from ..config import settings
from ..deps import DB, CurrentUser
from ..errors import BadRequest, TooManyAttempts, Unauthorized
from ..security import unlock_limiter
from ..services import vault as vault_svc
from ..vault_keys import vault_keys

router = APIRouter(prefix="/api/vault", tags=["vault"])


def _unlocked(user_id: int, key: bytes) -> schemas.VaultUnlocked:
    return schemas.VaultUnlocked(vault_token=vault_keys.put(user_id, key), idle_seconds=vault_keys.idle_seconds)


@router.get("/status", response_model=schemas.VaultStatus)
def status(user: CurrentUser):
    return schemas.VaultStatus(setup_required=not user.vault_initialized)


@router.post("/setup", response_model=schemas.VaultUnlocked)
def setup(body: schemas.MasterPassword, user: CurrentUser, request: Request, db: DB):
    if user.vault_initialized:
        raise BadRequest("Vault already initialized")
    if len(body.master_password) < settings.min_master_password:
        raise BadRequest(f"Master password must be at least {settings.min_master_password} characters")
    key = vault_svc.setup(user, body.master_password)
    audit.record(db, "vault_setup", user=user, request=request)
    return _unlocked(user.id, key)


@router.post("/unlock", response_model=schemas.VaultUnlocked)
def unlock(body: schemas.MasterPassword, user: CurrentUser, request: Request, db: DB):
    if not user.vault_initialized:
        return schemas.VaultUnlocked(setup_required=True)
    limiter_key = f"{audit.client_ip(request)}:{user.id}"
    if wait := unlock_limiter.retry_after(limiter_key):
        raise TooManyAttempts(wait, "unlock attempts")

    key = vault_svc.try_unlock(user, body.master_password)
    if key is None:
        unlock_limiter.fail(limiter_key)
        audit.record(db, "vault_unlock_failed", user=user, request=request)
        raise Unauthorized("Wrong master password")

    unlock_limiter.reset(limiter_key)
    vault_svc.on_unlocked(db, user, key)
    audit.record(db, "vault_unlocked", user=user, request=request)
    return _unlocked(user.id, key)


@router.post("/lock", response_model=schemas.Ok)
def lock(user: CurrentUser, request: Request, db: DB, x_vault_token: Annotated[str | None, Header()] = None):
    vault_keys.revoke(x_vault_token)
    audit.record(db, "vault_locked", user=user, request=request)
    return schemas.Ok()
