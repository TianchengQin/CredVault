"""Credential CRUD. Works with a session + unlocked vault or with an API token."""

from fastapi import APIRouter, Request
from sqlalchemy import select

from .. import audit, schemas
from ..deps import DB, Vault, WritableVault
from ..models import Credential
from ..services import vault as vault_svc

router = APIRouter(prefix="/api/vault/credentials", tags=["credentials"])


@router.get("", response_model=list[schemas.CredentialOut])
def list_credentials(ctx: Vault, db: DB):
    creds = db.scalars(select(Credential).where(Credential.user_id == ctx.user.id).order_by(Credential.name))
    return [vault_svc.read_credential(c, ctx.key) for c in creds]


@router.post("", response_model=schemas.CredentialOut, status_code=201)
def create_credential(body: schemas.CredentialIn, ctx: WritableVault, request: Request, db: DB):
    cred = vault_svc.write_credential(Credential(user_id=ctx.user.id), body, ctx.key)
    db.add(cred)
    audit.record(db, "credential_create", user=ctx.user, detail=cred.name, request=request)
    return vault_svc.read_credential(cred, ctx.key)


@router.get("/{cred_id}", response_model=schemas.CredentialOut)
def get_credential(cred_id: int, ctx: Vault, request: Request, db: DB):
    cred = vault_svc.own_credential(db, ctx.user, cred_id)
    audit.record(db, "credential_read", user=ctx.user, detail=cred.name, request=request)
    return vault_svc.read_credential(cred, ctx.key)


@router.put("/{cred_id}", response_model=schemas.CredentialOut)
def replace_credential(cred_id: int, body: schemas.CredentialIn, ctx: WritableVault, request: Request, db: DB):
    cred = vault_svc.write_credential(vault_svc.own_credential(db, ctx.user, cred_id), body, ctx.key)
    audit.record(db, "credential_update", user=ctx.user, detail=cred.name, request=request)
    return vault_svc.read_credential(cred, ctx.key)


@router.patch("/{cred_id}", response_model=schemas.CredentialOut)
def patch_credential(cred_id: int, body: schemas.CredentialPatch, ctx: WritableVault, request: Request, db: DB):
    cred = vault_svc.own_credential(db, ctx.user, cred_id)
    merged = vault_svc.merge_patch(vault_svc.read_credential(cred, ctx.key), body)
    vault_svc.write_credential(cred, merged, ctx.key)
    audit.record(db, "credential_update", user=ctx.user, detail=cred.name, request=request)
    return vault_svc.read_credential(cred, ctx.key)


@router.delete("/{cred_id}", response_model=schemas.Ok)
def delete_credential(cred_id: int, ctx: WritableVault, request: Request, db: DB):
    cred = vault_svc.own_credential(db, ctx.user, cred_id)
    vault_svc.detach_shares(db, cred)
    db.delete(cred)
    audit.record(db, "credential_delete", user=ctx.user, detail=cred.name, request=request)
    return schemas.Ok()
