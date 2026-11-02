"""Administration: user accounts and the audit trail. Admins never see vault contents."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from .. import audit, crypto, schemas
from ..deps import DB, AdminUser
from ..errors import BadRequest, NotFound
from ..models import AuditLog, User
from ..services import accounts
from ..services import vault as vault_svc
from ..vault_keys import vault_keys

router = APIRouter(prefix="/api/users", tags=["admin"])


def _out(u: User) -> schemas.UserOut:
    return schemas.UserOut(
        id=u.id, username=u.username, is_admin=bool(u.is_admin),
        vault_initialized=u.vault_initialized, mfa_enabled=bool(u.totp_enabled), created_at=u.created_at,
    )


def _target(db, admin: User, user_id: int, action: str) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise NotFound("User not found")
    if target.id == admin.id:
        raise BadRequest(f"You can't {action} your own account here")
    if target.is_admin:
        raise BadRequest(f"You can't {action} another administrator")
    return target


@router.get("", response_model=list[schemas.UserOut])
def list_users(_: AdminUser, db: DB):
    return [_out(u) for u in db.scalars(select(User).order_by(User.username))]


@router.post("", response_model=schemas.UserOut, status_code=201)
def create_user(body: schemas.UserCreate, admin: AdminUser, request: Request, db: DB):
    user = accounts.create(db, body.username, body.password)
    user.must_change_password = 1  # admin-chosen passwords are temporary
    audit.record(db, "user_create", user=admin, detail=user.username, request=request)
    return _out(user)


@router.delete("/{user_id}", response_model=schemas.Ok)
def delete_user(user_id: int, admin: AdminUser, request: Request, db: DB):
    target = _target(db, admin, user_id, "delete")
    name = target.username
    accounts.delete_user(db, target)
    audit.record(db, "user_delete", user=admin, detail=name, request=request)
    return schemas.Ok()


@router.post("/{user_id}/reset-vault", response_model=schemas.Ok)
def reset_vault(user_id: int, admin: AdminUser, request: Request, db: DB):
    target = _target(db, admin, user_id, "reset")
    vault_svc.wipe(db, target)
    vault_keys.revoke_user(target.id)
    audit.record(db, "vault_reset", user=admin, detail=target.username, request=request)
    return schemas.Ok()


@router.post("/{user_id}/reset-password", response_model=schemas.TempPassword)
def reset_password(user_id: int, admin: AdminUser, request: Request, db: DB):
    target = _target(db, admin, user_id, "reset")
    temp = crypto.generate_password(16)
    accounts.set_password(target, temp, must_change=True)
    audit.record(db, "password_reset", user=admin, detail=target.username, request=request)
    return schemas.TempPassword(username=target.username, temp_password=temp)


@router.get("/audit-log", response_model=list[schemas.AuditLogOut])
def audit_log(
    _: AdminUser, db: DB,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
    action: Annotated[str | None, Query(max_length=64)] = None,
):
    q = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if action:
        q = q.where(AuditLog.action == action)
    return list(db.scalars(q))
