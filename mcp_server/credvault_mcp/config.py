"""Cross-platform configuration for the CredVault MCP server.

Values are resolved in this order (first wins):

1. Environment variables (``CREDVAULT_URL``, ``CREDVAULT_API_TOKEN`` …)
2. A ``.env`` file in the current directory or next to this package
3. A JSON config file in the per-user config directory:
     Windows  %APPDATA%\\CredVault\\mcp.json
     macOS    ~/Library/Application Support/CredVault/mcp.json
     Linux    $XDG_CONFIG_HOME/credvault/mcp.json  (default ~/.config/credvault/mcp.json)
   or the path in ``CREDVAULT_MCP_CONFIG``.

The API token may also be read from a file (``CREDVAULT_API_TOKEN_FILE`` /
``"api_token_file"``) so it never has to appear in an MCP client's config.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ENV_PREFIX = "CREDVAULT_"
DEFAULT_URL = "https://localhost:8904"


class ConfigError(RuntimeError):
    pass


def user_config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
        return Path(base) / "CredVault"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "CredVault"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "credvault"


def config_file() -> Path:
    override = os.environ.get(f"{ENV_PREFIX}MCP_CONFIG")
    return Path(override).expanduser() if override else user_config_dir() / "mcp.json"


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.removeprefix("export ").partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _load_sources() -> dict[str, str]:
    """Merge config sources into ``{"URL": ..., "API_TOKEN": ...}`` (unprefixed, upper-case)."""
    merged: dict[str, str] = {}

    path = config_file()
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise ConfigError(f"{path} is not valid JSON: {exc}") from exc
        merged.update({str(k).upper(): str(v) for k, v in data.items() if v is not None})

    for candidate in (Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"):
        if candidate.is_file():
            merged.update({k.removeprefix(ENV_PREFIX): v for k, v in _parse_dotenv(candidate).items() if k.startswith(ENV_PREFIX)})
            break

    merged.update({k.removeprefix(ENV_PREFIX): v for k, v in os.environ.items() if k.startswith(ENV_PREFIX)})
    return merged


def _truthy(value: str | None, default: bool) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Config:
    url: str
    api_token: str
    verify: bool | str  # True, False, or a path to a CA bundle / self-signed cert
    timeout: float

    @classmethod
    def load(cls) -> "Config":
        src = _load_sources()

        token = src.get("API_TOKEN", "").strip()
        token_file = src.get("API_TOKEN_FILE", "").strip()
        if not token and token_file:
            path = Path(token_file).expanduser()
            try:
                token = path.read_text(encoding="utf-8-sig").strip()
            except OSError as exc:
                raise ConfigError(f"Cannot read API token file {path}: {exc}") from exc
        if not token:
            raise ConfigError(
                "No API token configured. Create one in CredVault (Settings → API tokens) and set "
                f"CREDVAULT_API_TOKEN, CREDVAULT_API_TOKEN_FILE, or \"api_token\" in {config_file()}."
            )

        url = (src.get("URL") or DEFAULT_URL).strip().rstrip("/")
        if not url.startswith(("https://", "http://")):
            raise ConfigError(f"CREDVAULT_URL must start with https:// (got {url!r})")

        ca_cert = src.get("CA_CERT", "").strip()
        if ca_cert:
            ca_path = Path(ca_cert).expanduser()
            if not ca_path.is_file():
                raise ConfigError(f"CREDVAULT_CA_CERT points to a missing file: {ca_path}")
            verify: bool | str = str(ca_path)
        else:
            verify = _truthy(src.get("VERIFY_TLS"), default=True)

        try:
            timeout = float(src.get("TIMEOUT") or 30)
        except ValueError:
            timeout = 30.0

        return cls(url=url, api_token=token, verify=verify, timeout=timeout)

    def warnings(self) -> list[str]:
        notes = []
        if self.url.startswith("http://") and not any(h in self.url for h in ("://localhost", "://127.0.0.1", "://[::1]")):
            notes.append("CREDVAULT_URL uses plain http:// — secrets and your token travel unencrypted.")
        if self.verify is False:
            notes.append("TLS verification is disabled (CREDVAULT_VERIFY_TLS=0). Prefer CREDVAULT_CA_CERT=<path to server.crt>.")
        return notes
