"""Sharing credentials between users.

Owners manage shares under ``/credentials/{id}/shares``; recipients see theirs under ``/shared``.
Shared copies are sealed to the recipient's public key, so the recipient need not be online.
"""

from fastapi import APIRouter, Request
from sqlalchemy import select

from .. import audit, schemas
from ..deps import DB, Vault, WritableVault
from ..errors import Forbidden, NotFound
from ..models import SharedCredential, User
from ..services import accounts
from ..services import vault as vault_svc

router = APIRouter(prefix="/api/vault", tags=["sharing"])


@router.get("/shareable-users", response_model=list[schemas.ShareableUser])
def shareable_users(ctx: Vault, db: DB):
    users = db.scalars(select(User).where(User.id != ctx.user.id).order_by(User.username))
    return [schemas.ShareableUser(id=u.id, username=u.username, can_receive=bool(u.public_key)) for u in users]


# ---------------------------------------------------------------- owner side

@router.get("/credentials/{cred_id}/shares", response_model=list[schemas.ShareOut])
def list_shares(cred_id: int, ctx: Vault, db: DB):
    vault_svc.own_credential(db, ctx.user, cred_id)
    rows = db.scalars(select(SharedCredential).where(
        SharedCredential.source_credential_id == cred_id, SharedCredential.owner_user_id == ctx.user.id,
    ))
    return [vault_svc.share_out(r) for r in rows]


@router.post("/credentials/{cred_id}/share", response_model=schemas.ShareOut, status_code=201)
def share_credential(cred_id: int, body: schemas.ShareRequest, ctx: WritableVault, request: Request, db: DB):
    cred = vault_svc.own_credential(db, ctx.user, cred_id)
    recipient = accounts.find_by_username(db, body.username)
    if recipient is None:
        raise NotFound("User not found")
    row = vault_svc.share(db, ctx.user, ctx.key, cred, recipient, body.permission)
    audit.record(db, "credential_share", user=ctx.user, request=request,
                 detail=f"{cred.name} -> {recipient.username} ({body.permission})")
    return vault_svc.share_out(row)


@router.patch("/credentials/{cred_id}/shares/{share_id}", response_model=schemas.ShareOut)
def update_share(cred_id: int, share_id: int, body: schemas.SharePermissionUpdate, ctx: WritableVault, request: Request, db: DB):
    row = vault_svc.owned_share(db, ctx.user, cred_id, share_id)
    row.permission = body.permission
    audit.record(db, "credential_share_permission", user=ctx.user, request=request,
                 detail=f"{row.name} -> {row.recipient.username} ({body.permission})")
    return vault_svc.share_out(row)


@router.delete("/credentials/{cred_id}/shares/{share_id}", response_model=schemas.Ok)
def unshare(cred_id: int, share_id: int, ctx: WritableVault, request: Request, db: DB):
    row = vault_svc.owned_share(db, ctx.user, cred_id, share_id)
    detail = f"{row.name} <- {row.recipient.username}"
    db.delete(row)
    audit.record(db, "credential_unshare", user=ctx.user, detail=detail, request=request)
    return schemas.Ok()


# ---------------------------------------------------------------- recipient side

@router.get("/shared", response_model=list[schemas.SharedCredentialOut])
def list_received(ctx: Vault, db: DB):
    rows = db.scalars(select(SharedCredential).where(SharedCredential.recipient_user_id == ctx.user.id).order_by(SharedCredential.name))
    out = []
    for row in rows:
        try:
            out.append(vault_svc.read_share(row, ctx.user, ctx.key))
        except Exception:  # an undecryptable legacy row must not break the whole list
            continue
    return out


@router.get("/shared/{share_id}", response_model=schemas.SharedCredentialOut)
def get_received(share_id: int, ctx: Vault, request: Request, db: DB):
    row = vault_svc.received_share(db, ctx.user, share_id)
    audit.record(db, "shared_credential_read", user=ctx.user, detail=row.name, request=request)
    return vault_svc.read_share(row, ctx.user, ctx.key)


@router.put("/shared/{share_id}", response_model=schemas.SharedCredentialOut)
def update_received(share_id: int, body: schemas.CredentialIn, ctx: WritableVault, request: Request, db: DB):
    row = vault_svc.received_share(db, ctx.user, share_id)
    if row.permission != "write":
        raise Forbidden("This share is read-only")
    vault_svc.update_received_share(row, ctx.user, body)
    audit.record(db, "shared_credential_update", user=ctx.user, detail=row.name, request=request)
    return vault_svc.read_share(row, ctx.user, ctx.key)


@router.delete("/shared/{share_id}", response_model=schemas.Ok)
def remove_received(share_id: int, ctx: WritableVault, request: Request, db: DB):
    row = vault_svc.received_share(db, ctx.user, share_id)
    db.delete(row)
    audit.record(db, "shared_credential_remove", user=ctx.user, detail=row.name, request=request)
    return schemas.Ok()
