import base64
from dataclasses import dataclass
from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from .database import get_db
from . import auth, crypto
from .models import User, ApiToken


@dataclass
class VaultContext:
    user: User
    key: bytes
    permission: str  # "read" | "write"
    via_api_token: bool = False


def _context_from_session(request: Request, db: Session) -> VaultContext | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    jwt_token = auth_header.split(" ", 1)[1].strip()
    user_id = auth.decode_token(jwt_token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    vault_token = request.headers.get("X-Vault-Token")
    key = auth.vault_store.get(vault_token)
    return VaultContext(user=user, key=key, permission="write")


def _context_from_api_token(request: Request, db: Session) -> VaultContext | None:
    secret = request.headers.get("X-API-Token")
    if not secret:
        return None
    tok_hash = auth.hash_api_token(secret)
    token = db.query(ApiToken).filter(ApiToken.token_hash == tok_hash).first()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")
    salt = base64.b64decode(token.token_salt)
    token_key = auth.derive_token_key(secret, salt)
    try:
        vault_key = crypto.decrypt_bytes(token.key_enc, token.nonce, token_key)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")
    token.last_used_at = datetime.utcnow()
    db.commit()
    return VaultContext(
        user=token.owner, key=vault_key, permission=token.permission, via_api_token=True
    )


def get_vault_context(request: Request, db: Session = Depends(get_db)) -> VaultContext:
    ctx = _context_from_api_token(request, db) or _context_from_session(request, db)
    if ctx is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return ctx


def require_write(ctx: VaultContext) -> VaultContext:
    if ctx.permission != "write":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="API token is read-only")
    return ctx
