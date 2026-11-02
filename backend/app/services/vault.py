"""Vault business logic: key setup/unlock, credential (de)serialisation and sharing."""

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from .. import crypto, schemas
from ..errors import BadRequest, NotFound
from ..models import Credential, SharedCredential, User

_MARKER = {"marker": True}


# ---------------------------------------------------------------- keys

def setup(user: User, master_password: str) -> bytes:
    """Initialise a user's vault and return the derived key."""
    salt = crypto.generate_salt()
    key = crypto.derive_key(master_password, salt)
    user.vault_salt = crypto.b64e(salt)
    user.vault_ciphertext, user.vault_nonce = crypto.encrypt_json(_MARKER, key)
    _create_keypair(user, key)
    return key


def try_unlock(user: User, master_password: str) -> bytes | None:
    """Return the vault key if the master password is right, else None."""
    key = crypto.derive_key(master_password, crypto.b64d(user.vault_salt))
    try:
        crypto.decrypt_json(user.vault_ciphertext, user.vault_nonce, key)
    except Exception:
        return None
    return key


def on_unlocked(db: Session, user: User, key: bytes) -> None:
    """Upgrade path for vaults created before sharing used public keys."""
    if not user.public_key:
        _create_keypair(user, key)
    for share in db.scalars(select(SharedCredential).where(
        SharedCredential.recipient_user_id == user.id, SharedCredential.ephemeral_pub.is_(None),
    )):
        try:
            payload = crypto.decrypt_json(share.encrypted_payload, share.nonce, key)
        except Exception:
            continue
        _seal_share(share, payload, crypto.b64d(user.public_key))


def wipe(db: Session, user: User) -> None:
    """Forget a vault entirely (lost master password).

    Credentials, API tokens and shares *received* (now undecryptable) are deleted.
    Copies this user shared out stay with their recipients, detached from the source.
    """
    user.vault_salt = user.vault_ciphertext = user.vault_nonce = None
    user.public_key = user.private_key_enc = user.private_key_nonce = None
    db.execute(delete(SharedCredential).where(SharedCredential.recipient_user_id == user.id))
    db.execute(update(SharedCredential).where(SharedCredential.owner_user_id == user.id).values(source_credential_id=None))
    user.credentials.clear()
    user.api_tokens.clear()


def _create_keypair(user: User, key: bytes) -> None:
    priv, pub = crypto.generate_keypair()
    user.public_key = crypto.b64e(pub)
    user.private_key_enc, user.private_key_nonce = crypto.encrypt_bytes(priv, key)


def _private_key(user: User, key: bytes) -> bytes:
    return crypto.decrypt_bytes(user.private_key_enc, user.private_key_nonce, key)


# ---------------------------------------------------------------- credentials

def own_credential(db: Session, user: User, cred_id: int) -> Credential:
    cred = db.scalar(select(Credential).where(Credential.id == cred_id, Credential.user_id == user.id))
    if cred is None:
        raise NotFound("Credential not found")
    return cred


def write_credential(cred: Credential, data: schemas.CredentialIn, key: bytes) -> Credential:
    cred.name = data.name
    cred.category = data.category
    cred.favorite = int(data.favorite)
    cred.encrypted_payload, cred.nonce = crypto.encrypt_json(data.secret_payload(), key)
    return cred


def read_credential(cred: Credential, key: bytes) -> schemas.CredentialOut:
    p = crypto.decrypt_json(cred.encrypted_payload, cred.nonce, key)
    return schemas.CredentialOut(
        id=cred.id, name=cred.name, category=cred.category or "", favorite=bool(cred.favorite),
        secret=p.get("secret", ""), url=p.get("url", ""), username=p.get("username", ""),
        description=p.get("description", ""), updated_at=cred.updated_at,
    )


def merge_patch(current: schemas.CredentialOut, patch: schemas.CredentialPatch) -> schemas.CredentialIn:
    data = current.model_dump(include=set(schemas.CredentialIn.model_fields))
    data.update(patch.model_dump(exclude_unset=True, exclude_none=True))
    return schemas.CredentialIn(**data)


def detach_shares(db: Session, cred: Credential) -> None:
    """Keep recipients' snapshots when the source credential is deleted."""
    db.execute(update(SharedCredential).where(SharedCredential.source_credential_id == cred.id).values(source_credential_id=None))


# ---------------------------------------------------------------- sharing

def _seal_share(share: SharedCredential, payload: dict, recipient_pub: bytes) -> None:
    share.encrypted_payload, share.nonce, share.ephemeral_pub = crypto.seal_json(payload, recipient_pub)


def share(db: Session, owner: User, key: bytes, cred: Credential, recipient: User, permission: str) -> SharedCredential:
    if recipient.id == owner.id:
        raise BadRequest("You can't share a credential with yourself")
    if not recipient.public_key:
        raise BadRequest(f"{recipient.username} must set up (or unlock) their vault before they can receive shares")

    payload = crypto.decrypt_json(cred.encrypted_payload, cred.nonce, key)
    row = db.scalar(select(SharedCredential).where(
        SharedCredential.source_credential_id == cred.id,
        SharedCredential.recipient_user_id == recipient.id,
    )) or SharedCredential(owner_user_id=owner.id, recipient_user_id=recipient.id, source_credential_id=cred.id)
    row.permission = permission
    row.name, row.category, row.favorite = cred.name, cred.category or "", cred.favorite or 0
    _seal_share(row, payload, crypto.b64d(recipient.public_key))
    db.add(row)
    return row


def owned_share(db: Session, owner: User, cred_id: int, share_id: int) -> SharedCredential:
    row = db.scalar(select(SharedCredential).where(
        SharedCredential.id == share_id,
        SharedCredential.owner_user_id == owner.id,
        SharedCredential.source_credential_id == cred_id,
    ))
    if row is None:
        raise NotFound("Share not found")
    return row


def received_share(db: Session, recipient: User, share_id: int) -> SharedCredential:
    row = db.scalar(select(SharedCredential).where(
        SharedCredential.id == share_id, SharedCredential.recipient_user_id == recipient.id,
    ))
    if row is None:
        raise NotFound("Shared credential not found")
    return row


def read_share(row: SharedCredential, recipient: User, key: bytes) -> schemas.SharedCredentialOut:
    if row.ephemeral_pub:
        p = crypto.open_json(row.encrypted_payload, row.nonce, row.ephemeral_pub, _private_key(recipient, key))
    else:
        p = crypto.decrypt_json(row.encrypted_payload, row.nonce, key)  # legacy
    return schemas.SharedCredentialOut(
        share_id=row.id, id=row.id, name=row.name, permission=row.permission,
        owner=row.owner.username if row.owner else "",
        category=row.category or "", favorite=bool(row.favorite),
        secret=p.get("secret", ""), url=p.get("url", ""), username=p.get("username", ""),
        description=p.get("description", ""), updated_at=row.updated_at,
    )


def update_received_share(row: SharedCredential, recipient: User, data: schemas.CredentialIn) -> None:
    row.name, row.category, row.favorite = data.name, data.category, int(data.favorite)
    _seal_share(row, data.secret_payload(), crypto.b64d(recipient.public_key))


def share_out(row: SharedCredential) -> schemas.ShareOut:
    return schemas.ShareOut(
        id=row.id, name=row.name, permission=row.permission,
        recipient=row.recipient.username if row.recipient else "",
        created_at=row.created_at, source_credential_id=row.source_credential_id,
    )
