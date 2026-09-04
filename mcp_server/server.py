"""CredVault MCP server.

Lets AI agents read/write credentials in CredVault using an API token.

Run (stdio):
    export CREDVAULT_URL=https://host:8904
    export CREDVAULT_API_TOKEN=<write-or-read-token>
    python server.py
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.environ.get("CREDVAULT_URL", "https://localhost:8904").rstrip("/")
API_TOKEN = os.environ.get("CREDVAULT_API_TOKEN", "")
VERIFY_TLS = os.environ.get("CREDVAULT_VERIFY_TLS", "0") == "1"

if not API_TOKEN:
    raise SystemExit("CREDVAULT_API_TOKEN is required (generate one in CredVault)")

mcp = FastMCP("credvault")


class Client:
    def __init__(self):
        self._c = httpx.Client(base_url=BASE_URL, verify=VERIFY_TLS, timeout=30)

    def _h(self):
        return {"X-API-Token": API_TOKEN}

    def list(self):
        r = self._c.get("/api/vault/credentials", headers=self._h())
        r.raise_for_status()
        return r.json()

    def get(self, cid):
        r = self._c.get(f"/api/vault/credentials/{cid}", headers=self._h())
        r.raise_for_status()
        return r.json()

    def create(self, payload):
        r = self._c.post("/api/vault/credentials", json=payload, headers=self._h())
        r.raise_for_status()
        return r.json()

    def update(self, cid, payload):
        r = self._c.put(f"/api/vault/credentials/{cid}", json=payload, headers=self._h())
        r.raise_for_status()
        return r.json()

    def delete(self, cid):
        r = self._c.delete(f"/api/vault/credentials/{cid}", headers=self._h())
        r.raise_for_status()
        return r.json()


client = Client()


@mcp.tool()
def list_credentials() -> list[dict]:
    """List all credentials (id, name, url, username, description, secret)."""
    return client.list()


@mcp.tool()
def get_credential(credential_id: int) -> dict:
    """Get a single credential by id, including the secret."""
    return client.get(credential_id)


@mcp.tool()
def create_credential(
    name: str,
    secret: str,
    url: str = "",
    username: str = "",
    description: str = "",
) -> dict:
    """Create a new credential. Requires a write token."""
    return client.create({
        "name": name, "secret": secret,
        "url": url, "username": username, "description": description,
    })


@mcp.tool()
def update_credential(
    credential_id: int,
    name: str | None = None,
    secret: str | None = None,
    url: str | None = None,
    username: str | None = None,
    description: str | None = None,
) -> dict:
    """Update an existing credential. Requires a write token."""
    existing = client.get(credential_id)
    payload = {
        "name": name if name is not None else existing["name"],
        "secret": secret if secret is not None else existing["secret"],
        "url": url if url is not None else existing["url"],
        "username": username if username is not None else existing["username"],
        "description": description if description is not None else existing["description"],
    }
    return client.update(credential_id, payload)


@mcp.tool()
def delete_credential(credential_id: int) -> dict:
    """Delete a credential by id. Requires a write token."""
    return client.delete(credential_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
