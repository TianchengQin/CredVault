from . import auth, backup, credentials, shares, tokens, users, vault

ROUTERS = (auth.router, vault.router, credentials.router, shares.router, backup.router, tokens.router, users.router)
