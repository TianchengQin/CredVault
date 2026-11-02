from fastapi import APIRouter, Request

from .. import audit, crypto, schemas, security
from ..config import settings
from ..deps import DB, CurrentUser
from ..errors import BadRequest, Forbidden, TooManyAttempts, Unauthorized
from ..models import User
from ..security import ip_limiter, login_limiter, mfa_limiter
from ..services import accounts

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _throttle(*checks: tuple[security.RateLimiter, str]) -> None:
    for limiter, key in checks:
        if wait := limiter.retry_after(key):
            raise TooManyAttempts(wait)


def _verify_totp(db, user: User, code: str) -> bool:
    """Check a TOTP code and burn its time step so it can't be reused."""
    counter = crypto.totp_match(user.totp_secret or "", code, after_counter=user.totp_last_counter or 0)
    if counter is None:
        return False
    user.totp_last_counter = counter
    db.commit()
    return True


@router.post("/login", response_model=schemas.Session)
def login(body: schemas.LoginRequest, request: Request, db: DB):
    ip = audit.client_ip(request)
    account_key = f"{ip}:{body.username.lower()}"
    _throttle((ip_limiter, ip), (login_limiter, account_key))

    user = accounts.find_by_username(db, body.username)
    if not security.verify_password(body.password, user.login_hash if user else None):
        login_limiter.fail(account_key)
        ip_limiter.fail(ip)
        audit.record(db, "login_failed", username=body.username, request=request)
        raise Unauthorized("Invalid username or password")

    login_limiter.reset(account_key)
    if user.totp_enabled:
        audit.record(db, "login_password_ok", user=user, request=request)
        return schemas.Session(
            **accounts.profile(user).model_dump(exclude={"token", "mfa_required", "mfa_token"}),
            mfa_required=True, mfa_token=security.create_mfa_ticket(user.id, user.token_version or 0),
        )
    audit.record(db, "login", user=user, request=request)
    return accounts.session_for(user)


@router.post("/2fa/confirm", response_model=schemas.Session)
def confirm_mfa(body: schemas.MfaConfirmRequest, request: Request, db: DB):
    user_id, version = security.decode_mfa_ticket(body.mfa_token)
    key = f"mfa:{user_id}"
    _throttle((mfa_limiter, key))

    user = db.get(User, user_id)
    if user is None or not user.totp_enabled or (user.token_version or 0) != version:
        raise Unauthorized("Verification expired, please sign in again")
    if not _verify_totp(db, user, body.code):
        mfa_limiter.fail(key)
        audit.record(db, "mfa_failed", user=user, request=request)
        raise Unauthorized("Invalid 2FA code")

    mfa_limiter.reset(key)
    audit.record(db, "login_mfa", user=user, request=request)
    return accounts.session_for(user)


@router.get("/config")
def public_config():
    """Unauthenticated settings the sign-in screen needs."""
    return {
        "allow_registration": settings.allow_registration,
        "min_password": settings.min_login_password,
        "min_master_password": settings.min_master_password,
    }


@router.post("/register", response_model=schemas.Session, status_code=201)
def register(body: schemas.RegisterRequest, request: Request, db: DB):
    if not settings.allow_registration:
        raise Forbidden("Self-registration is disabled. Ask an administrator for an account.")
    ip = audit.client_ip(request)
    _throttle((ip_limiter, ip))
    ip_limiter.fail(ip)  # every registration counts toward the per-IP budget

    user = accounts.create(db, body.username, body.password)
    audit.record(db, "user_register", user=user, request=request, commit=False)
    db.commit()
    return accounts.session_for(user)


@router.get("/me", response_model=schemas.Session)
def me(user: CurrentUser):
    return accounts.profile(user)


@router.post("/change-password", response_model=schemas.Session)
def change_password(body: schemas.ChangePasswordRequest, user: CurrentUser, request: Request, db: DB):
    """Re-verifies the current password (and 2FA when enabled).

    Every existing session is revoked; the response carries a fresh one for this client.
    """
    key = f"pw:{user.id}"
    _throttle((login_limiter, key))
    if not security.verify_password(body.current_password, user.login_hash):
        login_limiter.fail(key)
        raise BadRequest("Current password is incorrect")
    if user.totp_enabled and not _verify_totp(db, user, body.mfa_code):
        login_limiter.fail(key)
        raise BadRequest("Invalid 2FA code")
    if body.new_password == body.current_password:
        raise BadRequest("New password must differ from the current one")
    accounts.check_password_policy(body.new_password, user.username)

    login_limiter.reset(key)
    accounts.set_password(user, body.new_password)
    audit.record(db, "password_change", user=user, request=request)
    return accounts.session_for(user)


# ---------------------------------------------------------------- 2FA management

@router.get("/2fa/status", response_model=schemas.MfaStatus)
def mfa_status(user: CurrentUser):
    return schemas.MfaStatus(enabled=bool(user.totp_enabled), username=user.username)


@router.post("/2fa/setup", response_model=schemas.MfaSetup)
def setup_2fa(user: CurrentUser, db: DB):
    # Never reveal the secret of an active 2FA enrolment.
    if user.totp_enabled:
        raise BadRequest("2FA is already enabled")
    user.totp_secret = crypto.generate_totp_secret()
    user.totp_last_counter = 0
    db.commit()
    return schemas.MfaSetup(secret=user.totp_secret, otpauth_url=crypto.otpauth_uri(user.totp_secret, user.username))


@router.post("/2fa/verify", response_model=schemas.MfaStatus)
def verify_2fa(body: schemas.MfaCodeRequest, user: CurrentUser, request: Request, db: DB):
    if user.totp_enabled:
        raise BadRequest("2FA is already enabled")
    if not user.totp_secret:
        raise BadRequest("Start 2FA setup first")
    if not _verify_totp(db, user, body.code):
        raise BadRequest("Invalid 2FA code")
    user.totp_enabled = 1
    audit.record(db, "2fa_enabled", user=user, request=request)
    return schemas.MfaStatus(enabled=True, username=user.username)


@router.post("/2fa/disable", response_model=schemas.MfaStatus)
def disable_2fa(body: schemas.MfaCodeRequest, user: CurrentUser, request: Request, db: DB):
    key = f"mfa-off:{user.id}"
    _throttle((mfa_limiter, key))
    if not user.totp_enabled:
        raise BadRequest("2FA is not enabled")
    if not _verify_totp(db, user, body.code):
        mfa_limiter.fail(key)
        raise BadRequest("Invalid 2FA code")
    user.totp_enabled = 0
    user.totp_secret = None
    audit.record(db, "2fa_disabled", user=user, request=request)
    return schemas.MfaStatus(enabled=False, username=user.username)
