import base64

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, auth, crypto
from .. import audit
from ..models import ApiToken
from ..deps import get_vault_context, VaultContext

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.get("", response_model=list[schemas.ApiTokenOut])
def list_tokens(ctx: VaultContext = Depends(get_vault_context), db: Session = Depends(get_db)):
    tokens = db.query(ApiToken).filter(ApiToken.user_id == ctx.user.id).all()
    return [
        schemas.ApiTokenOut(
            id=t.id, name=t.name, permission=t.permission,
            created_at=t.created_at.isoformat() if t.created_at else "",
            last_used_at=t.last_used_at.isoformat() if t.last_used_at else None,
        )
        for t in tokens
    ]


@router.post("", response_model=schemas.ApiTokenCreated, status_code=201)
def create_token(
    body: schemas.ApiTokenIn,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if ctx.via_api_token:
        raise HTTPException(status_code=403, detail="Cannot create tokens via an API token")
    secret = auth.generate_api_token()
    salt = crypto.generate_salt()
    token_key = auth.derive_token_key(secret, salt)
    key_enc, nonce = crypto.encrypt_bytes(ctx.key, token_key)
    tok = ApiToken(
        user_id=ctx.user.id,
        name=body.name,
        permission=body.permission,
        token_hash=auth.hash_api_token(secret),
        token_salt=base64.b64encode(salt).decode(),
        key_enc=key_enc,
        nonce=nonce,
    )
    db.add(tok)
    db.commit()
    db.refresh(tok)
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="token_create", detail=tok.name, ip=audit.client_ip(request))
    return schemas.ApiTokenCreated(
        id=tok.id, name=tok.name, permission=tok.permission,
        created_at=tok.created_at.isoformat() if tok.created_at else "",
        token=secret,
    )


@router.delete("/{token_id}")
def revoke_token(
    token_id: int,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    tok = db.query(ApiToken).filter(ApiToken.id == token_id, ApiToken.user_id == ctx.user.id).first()
    if not tok:
        raise HTTPException(status_code=404, detail="Token not found")
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="token_revoke", detail=tok.name, ip=audit.client_ip(request))
    db.delete(tok)
    db.commit()
    return {"ok": True}
