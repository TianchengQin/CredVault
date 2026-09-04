import base64
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, auth, crypto
from .. import audit
from ..models import User, Credential
from ..deps import get_vault_context, require_write, VaultContext
from ..security import unlock_limiter

router = APIRouter(prefix="/api/vault", tags=["vault"])


def _vault_token_header(x_vault_token: str | None = Header(default=None)) -> str | None:
    return x_vault_token


# ---------------- Vault unlock/setup (session only) ----------------


@router.get("/status")
def vault_status(user: User = Depends(auth.get_current_user)):
    return {"setup_required": user.vault_salt is None}


@router.post("/setup", response_model=schemas.VaultUnlockResponse)
def vault_setup(
    body: schemas.VaultUnlockRequest,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if user.vault_salt is not None:
        raise HTTPException(status_code=400, detail="Vault already initialized")
    salt = crypto.generate_salt()
    key = crypto.derive_key(body.master_password, salt)
    ct, nonce = crypto.encrypt_json({"marker": True}, key)
    user.vault_salt = base64.b64encode(salt).decode()
    user.vault_ciphertext = ct
    user.vault_nonce = nonce
    db.commit()
    token = auth.vault_store.put(key)
    audit.log(db, user_id=user.id, username=user.username, action="vault_setup", ip=audit.client_ip(request))
    return schemas.VaultUnlockResponse(vault_token=token, setup_required=False)


@router.post("/unlock", response_model=schemas.VaultUnlockResponse)
def vault_unlock(
    body: schemas.VaultUnlockRequest,
    user: User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    if user.vault_salt is None:
        return schemas.VaultUnlockResponse(vault_token="", setup_required=True)
    key = f"{request.client.host if request else '?'}:{user.id}"
    allowed, retry_after = unlock_limiter.check(key)
    if not allowed:
        raise HTTPException(status_code=429, detail=f"Too many unlock attempts. Try again in {retry_after}s.")
    salt = base64.b64decode(user.vault_salt)
    candidate = crypto.derive_key(body.master_password, salt)
    try:
        crypto.decrypt_json(user.vault_ciphertext, user.vault_nonce, candidate)
    except Exception:
        unlock_limiter.fail(key)
        audit.log(db, user_id=user.id, username=user.username, action="vault_unlock_failed", ip=audit.client_ip(request))
        raise HTTPException(status_code=401, detail="Wrong master password")
    unlock_limiter.reset(key)
    token = auth.vault_store.put(candidate)
    audit.log(db, user_id=user.id, username=user.username, action="vault_unlocked", ip=audit.client_ip(request))
    return schemas.VaultUnlockResponse(vault_token=token, setup_required=False)


@router.post("/lock")
def vault_lock(user: User = Depends(auth.get_current_user), token: str | None = Depends(_vault_token_header), db: Session = Depends(get_db)):
    auth.vault_store.revoke(token)
    audit.log(db, user_id=user.id, username=user.username, action="vault_locked")
    return {"ok": True}


# ---------------- Credential CRUD (session OR API token) ----------------


def _payload(secret, url, username, description):
    return {"secret": secret, "url": url, "username": username, "description": description}


def _to_out(cred: Credential, key: bytes) -> schemas.CredentialFull:
    p = crypto.decrypt_json(cred.encrypted_payload, cred.nonce, key)
    return schemas.CredentialFull(
        id=cred.id, name=cred.name, secret=p.get("secret", ""),
        url=p.get("url", ""), username=p.get("username", ""),
        description=p.get("description", ""),
        category=cred.category or "", favorite=bool(cred.favorite),
    )


def _get_own_credential(cred_id: int, ctx: VaultContext, db: Session) -> Credential:
    cred = db.query(Credential).filter(Credential.id == cred_id, Credential.user_id == ctx.user.id).first()
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    return cred


@router.get("/credentials", response_model=list[schemas.CredentialFull])
def list_credentials(ctx: VaultContext = Depends(get_vault_context), db: Session = Depends(get_db)):
    creds = db.query(Credential).filter(Credential.user_id == ctx.user.id).all()
    return [_to_out(c, ctx.key) for c in creds]


@router.post("/credentials", response_model=schemas.CredentialFull)
def create_credential(
    body: schemas.CredentialIn,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    require_write(ctx)
    ct, nonce = crypto.encrypt_json(_payload(body.secret, body.url, body.username, body.description), ctx.key)
    cred = Credential(
        user_id=ctx.user.id, name=body.name, encrypted_payload=ct, nonce=nonce,
        category=body.category or "", favorite=1 if body.favorite else 0,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="credential_create", detail=cred.name, ip=audit.client_ip(request))
    return _to_out(cred, ctx.key)


@router.get("/credentials/{cred_id}", response_model=schemas.CredentialFull)
def get_credential(
    cred_id: int,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    cred = _get_own_credential(cred_id, ctx, db)
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="credential_read", detail=cred.name, ip=audit.client_ip(request))
    return _to_out(cred, ctx.key)


@router.put("/credentials/{cred_id}", response_model=schemas.CredentialFull)
def update_credential(
    cred_id: int,
    body: schemas.CredentialIn,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    require_write(ctx)
    cred = _get_own_credential(cred_id, ctx, db)
    ct, nonce = crypto.encrypt_json(_payload(body.secret, body.url, body.username, body.description), ctx.key)
    cred.name = body.name
    cred.encrypted_payload = ct
    cred.nonce = nonce
    cred.category = body.category or ""
    cred.favorite = 1 if body.favorite else 0
    db.commit()
    db.refresh(cred)
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="credential_update", detail=cred.name, ip=audit.client_ip(request))
    return _to_out(cred, ctx.key)


@router.delete("/credentials/{cred_id}")
def delete_credential(
    cred_id: int,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    require_write(ctx)
    cred = _get_own_credential(cred_id, ctx, db)
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="credential_delete", detail=cred.name, ip=audit.client_ip(request))
    db.delete(cred)
    db.commit()
    return {"ok": True}


# ---------------- Backup / restore ----------------


@router.get("/export")
def export_vault(ctx: VaultContext = Depends(get_vault_context), db: Session = Depends(get_db), request: Request = None):
    require_write(ctx)
    creds = db.query(Credential).filter(Credential.user_id == ctx.user.id).all()
    data = [
        {
            "name": c.name, "category": c.category or "", "favorite": bool(c.favorite),
            **_payload(
                crypto.decrypt_json(c.encrypted_payload, c.nonce, ctx.key).get("secret", ""),
                crypto.decrypt_json(c.encrypted_payload, c.nonce, ctx.key).get("url", ""),
                crypto.decrypt_json(c.encrypted_payload, c.nonce, ctx.key).get("username", ""),
                crypto.decrypt_json(c.encrypted_payload, c.nonce, ctx.key).get("description", ""),
            ),
        }
        for c in creds
    ]
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="vault_export", ip=audit.client_ip(request))
    return Response(
        content=json.dumps(data, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": 'attachment; filename="credvault-backup.json"'},
    )


@router.post("/import")
def import_vault(body: dict, ctx: VaultContext = Depends(get_vault_context), db: Session = Depends(get_db), request: Request = None):
    require_write(ctx)
    items = body.get("items", [])
    if not isinstance(items, list):
        raise HTTPException(status_code=400, detail="Expected { items: [...] }")
    created = 0
    for item in items:
        if not isinstance(item, dict) or not item.get("name") or not item.get("secret"):
            continue
        ct, nonce = crypto.encrypt_json(_payload(item.get("secret"), item.get("url", ""), item.get("username", ""), item.get("description", "")), ctx.key)
        db.add(Credential(
            user_id=ctx.user.id, name=item["name"], encrypted_payload=ct, nonce=nonce,
            category=item.get("category", "") or "", favorite=1 if item.get("favorite") else 0,
        ))
        created += 1
    db.commit()
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="vault_import", detail=f"{created} items", ip=audit.client_ip(request))
    return {"ok": True, "imported": created}
