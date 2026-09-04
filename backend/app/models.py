from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    login_hash = Column(String, nullable=False)
    is_admin = Column(Integer, default=0)
    # optional 2FA (TOTP)
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Integer, default=0)
    # vault metadata: each user has their own encrypted vault
    vault_salt = Column(String, nullable=True)
    vault_ciphertext = Column(Text, nullable=True)
    vault_nonce = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    credentials = relationship("Credential", back_populates="owner", cascade="all, delete-orphan")
    api_tokens = relationship("ApiToken", back_populates="owner", cascade="all, delete-orphan")


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    permission = Column(String, nullable=False)  # "read" | "write"
    token_hash = Column(String, unique=True, index=True, nullable=False)
    token_salt = Column(String, nullable=False)
    # encrypted copy of the owner's vault key, decryptable with the token secret
    key_enc = Column(Text, nullable=False)
    nonce = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="api_tokens")


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    # name stored plaintext (it is shown in list), rest is encrypted
    name = Column(String, nullable=False)
    encrypted_payload = Column(Text, nullable=False)
    nonce = Column(String, nullable=False)
    category = Column(String, default="", index=True)
    favorite = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="credentials")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)
    detail = Column(Text, default="")
    ip = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
