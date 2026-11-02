"""Plaintext JSON export / import of a user's own credentials. Session only."""

import json

from fastapi import APIRouter, Request
from fastapi.responses import Response
from sqlalchemy import select

from .. import audit, schemas
from ..deps import DB, SessionVault
from ..models import Credential
from ..services import vault as vault_svc

router = APIRouter(prefix="/api/vault", tags=["backup"])

_EXPORT_FIELDS = {"name", "secret", "url", "username", "description", "category", "favorite"}


@router.post("/export")
def export_vault(ctx: SessionVault, request: Request, db: DB):
    creds = db.scalars(select(Credential).where(Credential.user_id == ctx.user.id).order_by(Credential.name))
    items = [vault_svc.read_credential(c, ctx.key).model_dump(include=_EXPORT_FIELDS) for c in creds]
    audit.record(db, "vault_export", user=ctx.user, detail=f"{len(items)} items", request=request)
    return Response(
        content=json.dumps({"version": 1, "items": items}, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="credvault-backup.json"', "Cache-Control": "no-store"},
    )


@router.post("/import", response_model=schemas.ImportResult)
def import_vault(body: schemas.ImportRequest, ctx: SessionVault, request: Request, db: DB):
    for item in body.items:
        db.add(vault_svc.write_credential(Credential(user_id=ctx.user.id), item, ctx.key))
    audit.record(db, "vault_import", user=ctx.user, detail=f"{len(body.items)} items", request=request)
    return schemas.ImportResult(imported=len(body.items))
