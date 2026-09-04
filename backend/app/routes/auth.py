from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, auth, crypto
from .. import audit
from ..models import User
from ..security import login_limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _login_key(request: Request, username: str) -> str:
    return f"{request.client.host if request.client else '?'}:{username.lower()}"


@router.post("/login", response_model=schemas.LoginResponse)
def login(body: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    key = _login_key(request, body.username)
    allowed, retry_after = login_limiter.check(key)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many attempts. Try again in {retry_after}s.")

    user = db.query(User).filter(User.username == body.username).first()
    if not user or not auth.verify_login_password(body.password, user.login_hash):
        login_limiter.fail(key)
        audit.log(db, username=body.username, action="login_failed", ip=audit.client_ip(request))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    login_limiter.reset(key)
    audit.log(db, user_id=user.id, username=user.username, action="login", ip=audit.client_ip(request))

    if user.totp_enabled:
        mfa_token = auth.create_mfa_token(user.id)
        return schemas.LoginResponse(token="", username=user.username, is_admin=bool(user.is_admin), mfa_required=True, mfa_token=mfa_token)

    token = auth.create_access_token(user.id)
    return schemas.LoginResponse(token=token, username=user.username, is_admin=bool(user.is_admin))


@router.post("/2fa/confirm", response_model=schemas.LoginResponse)
def confirm_mfa(body: schemas.MfaConfirmLoginRequest, request: Request, db: Session = Depends(get_db)):
    user_id = auth.decode_mfa_token(body.mfa_token)
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=401, detail="2FA not enabled")
    if not crypto.totp_verify(user.totp_secret, body.code):
        audit.log(db, user_id=user.id, username=user.username, action="mfa_failed", ip=audit.client_ip(request))
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
    audit.log(db, user_id=user.id, username=user.username, action="login_mfa", ip=audit.client_ip(request))
    token = auth.create_access_token(user.id)
    return schemas.LoginResponse(token=token, username=user.username, is_admin=bool(user.is_admin))


@router.get("/2fa/setup", response_model=schemas.MfaSetupResponse)
def setup_2fa(user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    secret = user.totp_secret or crypto.generate_totp_secret()
    user.totp_secret = secret
    db.commit()
    return schemas.MfaSetupResponse(secret=secret, otpauth_url=crypto.otpauth_uri(secret, user.username))


@router.post("/2fa/verify")
def verify_2fa(body: schemas.MfaCodeRequest, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="No 2FA secret set up yet")
    if not crypto.totp_verify(user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    user.totp_enabled = 1
    db.commit()
    audit.log(db, user_id=user.id, username=user.username, action="2fa_enabled")
    return {"ok": True, "enabled": True}


@router.post("/2fa/disable")
def disable_2fa(body: schemas.MfaCodeRequest, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    if not user.totp_enabled:
        raise HTTPException(status_code=400, detail="2FA is not enabled")
    if not crypto.totp_verify(user.totp_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    user.totp_enabled = 0
    user.totp_secret = None
    db.commit()
    audit.log(db, user_id=user.id, username=user.username, action="2fa_disabled")
    return {"ok": True, "enabled": False}


@router.get("/2fa/status")
def mfa_status(user: User = Depends(auth.get_current_user)):
    return {"enabled": bool(user.totp_enabled), "username": user.username}


@router.get("/me", response_model=schemas.LoginResponse)
def me(user: User = Depends(auth.get_current_user)):
    return schemas.LoginResponse(token="", username=user.username, is_admin=bool(user.is_admin))