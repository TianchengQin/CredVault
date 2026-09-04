from .models import AuditLog


def log(db, user_id=None, username=None, action="", detail="", ip="") -> None:
    """Record an entry in the audit trail."""
    db.add(
        AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            detail=detail,
            ip=ip,
        )
    )
    db.commit()


def client_ip(request) -> str:
    return request.client.host if request.client else ""
