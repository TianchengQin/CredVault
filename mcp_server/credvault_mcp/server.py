"""CredVault MCP server: lets AI agents use a CredVault vault through a scoped API token."""

from __future__ import annotations

import argparse
import logging
import sys
from functools import lru_cache
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from . import __version__
from .config import Config, ConfigError, config_file

# stdout carries the MCP protocol — every diagnostic goes to stderr.
log = logging.getLogger("credvault-mcp")

mcp = FastMCP(
    "credvault",
    instructions=(
        "Access the user's CredVault password vault. Use list_credentials / search to find an item "
        "(secrets are not included), then get_credential to fetch its secret only when it is needed. "
        "Never echo secrets back to the user unless they explicitly ask for them."
    ),
)


class VaultError(RuntimeError):
    """Raised for API failures; FastMCP turns the message into a tool error."""


class VaultClient:
    def __init__(self, cfg: Config):
        self._http = httpx.Client(
            base_url=cfg.url,
            verify=cfg.verify,
            timeout=cfg.timeout,
            headers={"X-API-Token": cfg.api_token, "User-Agent": f"credvault-mcp/{__version__}"},
            follow_redirects=False,  # never forward the token to another host
        )

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            r = self._http.request(method, path, **kwargs)
        except httpx.ConnectError as exc:
            hint = " (self-signed certificate? set CREDVAULT_CA_CERT to the server's server.crt)" if "CERTIFICATE" in str(exc).upper() else ""
            raise VaultError(f"Cannot connect to CredVault at {self._http.base_url}{hint}: {exc}") from None
        except httpx.HTTPError as exc:
            raise VaultError(f"Request to CredVault failed: {exc}") from None
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise VaultError(f"CredVault returned {r.status_code}: {detail}")
        return r.json()


@lru_cache(maxsize=1)
def client() -> VaultClient:
    return VaultClient(Config.load())


def _summary(item: dict) -> dict:
    """Credential metadata without the secret."""
    return {k: item.get(k) for k in ("id", "name", "username", "url", "category", "favorite", "description") if k in item} | (
        {"owner": item["owner"], "permission": item["permission"]} if "owner" in item else {}
    )


def _matches(item: dict, query: str | None, category: str | None) -> bool:
    if category and (item.get("category") or "").lower() != category.lower():
        return False
    if not query:
        return True
    q = query.lower()
    return any(q in str(item.get(k) or "").lower() for k in ("name", "username", "url", "category", "description"))


# ---------------------------------------------------------------- tools

@mcp.tool()
def list_credentials(query: str | None = None, category: str | None = None) -> list[dict]:
    """List credentials in the vault (metadata only — secrets are NOT included).

    Args:
        query: optional case-insensitive text matched against name, username, URL, category and notes.
        category: optional exact category filter.
    """
    return [_summary(c) for c in client().request("GET", "/api/vault/credentials") if _matches(c, query, category)]


@mcp.tool()
def get_credential(credential_id: int) -> dict:
    """Fetch one credential including its secret. Each call is recorded in the CredVault audit log."""
    return client().request("GET", f"/api/vault/credentials/{credential_id}")


@mcp.tool()
def create_credential(name: str, secret: str, username: str = "", url: str = "",
                      description: str = "", category: str = "", favorite: bool = False) -> dict:
    """Create a credential. Requires a write token. Returns the created item without its secret."""
    body = {"name": name, "secret": secret, "username": username, "url": url,
            "description": description, "category": category, "favorite": favorite}
    return _summary(client().request("POST", "/api/vault/credentials", json=body))


@mcp.tool()
def update_credential(credential_id: int, name: str | None = None, secret: str | None = None,
                      username: str | None = None, url: str | None = None, description: str | None = None,
                      category: str | None = None, favorite: bool | None = None) -> dict:
    """Change only the given fields of a credential. Requires a write token."""
    patch = {k: v for k, v in {"name": name, "secret": secret, "username": username, "url": url,
                                 "description": description, "category": category, "favorite": favorite}.items() if v is not None}
    if not patch:
        raise VaultError("Nothing to update - pass at least one field")
    return _summary(client().request("PATCH", f"/api/vault/credentials/{credential_id}", json=patch))


@mcp.tool()
def delete_credential(credential_id: int) -> dict:
    """Permanently delete a credential. Requires a write token. Confirm with the user first."""
    return client().request("DELETE", f"/api/vault/credentials/{credential_id}")


@mcp.tool()
def list_shared_credentials(query: str | None = None) -> list[dict]:
    """List credentials other users shared with the token's owner (metadata only)."""
    return [_summary(s) for s in client().request("GET", "/api/vault/shared") if _matches(s, query, None)]


@mcp.tool()
def get_shared_credential(share_id: int) -> dict:
    """Fetch a shared credential including its secret (use the `id` from list_shared_credentials)."""
    return client().request("GET", f"/api/vault/shared/{share_id}")


# ---------------------------------------------------------------- entry point

def _check() -> int:
    cfg = Config.load()
    for w in cfg.warnings():
        print(f"warning: {w}", file=sys.stderr)
    items = VaultClient(cfg).request("GET", "/api/vault/credentials")
    print(f"OK - connected to {cfg.url}, {len(items)} credential(s) visible.", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="credvault-mcp", description=__doc__)
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio",
                        help="MCP transport (default: stdio, which is what desktop clients use)")
    parser.add_argument("--check", action="store_true", help="verify configuration and connectivity, then exit")
    parser.add_argument("--print-config-path", action="store_true", help="show where the config file is looked up")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, format="%(levelname)s %(name)s: %(message)s")

    if args.print_config_path:
        print(config_file())
        return 0
    try:
        if args.check:
            return _check()
        cfg = Config.load()  # fail fast with a readable message
    except (ConfigError, VaultError) as exc:
        print(f"credvault-mcp: {exc}", file=sys.stderr)
        return 2
    for w in cfg.warnings():
        log.warning(w)

    try:
        mcp.run(transport=args.transport)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
