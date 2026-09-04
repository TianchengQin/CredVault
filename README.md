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
| 💾 **Backup / restore** | Export to JSON, import to restore or merge. Peace of mind. |
| 🤖 **AI-agent friendly** | API tokens (`read`/`write`) + an MCP server so agents can work for you. |
| 🎨 **Apple-tasteful UI** | Parchment-clean surfaces, Action Blue accent, dark mode. Easy on the eyes. |

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
  `SECRET_KEY`, persists them under `./data/`, and prints them once to the container logs.

> 🔐 **Never run it with a weak default.** If you see the warning about the insecure
> admin password or secret key, set real values in your environment. This repo ships
> **no credentials** — you bring your own.

### Configuration (`docker-compose.yml`)

| Env var | Purpose |
|---|---|
| `ADMIN_USERNAME` | First admin login name (default `admin`) |
| `ADMIN_PASSWORD` | First admin login password — **strongly recommended to set** |
| `SECRET_KEY` | Long random value used to sign sessions — **set this** |
| `DATABASE_URL` | SQLAlchemy URL (default: SQLite in `./data`) |

Volumes: `./data` (SQLite DB) and `./certs` (TLS). Both are git-ignored — they live on your box only.

---

## 🧩 The app at a glance

- **Sidebar** to hop between Credentials, API tokens, Security (2FA), Backup, and Admin.
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

```bash
cd mcp_server && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
export CREDVAULT_URL=https://<host>:8904
export CREDVAULT_API_TOKEN=<write-or-read-token>
python server.py   # speaks MCP over stdio
```

Tools: `list_credentials`, `get_credential`, `create_credential`, `update_credential`, `delete_credential`.

---

## 🔒 Security model

- **Per-user vaults.** Each vault key is derived (Argon2id) from that user's master password. Credentials are AES-256-GCM encrypted; admins manage accounts but can't decrypt your vault.
- **No secrets at rest in the repo.** The database, TLS keys, and generated secrets live under `data/` and `certs/` — both git-ignored.
- **Brute-force armor:** 5 failed login/unlock attempts → 15-minute lockout.
- **Optional TOTP 2FA** enforced at sign-in when enabled.
- **Auto-lock** after inactivity (client + server-side TTL).
- **Lost your master password?** Your vault is unrecoverable by design. An admin can **reset** a vault so the user starts fresh (this wipes that vault's credentials).

> 📖 Full API & token management details live in the app and its OpenAPI docs at `/docs`.

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
# backend
cd backend && uvicorn app.main:app --reload --port 8443

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
