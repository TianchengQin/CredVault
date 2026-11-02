"""FastAPI dependencies: who is calling, and which vault key they hold."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import crypto, security
from .database import get_db
from .errors import Forbidden, SessionExpired, Unauthorized
from .models import ApiToken, User, utcnow
from .vault_keys import vault_keys

DB = Annotated[Session, Depends(get_db)]

_bearer = HTTPBearer(auto_error=False)
API_TOKEN_KDF_COST = 2  # time_cost used to wrap vault keys for API tokens


def _user_from_bearer(creds: HTTPAuthorizationCredentials | None, db: Session) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise SessionExpired("Authentication required")
    user_id, version = security.decode_session_token(creds.credentials)
    user = db.get(User, user_id)
    # token_version is bumped on password change/reset, revoking older sessions
    if user is None or (user.token_version or 0) != version:
        raise SessionExpired()
    return user


def current_user(
    db: DB,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    return _user_from_bearer(creds, db)


def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if not user.is_admin:
        raise Forbidden("Admin privileges required")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
AdminUser = Annotated[User, Depends(admin_user)]


# ---------------------------------------------------------------- vault access

@dataclass
class VaultContext:
    user: User
    key: bytes
    permission: str  # "read" | "write"
    via_api_token: bool = False
    vault_token: str | None = None

    def require_write(self) -> "VaultContext":
        if self.permission != "write":
            raise Forbidden("This API token is read-only")
        return self

    def require_session(self) -> "VaultContext":
        if self.via_api_token:
            raise Forbidden("Not available to API tokens")
        return self


def _context_from_api_token(secret: str, db: Session) -> VaultContext:
    token = db.scalar(select(ApiToken).where(ApiToken.token_hash == crypto.sha256_hex(secret)))
    if token is None:
        raise Unauthorized("Invalid API token")
    try:
        wrap_key = crypto.derive_key(secret, crypto.b64d(token.token_salt), time_cost=API_TOKEN_KDF_COST)
        vault_key = crypto.decrypt_bytes(token.key_enc, token.nonce, wrap_key)
    except Exception:
        raise Unauthorized("Invalid API token")
    token.last_used_at = utcnow()
    db.commit()
    return VaultContext(user=token.owner, key=vault_key, permission=token.permission, via_api_token=True)


def vault_context(
    db: DB,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    x_api_token: Annotated[str | None, Header()] = None,
    x_vault_token: Annotated[str | None, Header()] = None,
) -> VaultContext:
    """Either an API token (``X-API-Token``) or a session + unlocked vault (``X-Vault-Token``)."""
    if x_api_token:
        return _context_from_api_token(x_api_token, db)
    user = _user_from_bearer(creds, db)
    key = vault_keys.get(x_vault_token, user.id)
    return VaultContext(user=user, key=key, permission="write", vault_token=x_vault_token)


def writable_vault(ctx: Annotated[VaultContext, Depends(vault_context)]) -> VaultContext:
    return ctx.require_write()


def session_vault(ctx: Annotated[VaultContext, Depends(vault_context)]) -> VaultContext:
    return ctx.require_session()


Vault = Annotated[VaultContext, Depends(vault_context)]
WritableVault = Annotated[VaultContext, Depends(writable_vault)]
SessionVault = Annotated[VaultContext, Depends(session_vault)]
