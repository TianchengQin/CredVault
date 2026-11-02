from fastapi import HTTPException, status


class Unauthorized(HTTPException):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer"})


class SessionExpired(HTTPException):
    """401 for a missing/expired/revoked session; tells the UI to return to sign-in."""

    def __init__(self, detail: str = "Session expired, please sign in again"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, headers={"WWW-Authenticate": "Bearer", "X-Session-Expired": "1"})


class VaultLocked(HTTPException):
    """401 with a machine-readable header so the UI can tell 'locked' from 'signed out'."""

    def __init__(self, detail: str = "Vault is locked"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, headers={"X-Vault-Locked": "1"})


class Forbidden(HTTPException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail)


class NotFound(HTTPException):
    def __init__(self, detail: str = "Not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail)


class BadRequest(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail)


class Conflict(HTTPException):
    def __init__(self, detail: str):
        super().__init__(status.HTTP_409_CONFLICT, detail)


class TooManyAttempts(HTTPException):
    def __init__(self, retry_after: int, what: str = "attempts"):
        super().__init__(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Too many {what}. Try again in {retry_after}s.",
            headers={"Retry-After": str(retry_after)},
        )
