from datetime import datetime, timezone
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints, field_validator

Permission = Literal["read", "write"]
# SQLite hands back naive datetimes; they are UTC, so say so on the wire.
UtcDatetime = Annotated[datetime, AfterValidator(lambda d: d if d.tzinfo else d.replace(tzinfo=timezone.utc))]
Username = Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=64, pattern=r"^[A-Za-z0-9._@-]+$")]
Password = Annotated[str, StringConstraints(min_length=1, max_length=256)]
TotpCode = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^\d{6}$")]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------- auth

class LoginRequest(Model):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    password: Password


class RegisterRequest(Model):
    username: Username
    password: Password


class Session(BaseModel):
    """Returned by login/register/me. ``token`` is empty when MFA is still pending."""
    token: str = ""
    username: str
    is_admin: bool = False
    mfa_required: bool = False
    mfa_token: str = ""
    mfa_enabled: bool = False
    must_change_password: bool = False


class MfaConfirmRequest(Model):
    mfa_token: str = Field(max_length=2048)
    code: TotpCode


class MfaCodeRequest(Model):
    code: TotpCode


class MfaSetup(BaseModel):
    secret: str
    otpauth_url: str


class MfaStatus(BaseModel):
    enabled: bool
    username: str


class ChangePasswordRequest(Model):
    current_password: Password
    new_password: Password
    mfa_code: str = Field(default="", max_length=6)


# ---------------------------------------------------------------- vault

class VaultStatus(BaseModel):
    setup_required: bool


class MasterPassword(Model):
    master_password: Password


class VaultUnlocked(BaseModel):
    vault_token: str = ""
    setup_required: bool = False
    idle_seconds: int = 0


class CredentialIn(Model):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    secret: Annotated[str, StringConstraints(min_length=1, max_length=10_000)]
    url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] = ""
    username: Annotated[str, StringConstraints(max_length=256)] = ""
    description: Annotated[str, StringConstraints(max_length=5_000)] = ""
    category: Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] = ""
    favorite: bool = False

    def secret_payload(self) -> dict:
        return {"secret": self.secret, "url": self.url, "username": self.username, "description": self.description}


class CredentialPatch(Model):
    """Partial update; only the fields provided are changed."""
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)] | None = None
    secret: Annotated[str, StringConstraints(min_length=1, max_length=10_000)] | None = None
    url: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048)] | None = None
    username: Annotated[str, StringConstraints(max_length=256)] | None = None
    description: Annotated[str, StringConstraints(max_length=5_000)] | None = None
    category: Annotated[str, StringConstraints(strip_whitespace=True, max_length=64)] | None = None
    favorite: bool | None = None


class CredentialOut(BaseModel):
    id: int
    name: str
    secret: str
    url: str = ""
    username: str = ""
    description: str = ""
    category: str = ""
    favorite: bool = False
    updated_at: UtcDatetime | None = None


class SharedCredentialOut(CredentialOut):
    share_id: int
    permission: Permission
    owner: str = ""


class ImportItem(CredentialIn):
    model_config = ConfigDict(extra="ignore")  # tolerate extra keys from other exporters


class ImportRequest(Model):
    items: list[ImportItem] = Field(max_length=5_000)


class ImportResult(BaseModel):
    imported: int


# ---------------------------------------------------------------- sharing

class ShareRequest(Model):
    username: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
    permission: Permission


class SharePermissionUpdate(Model):
    permission: Permission


class ShareOut(BaseModel):
    id: int
    name: str
    permission: Permission
    recipient: str = ""
    created_at: UtcDatetime | None = None
    source_credential_id: int | None = None


class ShareableUser(BaseModel):
    id: int
    username: str
    can_receive: bool = True


# ---------------------------------------------------------------- tokens

class ApiTokenIn(Model):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
    permission: Permission


class ApiTokenOut(BaseModel):
    id: int
    name: str
    permission: Permission
    created_at: UtcDatetime | None = None
    last_used_at: UtcDatetime | None = None


class ApiTokenCreated(ApiTokenOut):
    token: str


# ---------------------------------------------------------------- admin

class UserCreate(Model):
    username: Username
    password: Password


class UserOut(BaseModel):
    id: int
    username: str
    is_admin: bool
    vault_initialized: bool
    mfa_enabled: bool
    created_at: UtcDatetime | None = None


class TempPassword(BaseModel):
    username: str
    temp_password: str


class AuditLogOut(BaseModel):
    id: int
    username: str = ""
    action: str
    detail: str = ""
    ip: str = ""
    created_at: UtcDatetime | None = None

    @field_validator("username", "detail", "ip", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return v or ""


class Ok(BaseModel):
    ok: bool = True
