"""Login passwords, session JWTs and brute-force throttling."""

import threading
import time
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings
from .errors import SessionExpired, Unauthorized

ALGORITHM = "HS256"
ISSUER = "credvault"

# ---------------------------------------------------------------- login passwords (bcrypt)

_BCRYPT_MAX = 72  # bcrypt only uses the first 72 bytes; truncate explicitly (bcrypt>=5 raises)


def _pw(password: str) -> bytes:
    return password.encode()[:_BCRYPT_MAX]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_pw(password), bcrypt.gensalt(rounds=12)).decode()


# Verified against when the user doesn't exist so response time doesn't leak usernames.
_DUMMY_HASH = hash_password("credvault-timing-equaliser")


def verify_password(password: str, hashed: str | None) -> bool:
    try:
        return bcrypt.checkpw(_pw(password), (hashed or _DUMMY_HASH).encode()) and hashed is not None
    except ValueError:
        return False


# ---------------------------------------------------------------- JWTs

def _encode(claims: dict, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {**claims, "iss": ISSUER, "iat": now, "exp": now + timedelta(minutes=minutes)},
        settings.jwt_key, algorithm=ALGORITHM,
    )


def _decode(token: str, typ: str) -> dict:
    try:
        claims = jwt.decode(
            token, settings.jwt_key, algorithms=[ALGORITHM], issuer=ISSUER,
            options={"require": ["exp", "iat", "sub", "typ"]},
        )
    except jwt.PyJWTError:
        raise Unauthorized("Session expired, please sign in again")
    # Never accept one token type in place of another (e.g. an MFA ticket as a session).
    if claims.get("typ") != typ:
        raise Unauthorized("Invalid session")
    return claims


def create_session_token(user_id: int, token_version: int) -> str:
    return _encode({"sub": str(user_id), "typ": "access", "ver": token_version}, settings.session_minutes)


def decode_session_token(token: str) -> tuple[int, int]:
    try:
        claims = _decode(token, "access")
    except Unauthorized as exc:
        raise SessionExpired(exc.detail)
    return int(claims["sub"]), int(claims.get("ver", 0))


def create_mfa_ticket(user_id: int, token_version: int) -> str:
    return _encode({"sub": str(user_id), "typ": "mfa", "ver": token_version}, settings.mfa_token_minutes)


def decode_mfa_ticket(token: str) -> tuple[int, int]:
    try:
        claims = _decode(token, "mfa")
    except Unauthorized:
        raise Unauthorized("Verification expired, please sign in again")
    return int(claims["sub"]), int(claims.get("ver", 0))


# ---------------------------------------------------------------- rate limiting

class RateLimiter:
    """In-memory sliding-window limiter with lockout. Single-process only."""

    def __init__(self, max_attempts: int = 5, window: int = 300, lockout: int = 900):
        self.max_attempts = max_attempts
        self.window = window
        self.lockout = lockout
        self._fails: dict[str, tuple[list[float], float]] = {}
        self._lock = threading.Lock()

    def retry_after(self, key: str) -> int:
        """Seconds until ``key`` may try again (0 = allowed)."""
        now = time.monotonic()
        with self._lock:
            times, locked_until = self._fails.get(key, ([], 0.0))
            return max(0, int(locked_until - now) + 1) if now < locked_until else 0

    def fail(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            times, locked_until = self._fails.get(key, ([], 0.0))
            times = [t for t in times if now - t < self.window] + [now]
            if len(times) >= self.max_attempts:
                times, locked_until = [], now + self.lockout
            self._fails[key] = (times, locked_until)
            if len(self._fails) > 10_000:
                self._prune(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._fails.clear()

    def _prune(self, now: float) -> None:
        self._fails = {
            k: (ts, lu) for k, (ts, lu) in self._fails.items()
            if lu > now or any(now - t < self.window for t in ts)
        }


# per IP+account, plus a looser per-IP limit against password spraying
login_limiter = RateLimiter(max_attempts=5, window=300, lockout=900)
ip_limiter = RateLimiter(max_attempts=30, window=300, lockout=900)
unlock_limiter = RateLimiter(max_attempts=5, window=300, lockout=900)
mfa_limiter = RateLimiter(max_attempts=5, window=300, lockout=900)

ALL_LIMITERS = (login_limiter, ip_limiter, unlock_limiter, mfa_limiter)
