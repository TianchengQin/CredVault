"""API tokens for agents. Managed only from an interactive session, never by a token."""

from fastapi import APIRouter, Request
from sqlalchemy import select

from .. import audit, crypto, schemas
from ..deps import API_TOKEN_KDF_COST, DB, SessionVault
from ..errors import NotFound
from ..models import ApiToken

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


def _out(t: ApiToken) -> schemas.ApiTokenOut:
    return schemas.ApiTokenOut(id=t.id, name=t.name, permission=t.permission, created_at=t.created_at, last_used_at=t.last_used_at)


@router.get("", response_model=list[schemas.ApiTokenOut])
def list_tokens(ctx: SessionVault, db: DB):
    return [_out(t) for t in db.scalars(select(ApiToken).where(ApiToken.user_id == ctx.user.id).order_by(ApiToken.id))]


@router.post("", response_model=schemas.ApiTokenCreated, status_code=201)
def create_token(body: schemas.ApiTokenIn, ctx: SessionVault, request: Request, db: DB):
    secret = "cv_" + crypto.random_token()
    salt = crypto.generate_salt()
    key_enc, nonce = crypto.encrypt_bytes(ctx.key, crypto.derive_key(secret, salt, time_cost=API_TOKEN_KDF_COST))
    token = ApiToken(
        user_id=ctx.user.id, name=body.name, permission=body.permission,
        token_hash=crypto.sha256_hex(secret), token_salt=crypto.b64e(salt), key_enc=key_enc, nonce=nonce,
    )
    db.add(token)
    audit.record(db, "token_create", user=ctx.user, detail=f"{token.name} ({token.permission})", request=request)
    return schemas.ApiTokenCreated(**_out(token).model_dump(), token=secret)


@router.delete("/{token_id}", response_model=schemas.Ok)
def revoke_token(token_id: int, ctx: SessionVault, request: Request, db: DB):
    token = db.scalar(select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == ctx.user.id))
    if token is None:
        raise NotFound("Token not found")
    db.delete(token)
    audit.record(db, "token_revoke", user=ctx.user, detail=token.name, request=request)
    return schemas.Ok()
