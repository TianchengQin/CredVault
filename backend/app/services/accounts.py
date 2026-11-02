"""Account lifecycle: creation, password policy, sessions and deletion."""

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from .. import schemas, security
from ..config import settings
from ..errors import BadRequest, Conflict
from ..models import AuditLog, SharedCredential, User
from ..vault_keys import vault_keys


def check_password_policy(password: str, username: str = "") -> None:
    if len(password) < settings.min_login_password:
        raise BadRequest(f"Password must be at least {settings.min_login_password} characters")
    if username and password.lower() == username.lower():
        raise BadRequest("Password must not equal the username")


def find_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.username) == username.strip().lower()))


def create(db: Session, username: str, password: str, *, is_admin: bool = False) -> User:
    check_password_policy(password, username)
    if find_by_username(db, username):
        raise Conflict("Username already exists")
    user = User(username=username, login_hash=security.hash_password(password), is_admin=int(is_admin))
    db.add(user)
    db.flush()
    return user


def session_for(user: User) -> schemas.Session:
    return schemas.Session(
        token=security.create_session_token(user.id, user.token_version or 0),
        **profile(user).model_dump(exclude={"token"}),
    )


def profile(user: User) -> schemas.Session:
    return schemas.Session(
        username=user.username, is_admin=bool(user.is_admin),
        mfa_enabled=bool(user.totp_enabled), must_change_password=bool(user.must_change_password),
    )


def set_password(user: User, password: str, *, must_change: bool = False) -> None:
    """Change the login password and revoke every existing session and unlocked vault."""
    user.login_hash = security.hash_password(password)
    user.must_change_password = int(must_change)
    user.token_version = (user.token_version or 0) + 1
    vault_keys.revoke_user(user.id)


def delete_user(db: Session, user: User) -> None:
    # Explicit clean-up so databases created before FK cascades existed stay consistent.
    db.execute(update(AuditLog).where(AuditLog.user_id == user.id).values(user_id=None))
    db.execute(delete(SharedCredential).where(
        (SharedCredential.owner_user_id == user.id) | (SharedCredential.recipient_user_id == user.id)
    ))
    db.delete(user)
    vault_keys.revoke_user(user.id)
