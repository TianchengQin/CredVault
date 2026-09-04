import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import Base, engine, SessionLocal
from .models import User
from . import auth
from .routes import auth as auth_routes
from .routes import vault as vault_routes
from .routes import users as users_routes
from .routes import tokens as tokens_routes

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "123sqwert")

STATIC_DIR = Path(os.environ.get("STATIC_DIR", "/app/static"))

# Refuse to run with a weak/default SECRET_KEY in production.
_DEFAULT_KEYS = {"dev-secret-change-me", "change-me-to-a-long-random-string"}
if os.environ.get("CREDVAULT_ALLOW_INSECURE", "").lower() not in {"1", "true", "yes"}:
    if auth.SECRET_KEY in _DEFAULT_KEYS:
        raise RuntimeError(
            "SECRET_KEY is unset or set to the insecure default. "
            "Set a long random SECRET_KEY (or CREDVAULT_ALLOW_INSECURE=1 for dev)."
        )


def _migrate():
    """Idempotently add columns for upgrades on existing SQLite DBs."""
    from sqlalchemy import text
    statements = {
        "users": [
            ("totp_secret", "ALTER TABLE users ADD COLUMN totp_secret VARCHAR"),
            ("totp_enabled", "ALTER TABLE users ADD COLUMN totp_enabled INTEGER DEFAULT 0"),
        ],
        "credentials": [
            ("category", "ALTER TABLE credentials ADD COLUMN category VARCHAR DEFAULT ''"),
            ("favorite", "ALTER TABLE credentials ADD COLUMN favorite INTEGER DEFAULT 0"),
        ],
    }
    with engine.begin() as conn:
        for table, cols in statements.items():
            existing = {row[1] for row in conn.execute(text(f"PRAGMA table_info({table})")).fetchall()}
            for col, stmt in cols:
                if col not in existing:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _migrate()
    db = SessionLocal()
    if not db.query(User).filter(User.username == ADMIN_USERNAME).first():
        db.add(User(
            username=ADMIN_USERNAME,
            login_hash=auth.hash_login_password(ADMIN_PASSWORD),
            is_admin=1,
        ))
        db.commit()
    db.close()
    yield


app = FastAPI(title="CredVault", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(vault_routes.router)
app.include_router(users_routes.router)
app.include_router(tokens_routes.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/{full_path:path}")
    def spa_fallback(full_path: str):
        f = STATIC_DIR / full_path
        if f.is_file():
            return FileResponse(f)
        return FileResponse(STATIC_DIR / "index.html")
