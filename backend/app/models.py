from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    login_hash: Mapped[str] = mapped_column(String)
    is_admin: Mapped[int] = mapped_column(Integer, default=0)
    # set after an admin reset: the user must pick a new login password
    must_change_password: Mapped[int] = mapped_column(Integer, default=0)
    # bumped on password change/reset; embedded in JWTs to revoke old sessions
    token_version: Mapped[int] = mapped_column(Integer, default=0)

    # optional TOTP 2FA
    totp_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    totp_enabled: Mapped[int] = mapped_column(Integer, default=0)
    totp_last_counter: Mapped[int] = mapped_column(Integer, default=0)  # replay guard

    # vault: key derived from the master password; the marker proves a candidate key
    vault_salt: Mapped[str | None] = mapped_column(String, nullable=True)
    vault_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    vault_nonce: Mapped[str | None] = mapped_column(String, nullable=True)

    # X25519 keypair for receiving shares; the private key is wrapped by the vault key
    public_key: Mapped[str | None] = mapped_column(String, nullable=True)
    private_key_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    private_key_nonce: Mapped[str | None] = mapped_column(String, nullable=True)

    credentials: Mapped[list["Credential"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    api_tokens: Mapped[list["ApiToken"]] = relationship(back_populates="owner", cascade="all, delete-orphan")

    @property
    def vault_initialized(self) -> bool:
        return self.vault_salt is not None


class ApiToken(TimestampMixin, Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    permission: Mapped[str] = mapped_column(String(8))  # "read" | "write"
    token_hash: Mapped[str] = mapped_column(String, unique=True, index=True)
    token_salt: Mapped[str] = mapped_column(String)
    # the owner's vault key, wrapped with a key derived from the token secret
    key_enc: Mapped[str] = mapped_column(Text)
    nonce: Mapped[str] = mapped_column(String)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner: Mapped[User] = relationship(back_populates="api_tokens")


class Credential(TimestampMixin, Base):
    __tablename__ = "credentials"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))  # plaintext so lists can render without decrypting
    encrypted_payload: Mapped[str] = mapped_column(Text)
    nonce: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String(64), default="", index=True)
    favorite: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(back_populates="credentials")


class SharedCredential(TimestampMixin, Base):
    """A snapshot of a credential shared with another user.

    The payload is sealed to the recipient's X25519 public key (``ephemeral_pub``
    set), so it can be created without the recipient being online. Rows with no
    ``ephemeral_pub`` are legacy shares encrypted directly with the recipient's
    vault key; they are re-sealed the next time the recipient unlocks.
    """

    __tablename__ = "shared_credentials"
    __table_args__ = (UniqueConstraint("source_credential_id", "recipient_user_id", name="uq_share_source_recipient"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_credential_id: Mapped[int | None] = mapped_column(ForeignKey("credentials.id", ondelete="SET NULL"), nullable=True)
    permission: Mapped[str] = mapped_column(String(8))
    name: Mapped[str] = mapped_column(String(200))
    encrypted_payload: Mapped[str] = mapped_column(Text)
    nonce: Mapped[str] = mapped_column(String)
    ephemeral_pub: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str] = mapped_column(String(64), default="", index=True)
    favorite: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    owner: Mapped[User] = relationship(foreign_keys=[owner_user_id])
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_user_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    detail: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
