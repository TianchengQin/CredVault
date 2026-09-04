import threading
import time


class RateLimiter:
    """Simple in-memory sliding-window attempt limiter.

    After `max_attempts` failures within `window` seconds, the key is
    locked for `lockout` seconds. Single-process only (fine for this LAN app).
    """

    def __init__(self, max_attempts=5, window=300, lockout=900):
        self.max_attempts = max_attempts
        self.window = window
        self.lockout = lockout
        self._fails = {}
        self._lock = threading.Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """Return (allowed, retry_after_seconds)."""
        now = time.time()
        with self._lock:
            entry = self._fails.get(key)
            if not entry:
                return True, 0
            if now < entry["locked_until"]:
                return False, int(entry["locked_until"] - now)
            # slide window
            entry["times"] = [t for t in entry["times"] if now - t < self.window]
            if len(entry["times"]) >= self.max_attempts:
                entry["locked_until"] = now + self.lockout
                entry["times"] = []
                return False, self.lockout
            return True, 0

    def fail(self, key: str) -> None:
        now = time.time()
        with self._lock:
            entry = self._fails.setdefault(key, {"times": [], "locked_until": 0})
            entry["times"].append(now)
            entry["times"] = [t for t in entry["times"] if now - t < self.window]

    def reset(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)


# Shared instances for login and vault-unlock attempts.
login_limiter = RateLimiter(max_attempts=5, window=300, lockout=900)
unlock_limiter = RateLimiter(max_attempts=5, window=300, lockout=900)
