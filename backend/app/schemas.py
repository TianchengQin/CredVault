from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    is_admin: bool = False
    mfa_required: bool = False
    mfa_token: str = ""


class MfaConfirmLoginRequest(BaseModel):
    mfa_token: str
    code: str


class MfaCodeRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)


class MfaSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class VaultUnlockRequest(BaseModel):
    master_password: str


class VaultUnlockResponse(BaseModel):
    vault_token: str
    setup_required: bool = False


class CredentialIn(BaseModel):
    name: str = Field(..., min_length=1)
    secret: str = Field(..., min_length=1)
    url: str = ""
    username: str = ""
    description: str = ""
    category: str = ""
    favorite: bool = False


class CredentialOut(BaseModel):
    id: int
    name: str
    url: str = ""
    username: str = ""
    description: str = ""
    category: str = ""
    favorite: bool = False
    # secret omitted from default output; only returned when explicitly decrypted


class CredentialFull(CredentialOut):
    secret: str


class UserCreate(BaseModel):
    username: str
    password: str


class ApiTokenIn(BaseModel):
    name: str = Field(..., min_length=1)
    permission: str = Field(..., pattern="^(read|write)$")


class ApiTokenOut(BaseModel):
    id: int
    name: str
    permission: str
    created_at: str = ""
    last_used_at: str | None = None


class ApiTokenCreated(ApiTokenOut):
    token: str


class AuditLogOut(BaseModel):
    id: int
    username: str = ""
    action: str
    detail: str = ""
    ip: str = ""
    created_at: str = ""
