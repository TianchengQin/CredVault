# CredVault MCP server

Gives AI agents (Claude Desktop, Claude Code, Cursor, any MCP client) scoped access to a
CredVault vault through an API token. Runs on **Windows, macOS and Linux** with Python 3.10+.

## 1. Create a token

In CredVault: **Settings → API tokens**. Use *Read only* unless the agent must change items.

## 2. Install

Pick one — all work on every OS:

```bash
uvx --from ./mcp_server credvault-mcp --check      # no install, uses uv
pipx install ./mcp_server                           # isolated global command
pip install ./mcp_server                            # into the current venv
```

Or use the bundled launchers, which create `mcp_server/.venv` on first run:
`run.sh` (Linux/macOS), `run.ps1` (PowerShell) or `run.cmd` (cmd.exe).

## 3. Configure

| Setting | Env var | JSON key | Default |
|---|---|---|---|
| Server URL | `CREDVAULT_URL` | `url` | `https://localhost:8904` |
| Token | `CREDVAULT_API_TOKEN` | `api_token` | — |
| Token from file | `CREDVAULT_API_TOKEN_FILE` | `api_token_file` | — |
| Trust a self-signed cert | `CREDVAULT_CA_CERT` | `ca_cert` | — |
| Disable TLS checks (avoid) | `CREDVAULT_VERIFY_TLS=0` | `verify_tls` | on |

Lookup order: environment → `.env` (cwd or `mcp_server/`) → per-user JSON file:

- Windows `%APPDATA%\CredVault\mcp.json`
- macOS `~/Library/Application Support/CredVault/mcp.json`
- Linux `~/.config/credvault/mcp.json` (honours `XDG_CONFIG_HOME`)

`credvault-mcp --print-config-path` prints it; `credvault-mcp --check` tests the connection.

Example `mcp.json`:

```json
{ "url": "https://vault.lan:8904", "api_token_file": "~/.credvault-token", "ca_cert": "~/credvault-server.crt" }
```

> **TLS is verified by default.** CredVault ships a self-signed certificate; copy
> `certs/server.crt` from the server and point `CREDVAULT_CA_CERT` at it instead of disabling checks.

## 4. Add to your MCP client

Claude Desktop config file — Windows `%APPDATA%\Claude\claude_desktop_config.json`,
macOS `~/Library/Application Support/Claude/claude_desktop_config.json`.

```json
{
  "mcpServers": {
    "credvault": {
      "command": "credvault-mcp",
      "env": { "CREDVAULT_URL": "https://vault.lan:8904", "CREDVAULT_API_TOKEN_FILE": "C:\\Users\\me\\.credvault-token" }
    }
  }
}
```

Without installing, use a launcher as the command: `"command": "C:\\path\\to\\mcp_server\\run.cmd"`
(Windows) or `"command": "/path/to/mcp_server/run.sh"` (Linux/macOS).

Claude Code: `claude mcp add credvault -- credvault-mcp`

## Tools

| Tool | Token | Notes |
|---|---|---|
| `list_credentials(query?, category?)` | read | metadata only — no secrets |
| `get_credential(credential_id)` | read | includes the secret; audit-logged |
| `create_credential(...)` | write | |
| `update_credential(credential_id, ...)` | write | only fields you pass change |
| `delete_credential(credential_id)` | write | |
| `list_shared_credentials(query?)` | read | items shared with you |
| `get_shared_credential(share_id)` | read | includes the secret |
