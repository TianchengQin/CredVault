<div align="center">

# 🔐 CredVault

### *The cozy, encrypted credential manager for your LAN*

[![Built with FastAPI](https://img.shields.io/badge/backend-FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61dafb?style=flat-square&logo=react&logoColor=white)](https://reactjs.org)
[![AES-256-GCM](https://img.shields.io/badge/crypto-AES--256--GCM-2ea44f?style=flat-square)](https://cryptography.io)
[![Argon2](https://img.shields.io/badge/kdf-Argon2id-8e44ad?style=flat-square)](https://en.wikipedia.org/wiki/Argon2)
[![2FA](https://img.shields.io/badge/2FA-TOTP-ff9f0a?style=flat-square)](#-optional-two-factor-authentication)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)

Your passwords deserve better than a sticky note. CredVault is a self-hosted,
**zero-trust** vault where your secrets are encrypted on your machine and stay
ciphertext at rest. It runs in Docker, talks HTTPS on your LAN, and plays nice
with AI agents.

```
   .  .      .
   |\/|_.-._|  /
   | |||  \| |    "the password manager that respects your master password"
   (o)(o)  \|__|
```

</div>

---

## ✨ Features

| Pillar | What you get |
|---|---|
| 🔒 **Zero-trust encryption** | AES-256-GCM at rest; key derived from your master password with **Argon2id**. Not even the admin can read your vault. |
| 🧩 **Multi-user vaults** | Everyone gets their own vault. Admins manage users, never your secrets. |
| 🛡️ **Brute-force protection** | Login & unlock are rate-limited → lock out after repeated failures. |
| 📜 **Audit trail** | Every login, unlock, credential access, token, and admin action is logged. |
| 📱 **Optional 2FA** | TOTP one-time codes at sign-in via your favorite authenticator app. |
| ⏱️ **Auto-lock** | The vault locks itself after inactivity. Security naps included. |
| 🔑 **Password generator** | Strong, crypto-random passwords at the click of a button. |
| 🗂️ **Organize** | Categories, favorites, search & filters so nothing gets lost. |
| 🔗 **Share credentials** | Share a credential with another user with `read` or `write` access. Copies are re-encrypted with the recipient's vault key. |
| ✍️ **Self-registration** | Users can create their own account right from the sign-in page. |
| 🔑 **Password reset** | An admin can reset a user to a temporary password; the user then sets a new one (with MFA) on next sign-in. |
| 💾 **Backup / restore** | Export to JSON, import to restore or merge. Peace of mind. |
| 🤖 **AI-agent friendly** | API tokens (`read`/`write`) + an MCP server so agents can work for you. |
| 🎨 **Focused UI** | Two-pane vault browser, categories in the sidebar, password generator & strength meter, light/dark themes. |

> 🧠 *Why another password manager?* Because we believe your secrets should be
> encrypted with a key only *you* hold — not one a cloud vendor keeps for you.
> Run it at home, in a VM, or on a Raspberry Pi that fits in a toaster. 🍞

---

## 🚀 Quickstart

```bash
git clone git@github.com:TianchengQin/CredVault.git
cd CredVault
cp .env.example .env   # set ADMIN_PASSWORD, SECRET_KEY

docker compose up -d --build
```

Then open **https://<host-ip>:8904** (browsers warn about the self-signed cert — accept it).

- **First run:** set your vault master password. It **cannot be recovered** if forgotten. 🫡
- **Not set in `.env`?** The entrypoint auto-generates a strong `ADMIN_PASSWORD` and
  `SECRET_KEY` and persists them under `./data/` (never in the logs). Read the admin password with
  `docker compose exec credvault cat /data/.admin_password`.

> 🔐 **Never run it with a weak default.** If you see the warning about the insecure
> admin password or secret key, set real values in your environment. This repo ships
> **no credentials** — you bring your own.

### Configuration (`docker-compose.yml`)

| Env var | Purpose |
|---|---|
| `ADMIN_USERNAME` | First admin login name (default `admin`) |
| `ADMIN_PASSWORD` | First admin login password — **strongly recommended to set** |
| `SECRET_KEY` | Random value (≥ 32 chars) used to sign sessions — generated if unset |
| `ALLOW_REGISTRATION` | Let anyone reach the sign-up form (default `true`) |
| `VAULT_IDLE_MINUTES` | Auto-lock an unlocked vault after this idle time (default `15`) |
| `SESSION_MINUTES` | Sign-in session lifetime (default `720`) |
| `ENABLE_API_DOCS` | Serve OpenAPI docs at `/docs` (default off) |
| `CORS_ORIGINS` | Comma-separated origins allowed cross-origin (default none) |
| `DATABASE_URL` | SQLAlchemy URL (default: SQLite in `./data`) |

Volumes: `./data` (SQLite DB) and `./certs` (TLS). Both are git-ignored — they live on your box only.

---

## 🧩 The app at a glance

- **Sidebar** with All items, Favorites, Shared with me, your categories, and Settings (API tokens, Security, Backup, Admin).
- **Two-pane browser:** search with `/`, copy username/password in one click (clipboard auto-clears after 30s).
- **Modals stay put** — closing a panel is a deliberate click on ✕ / Cancel, never an accidental outside-click. 🙅
- **Dark mode** 🌙 — toggle in the sidebar, follows your OS preference by default.

### API tokens (agent access)

Generate a token in the **API tokens** page (you must be unlocked), then:

```bash
curl -k https://<host>:8904/api/vault/credentials \
  -H 'X-API-Token: <your-token>'
```

Tokens are scoped to one user's vault, with `read` or `write` permission. The secret is shown **only once**.

### MCP server (AI agents)

Works on Windows, macOS and Linux:

```bash
pipx install ./mcp_server            # or: uvx --from ./mcp_server credvault-mcp
CREDVAULT_URL=https://<host>:8904 CREDVAULT_API_TOKEN=<token> CREDVAULT_CA_CERT=./certs/server.crt credvault-mcp --check
```

Or run `mcp_server/run.sh`, `run.ps1` or `run.cmd`, which bootstrap a venv on first use.
Config can also live in a per-user `mcp.json`. See [mcp_server/README.md](mcp_server/README.md)
for client setup (Claude Desktop / Claude Code) and the tool list.

---

## 🔒 Security model

- **Per-user vaults.** Each vault key is derived (Argon2id) from that user's master password. Credentials are AES-256-GCM encrypted; admins manage accounts but can't decrypt your vault.
- **Shared credentials stay encrypted for the recipient.** Sharing re-encrypts a copy with the recipient's vault key, so only they can decrypt it. The recipient must have unlocked their vault recently for the share to be created; edits to a shared copy are independent (a snapshot).
- **No secrets at rest in the repo.** The database, TLS keys, and generated secrets live under `data/` and `certs/` — both git-ignored.
- **Sharing uses public-key crypto.** Each vault has an X25519 keypair (private key wrapped by the vault key); shares are sealed to the recipient's public key, so recipients don't need to be online.
- **Brute-force armor:** per-account and per-IP lockouts on login, vault unlock, 2FA and password change.
- **Optional TOTP 2FA** enforced at sign-in; codes are single-use.
- **Sessions are revocable:** changing or resetting a password signs out every session and re-locks every unlocked vault.
- **Auto-lock** after inactivity (sliding server-side TTL + client timer). Vault handles are bound to the user they were issued to and live only in memory.
- **Hardened HTTP:** strict CSP, no CORS by default, no-store on API responses, frame denial, path-traversal-safe static serving. The container runs as an unprivileged user.
- **Login password ≠ vault master password.** An admin can reset a user's *login* password to a temporary one (the user is forced to set a new one, with MFA, on next sign-in) without touching the vault. The vault is separate.
- **Lost your master password?** Your vault is unrecoverable by design. An admin can **reset** a vault so the user starts fresh (this wipes that vault's credentials).

> 📖 Set `ENABLE_API_DOCS=true` to browse the OpenAPI docs at `/docs`.

---

## 🧱 Stack

| Layer | Tech |
|---|---|
| Backend | Python · FastAPI · SQLAlchemy · PyJWT · bcrypt · `cryptography` (AES-GCM) · `argon2-cffi` |
| Frontend | React · Vite · Tailwind CSS (Apple-flavored tokens) |
| Ops | Docker multi-stage · docker-compose · self-signed TLS via uvicorn |
| Agents | MCP server wrapping the REST API |

---

## 🧑‍💻 Local development

```bash
# backend (plain HTTP for local dev)
cd backend && pip install -r requirements-dev.txt
CREDVAULT_ALLOW_INSECURE=1 DATABASE_URL=sqlite:///./dev.db STATIC_DIR=../frontend/dist uvicorn app.main:app --reload --port 8443

# tests
cd backend && pytest

# frontend (proxies /api to :8443)
cd frontend && npm install && npm run dev

# build frontend into the app
cd frontend && npm run build
```

---

<div align="center">

Made with ☕, ❤️, and a healthy respect for your secrets.

**Keep your vault locked. 🗝️**

</div>
