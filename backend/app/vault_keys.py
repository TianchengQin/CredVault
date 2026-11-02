"""Unlocked vault keys, held in process memory only.

A vault token is a random handle bound to one user. Keys expire after
``idle_seconds`` without use (sliding), and are dropped on lock, sign-out,
password reset, vault reset or user deletion.
"""

import secrets
import threading
import time
from dataclasses import dataclass

from .config import settings
from .errors import VaultLocked


@dataclass
class _Entry:
    user_id: int
    key: bytes
    expires: float


class VaultKeyStore:
    def __init__(self, idle_seconds: int):
        self.idle_seconds = idle_seconds
        self._entries: dict[str, _Entry] = {}
        self._lock = threading.Lock()

    def put(self, user_id: int, key: bytes) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._purge()
            self._entries[token] = _Entry(user_id, key, time.monotonic() + self.idle_seconds)
        return token

    def get(self, token: str | None, user_id: int) -> bytes:
        if not token:
            raise VaultLocked("Vault is locked")
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(token)
            # A token is only valid for the user it was issued to.
            if entry is None or entry.user_id != user_id:
                raise VaultLocked("Vault is locked")
            if now > entry.expires:
                del self._entries[token]
                raise VaultLocked("Vault locked after inactivity")
            entry.expires = now + self.idle_seconds
            return entry.key

    def revoke(self, token: str | None) -> None:
        if token:
            with self._lock:
                self._entries.pop(token, None)

    def revoke_user(self, user_id: int) -> None:
        with self._lock:
            self._entries = {t: e for t, e in self._entries.items() if e.user_id != user_id}

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def _purge(self) -> None:
        now = time.monotonic()
        self._entries = {t: e for t, e in self._entries.items() if e.expires >= now}


vault_keys = VaultKeyStore(idle_seconds=settings.vault_idle_minutes * 60)
