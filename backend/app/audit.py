from fastapi import Request
from sqlalchemy.orm import Session

from .models import AuditLog, User


def client_ip(request: Request | None) -> str:
    return request.client.host if request is not None and request.client else ""


def record(
    db: Session,
    action: str,
    *,
    user: User | None = None,
    username: str | None = None,
    detail: str = "",
    request: Request | None = None,
    commit: bool = True,
) -> None:
    """Append an audit entry. Pass ``commit=False`` to join the caller's transaction."""
    db.add(AuditLog(
        user_id=user.id if user else None,
        username=(user.username if user else username or "")[:64],
        action=action,
        detail=detail[:500],
        ip=client_ip(request),
    ))
    if commit:
        db.commit()
