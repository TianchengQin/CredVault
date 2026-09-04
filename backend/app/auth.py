import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from . import crypto

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24h session
MFA_TOKEN_EXPIRE_MINUTES = 5  # short-lived token exchanged for a real session

security = HTTPBearer()


# ---- login password hashing (bcrypt) ----
def hash_login_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_login_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False


# ---- JWT session tokens ----
def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")


def create_mfa_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=MFA_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire, "typ": "mfa"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_mfa_token(token: str) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("typ") != "mfa":
            raise ValueError("not an mfa token")
        return int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA verification expired, sign in again")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    user_id = decode_token(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# ---- in-memory vault key store (per unlocked session) ----
# Maps a vault token to the derived AES key. Keys live in memory only.
class VaultKeyStore:
    def __init__(self, ttl_seconds: int = 1800):
        self._keys: dict[str, tuple[bytes, float]] = {}
        self.ttl_seconds = ttl_seconds

    def put(self, key: bytes) -> str:
        token = secrets.token_urlsafe(32)
        self._keys[token] = (key, datetime.now(timezone.utc).timestamp() + self.ttl_seconds)
        return token

    def get(self, token: str | None) -> bytes:
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vault not unlocked")
        entry = self._keys.get(token)
        if entry is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vault not unlocked or expired")
        key, expires = entry
        if datetime.now(timezone.utc).timestamp() > expires:
            self._keys.pop(token, None)
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vault locked due to inactivity, unlock again")
        return key

    def revoke(self, token: str | None) -> None:
        if token:
            self._keys.pop(token, None)


# Vault keys auto-expire after 30 minutes of inactivity.
vault_store = VaultKeyStore(ttl_seconds=30 * 60)


# ---- API tokens (agent access) ----
def generate_api_token() -> str:
    return secrets.token_urlsafe(32)


def hash_api_token(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


def derive_token_key(secret: str, salt: bytes) -> bytes:
    """Key used to wrap the vault key. Derivable from the token secret alone."""
    from argon2.low_level import hash_secret_raw, Type
    return hash_secret_raw(
        secret=secret.encode(), salt=salt, time_cost=2, memory_cost=65536,
        parallelism=2, hash_len=32, type=Type.ID,
    )
