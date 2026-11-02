"""Runtime configuration, read once from the environment."""

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

INSECURE_SECRET_KEYS = frozenset({"", "dev-secret-change-me", "change-me-to-a-long-random-string"})
INSECURE_ADMIN_PASSWORDS = frozenset({"123sqwert", "change-me-to-a-strong-password"})


def _flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _list(name: str) -> list[str]:
    return [v.strip() for v in os.environ.get(name, "").split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    secret_key: str = field(default_factory=lambda: os.environ.get("SECRET_KEY", ""))
    allow_insecure: bool = field(default_factory=lambda: _flag("CREDVAULT_ALLOW_INSECURE"))

    database_url: str = field(default_factory=lambda: os.environ.get("DATABASE_URL", "sqlite:////data/credvault.db"))
    static_dir: Path = field(default_factory=lambda: Path(os.environ.get("STATIC_DIR", "/app/static")))

    admin_username: str = field(default_factory=lambda: os.environ.get("ADMIN_USERNAME", "admin"))
    admin_password: str = field(default_factory=lambda: os.environ.get("ADMIN_PASSWORD", ""))

    allow_registration: bool = field(default_factory=lambda: _flag("ALLOW_REGISTRATION", True))
    enable_docs: bool = field(default_factory=lambda: _flag("ENABLE_API_DOCS", False))
    cors_origins: list[str] = field(default_factory=lambda: _list("CORS_ORIGINS"))

    session_minutes: int = field(default_factory=lambda: _int("SESSION_MINUTES", 12 * 60))
    mfa_token_minutes: int = 5
    vault_idle_minutes: int = field(default_factory=lambda: _int("VAULT_IDLE_MINUTES", 15))

    min_login_password: int = 10
    min_master_password: int = 12

    def validate(self) -> None:
        if self.allow_insecure:
            return
        if self.secret_key in INSECURE_SECRET_KEYS or len(self.secret_key) < 32:
            raise RuntimeError(
                "SECRET_KEY is unset, too short (<32 chars) or a known default. "
                "Generate one with `openssl rand -hex 32` (or set CREDVAULT_ALLOW_INSECURE=1 for local dev)."
            )

    @property
    def jwt_key(self) -> str:
        # In insecure/dev mode without a key, fall back to a per-process random key
        # so a guessable default never signs sessions.
        return self.secret_key if self.secret_key not in INSECURE_SECRET_KEYS else _EPHEMERAL_KEY


_EPHEMERAL_KEY = secrets.token_hex(32)

settings = Settings()
