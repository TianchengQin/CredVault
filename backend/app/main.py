import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import migrations
from .config import INSECURE_ADMIN_PASSWORDS, settings
from .database import Base, SessionLocal, engine
from .routes import ROUTERS
from .services import accounts

log = logging.getLogger("credvault")

CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; "
    "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    "Content-Security-Policy": CSP,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Strict-Transport-Security": "max-age=31536000",
}


def _bootstrap_admin() -> None:
    with SessionLocal() as db:
        if accounts.find_by_username(db, settings.admin_username):
            return
        password = settings.admin_password
        generated = (not password or password in INSECURE_ADMIN_PASSWORDS
                     or len(password) < settings.min_login_password)
        if generated:
            password = secrets.token_urlsafe(18)
            log.warning("ADMIN_PASSWORD unset, weak or a known default; generated a one-time password for %r: %s",
                        settings.admin_username, password)
        admin = accounts.create(db, settings.admin_username, password, is_admin=True)
        admin.must_change_password = int(generated)
        db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate()
    Base.metadata.create_all(bind=engine)
    migrations.upgrade(engine)
    _bootstrap_admin()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="CredVault",
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )

    if settings.cors_origins:  # only needed when the UI is served from another origin
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Vault-Token", "X-API-Token"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers.setdefault(name, value)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    for router in ROUTERS:
        app.include_router(router)

    @app.get("/api/health", include_in_schema=False)
    def health():
        return {"status": "ok"}

    @app.api_route("/api/{_:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def api_not_found(_: str):
        return JSONResponse({"detail": "Not found"}, status_code=404)

    _mount_spa(app, settings.static_dir)
    return app


def _mount_spa(app: FastAPI, static_dir: Path) -> None:
    if not (static_dir / "index.html").is_file():
        return
    root = static_dir.resolve()
    index = root / "index.html"
    if (root / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = (root / full_path).resolve()
        # resolve() + containment check blocks ../ and encoded traversal
        if full_path and candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
