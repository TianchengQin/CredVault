from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, auth, audit
from ..models import User, AuditLog

router = APIRouter(prefix="/api/users", tags=["users"])


def _require_admin(user: User):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user


@router.get("")
def list_users(user: User = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    _require_admin(user)
    users = db.query(User).all()
    return [{"id": u.id, "username": u.username, "is_admin": bool(u.is_admin),
             "vault_initialized": u.vault_salt is not None,
             "mfa_enabled": bool(u.totp_enabled)} for u in users]


@router.post("")
def create_user(body: schemas.UserCreate, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db), request: Request = None):
    _require_admin(user)
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    new_user = User(
        username=body.username,
        login_hash=auth.hash_login_password(body.password),
        is_admin=0,
    )
    db.add(new_user)
    db.commit()
    audit.log(db, user_id=user.id, username=user.username, action="user_create", detail=new_user.username, ip=audit.client_ip(request))
    return {"id": new_user.id, "username": new_user.username, "is_admin": False, "vault_initialized": False}


@router.delete("/{user_id}")
def delete_user(user_id: int, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db), request: Request = None):
    _require_admin(user)
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if target.is_admin:
        raise HTTPException(status_code=400, detail="Cannot delete an admin")
    audit.log(db, user_id=user.id, username=user.username, action="user_delete", detail=target.username, ip=audit.client_ip(request))
    db.delete(target)
    db.commit()
    return {"ok": True}


@router.post("/{user_id}/reset-vault")
def reset_user_vault(user_id: int, user: User = Depends(auth.get_current_user), db: Session = Depends(get_db), request: Request = None):
    _require_admin(user)
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot reset your own vault here")
    target.vault_salt = None
    target.vault_ciphertext = None
    target.vault_nonce = None
    # remove their credentials and API tokens so the vault restarts clean
    db.query(type(target).credentials.property.mapper.class_).filter_by(user_id=target.id).delete()
    db.query(type(target).api_tokens.property.mapper.class_).filter_by(user_id=target.id).delete()
    db.commit()
    audit.log(db, user_id=user.id, username=user.username, action="vault_reset", detail=target.username, ip=audit.client_ip(request))
    return {"ok": True}


@router.get("/audit-log")
def audit_log(user: User = Depends(auth.get_current_user), db: Session = Depends(get_db), limit: int = 200):
    _require_admin(user)
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 1000)).all()
    return [
        schemas.AuditLogOut(
            id=r.id, username=r.username or "", action=r.action, detail=r.detail or "",
            ip=r.ip or "", created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in rows
    ]