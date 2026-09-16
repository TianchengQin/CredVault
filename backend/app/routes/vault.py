import base64
import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas, auth, crypto
from .. import audit
from ..models import User, Credential, SharedCredential
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
    token = auth.vault_store.put(key, user.id)
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
    token = auth.vault_store.put(candidate, user.id)
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


# ---------------- Sharing credentials with other users ----------------


@router.get("/shareable-users", response_model=list[schemas.ShareableUser])
def shareable_users(ctx: VaultContext = Depends(get_vault_context), db: Session = Depends(get_db)):
    """Users the current user can share a credential with (everyone but themself)."""
    users = db.query(User).filter(User.id != ctx.user.id).order_by(User.username).all()
    return [schemas.ShareableUser(id=u.id, username=u.username) for u in users]


def _shared_to_out(share: SharedCredential, key: bytes, owner: str = "") -> schemas.SharedCredentialFull:
    p = crypto.decrypt_json(share.encrypted_payload, share.nonce, key)
    return schemas.SharedCredentialFull(
        share_id=share.id, id=share.source_credential_id or share.id,
        name=share.name, secret=p.get("secret", ""),
        url=p.get("url", ""), username=p.get("username", ""),
        description=p.get("description", ""),
        category=share.category or "", favorite=bool(share.favorite),
        permission=share.permission, owner=owner,
    )


@router.get("/credentials/{cred_id}/shares", response_model=list[schemas.ShareInDetail])
def list_credential_shares(
    cred_id: int,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
):
    """Owner view: who a credential is shared with."""
    _get_own_credential(cred_id, ctx, db)
    shares = db.query(SharedCredential).filter(SharedCredential.source_credential_id == cred_id).all()
    recipients = {u.id: u.username for u in db.query(User).all()}
    return [
        schemas.ShareInDetail(
            id=s.id, name=s.name, permission=s.permission,
            recipient=recipients.get(s.recipient_user_id, ""),
            category=s.category or "", favorite=bool(s.favorite),
            created_at=s.created_at.isoformat() if s.created_at else "",
            source_credential_id=s.source_credential_id,
        )
        for s in shares
    ]


@router.post("/credentials/{cred_id}/share", response_model=schemas.ShareInDetail, status_code=201)
def share_credential(
    cred_id: int,
    body: schemas.ShareRequest,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Share a credential to another user with read/write permission.

    A decrypted copy is re-encrypted with the recipient's vault key, so only
    the recipient can decrypt it. The recipient must have unlocked their vault
    recently so their key is available in memory.
    """
    require_write(ctx)
    cred = _get_own_credential(cred_id, ctx, db)
    recipient = db.query(User).filter(User.username == body.username).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    if recipient.id == ctx.user.id:
        raise HTTPException(status_code=400, detail="Cannot share a credential with yourself")
    if recipient.vault_salt is None:
        raise HTTPException(status_code=400, detail="Recipient has not set up their vault yet")
    recipient_key = auth.vault_store.get_key_for_user(recipient.id)
    if recipient_key is None:
        raise HTTPException(
            status_code=400,
            detail="Recipient must unlock their vault first so the shared copy can be encrypted for them.",
        )

    payload = crypto.decrypt_json(cred.encrypted_payload, cred.nonce, ctx.key)
    ct, nonce = crypto.encrypt_json(payload, recipient_key)

    existing = db.query(SharedCredential).filter(
        SharedCredential.source_credential_id == cred.id,
        SharedCredential.recipient_user_id == recipient.id,
    ).first()
    if existing:
        existing.permission = body.permission
        existing.name = cred.name
        existing.encrypted_payload = ct
        existing.nonce = nonce
        existing.category = cred.category or ""
        existing.favorite = 1 if cred.favorite else 0
        db.commit()
        db.refresh(existing)
        audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="credential_share_updated", detail=f"{cred.name} -> {recipient.username} ({body.permission})", ip=audit.client_ip(request))
        return schemas.ShareInDetail(
            id=existing.id, name=existing.name, permission=existing.permission,
            recipient=recipient.username, category=existing.category or "",
            favorite=bool(existing.favorite),
            created_at=existing.created_at.isoformat() if existing.created_at else "",
            source_credential_id=existing.source_credential_id,
        )

    share = SharedCredential(
        owner_user_id=ctx.user.id, recipient_user_id=recipient.id,
        source_credential_id=cred.id, permission=body.permission,
        name=cred.name, encrypted_payload=ct, nonce=nonce,
        category=cred.category or "", favorite=1 if cred.favorite else 0,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="credential_share", detail=f"{cred.name} -> {recipient.username} ({body.permission})", ip=audit.client_ip(request))
    return schemas.ShareInDetail(
        id=share.id, name=share.name, permission=share.permission,
        recipient=recipient.username, category=share.category or "",
        favorite=bool(share.favorite),
        created_at=share.created_at.isoformat() if share.created_at else "",
        source_credential_id=share.source_credential_id,
    )


@router.patch("/credentials/{cred_id}/shares/{share_id}", response_model=schemas.ShareInDetail)
def update_share_permission(
    cred_id: int,
    share_id: int,
    body: schemas.SharePermissionUpdate,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    require_write(ctx)
    _get_own_credential(cred_id, ctx, db)
    share = db.query(SharedCredential).filter(
        SharedCredential.id == share_id,
        SharedCredential.owner_user_id == ctx.user.id,
        SharedCredential.source_credential_id == cred_id,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    share.permission = body.permission
    db.commit()
    db.refresh(share)
    recipient = db.query(User).filter(User.id == share.recipient_user_id).first()
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="credential_share_permission", detail=f"{share.name} -> {recipient.username if recipient else ''} ({body.permission})", ip=audit.client_ip(request))
    return schemas.ShareInDetail(
        id=share.id, name=share.name, permission=share.permission,
        recipient=recipient.username if recipient else "", category=share.category or "",
        favorite=bool(share.favorite),
        created_at=share.created_at.isoformat() if share.created_at else "",
        source_credential_id=share.source_credential_id,
    )


@router.delete("/credentials/{cred_id}/shares/{share_id}")
def unshare_credential(
    cred_id: int,
    share_id: int,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    require_write(ctx)
    _get_own_credential(cred_id, ctx, db)
    share = db.query(SharedCredential).filter(
        SharedCredential.id == share_id,
        SharedCredential.owner_user_id == ctx.user.id,
        SharedCredential.source_credential_id == cred_id,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    recipient = db.query(User).filter(User.id == share.recipient_user_id).first()
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="credential_unshare", detail=f"{share.name} <- {recipient.username if recipient else ''}", ip=audit.client_ip(request))
    db.delete(share)
    db.commit()
    return {"ok": True}


# ---------------- Recipient view of shared credentials ----------------


@router.get("/shared", response_model=list[schemas.SharedCredentialFull])
def list_shared_with_me(ctx: VaultContext = Depends(get_vault_context), db: Session = Depends(get_db)):
    """Credentials shared to the current user by others."""
    shares = db.query(SharedCredential).filter(SharedCredential.recipient_user_id == ctx.user.id).all()
    owners = {u.id: u.username for u in db.query(User).all()}
    out = []
    for s in shares:
        try:
            out.append(_shared_to_out(s, ctx.key, owner=owners.get(s.owner_user_id, "")))
        except Exception:
            continue
    return out


@router.get("/shared/{share_id}", response_model=schemas.SharedCredentialFull)
def get_shared_credential(
    share_id: int,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    share = db.query(SharedCredential).filter(
        SharedCredential.id == share_id,
        SharedCredential.recipient_user_id == ctx.user.id,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Shared credential not found")
    owner = db.query(User).filter(User.id == share.owner_user_id).first()
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="shared_credential_read", detail=share.name, ip=audit.client_ip(request))
    return _shared_to_out(share, ctx.key, owner=owner.username if owner else "")


@router.put("/shared/{share_id}", response_model=schemas.SharedCredentialFull)
def update_shared_credential(
    share_id: int,
    body: schemas.CredentialIn,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    share = db.query(SharedCredential).filter(
        SharedCredential.id == share_id,
        SharedCredential.recipient_user_id == ctx.user.id,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Shared credential not found")
    require_write(ctx)
    if share.permission != "write":
        raise HTTPException(status_code=403, detail="This share is read-only")
    ct, nonce = crypto.encrypt_json(_payload(body.secret, body.url, body.username, body.description), ctx.key)
    share.name = body.name
    share.encrypted_payload = ct
    share.nonce = nonce
    share.category = body.category or ""
    share.favorite = 1 if body.favorite else 0
    db.commit()
    db.refresh(share)
    owner = db.query(User).filter(User.id == share.owner_user_id).first()
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="shared_credential_update", detail=share.name, ip=audit.client_ip(request))
    return _shared_to_out(share, ctx.key, owner=owner.username if owner else "")


@router.delete("/shared/{share_id}")
def remove_shared_credential(
    share_id: int,
    ctx: VaultContext = Depends(get_vault_context),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Recipient removes a shared credential from their vault."""
    share = db.query(SharedCredential).filter(
        SharedCredential.id == share_id,
        SharedCredential.recipient_user_id == ctx.user.id,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="Shared credential not found")
    audit.log(db, user_id=ctx.user.id, username=ctx.user.username, action="shared_credential_remove", detail=share.name, ip=audit.client_ip(request))
    db.delete(share)
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
