"""Cryptographic primitives: KDF, AEAD, sealed boxes, TOTP and password generation."""

import base64
import hashlib
import hmac
import json
import os
import secrets
import string
import struct
import time
from urllib.parse import quote

from argon2.low_level import Type, hash_secret_raw
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KEY_LEN = 32
NONCE_LEN = 12
SALT_LEN = 16


def b64e(data: bytes) -> str:
    return base64.b64encode(data).decode()


def b64d(data: str) -> bytes:
    return base64.b64decode(data)


# ---------------------------------------------------------------- key derivation

def generate_salt() -> bytes:
    return os.urandom(SALT_LEN)


def derive_key(password: str, salt: bytes, *, time_cost: int = 3) -> bytes:
    """Argon2id: 64 MiB, 2 lanes. Used for master passwords and API-token wrapping keys."""
    return hash_secret_raw(
        secret=password.encode(), salt=salt, time_cost=time_cost,
        memory_cost=64 * 1024, parallelism=2, hash_len=KEY_LEN, type=Type.ID,
    )


# ---------------------------------------------------------------- AES-256-GCM

def encrypt_bytes(data: bytes, key: bytes, aad: bytes | None = None) -> tuple[str, str]:
    """Return (ciphertext_b64, nonce_b64)."""
    nonce = os.urandom(NONCE_LEN)
    return b64e(AESGCM(key).encrypt(nonce, data, aad)), b64e(nonce)


def decrypt_bytes(ciphertext_b64: str, nonce_b64: str, key: bytes, aad: bytes | None = None) -> bytes:
    return AESGCM(key).decrypt(b64d(nonce_b64), b64d(ciphertext_b64), aad)


def encrypt_json(payload: dict, key: bytes) -> tuple[str, str]:
    return encrypt_bytes(json.dumps(payload, separators=(",", ":")).encode(), key)


def decrypt_json(ciphertext_b64: str, nonce_b64: str, key: bytes) -> dict:
    return json.loads(decrypt_bytes(ciphertext_b64, nonce_b64, key))


# ---------------------------------------------------------------- X25519 sealed boxes
# Lets anyone encrypt for a user (sharing) while only that user's vault can decrypt.

_SEAL_INFO = b"credvault/share/v1"


def generate_keypair() -> tuple[bytes, bytes]:
    """Return (private_raw, public_raw)."""
    priv = X25519PrivateKey.generate()
    return (
        priv.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw, serialization.NoEncryption()),
        priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw),
    )


def _seal_key(shared_secret: bytes, eph_pub: bytes, recipient_pub: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=KEY_LEN, salt=eph_pub + recipient_pub, info=_SEAL_INFO).derive(shared_secret)


def seal_json(payload: dict, recipient_pub: bytes) -> tuple[str, str, str]:
    """Encrypt for a public key. Return (ciphertext_b64, nonce_b64, ephemeral_pub_b64)."""
    eph = X25519PrivateKey.generate()
    eph_pub = eph.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key = _seal_key(eph.exchange(X25519PublicKey.from_public_bytes(recipient_pub)), eph_pub, recipient_pub)
    ct, nonce = encrypt_bytes(json.dumps(payload, separators=(",", ":")).encode(), key, aad=eph_pub)
    return ct, nonce, b64e(eph_pub)


def open_json(ciphertext_b64: str, nonce_b64: str, eph_pub_b64: str, recipient_priv: bytes) -> dict:
    priv = X25519PrivateKey.from_private_bytes(recipient_priv)
    eph_pub = b64d(eph_pub_b64)
    recipient_pub = priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    key = _seal_key(priv.exchange(X25519PublicKey.from_public_bytes(eph_pub)), eph_pub, recipient_pub)
    return json.loads(decrypt_bytes(ciphertext_b64, nonce_b64, key, aad=eph_pub))


# ---------------------------------------------------------------- tokens

def random_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# ---------------------------------------------------------------- TOTP (RFC 6238)

TOTP_STEP = 30


def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode()


def _hotp(secret: str, counter: int) -> str:
    digest = hmac.new(base64.b32decode(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"


def totp_match(secret: str, code: str, *, window: int = 1, after_counter: int = 0) -> int | None:
    """Return the matching time-step counter, or None.

    Counters at or below ``after_counter`` are rejected so a code can't be replayed.
    """
    code = str(code or "").strip()
    if len(code) != 6 or not code.isdigit():
        return None
    now = int(time.time()) // TOTP_STEP
    for counter in range(now - window, now + window + 1):
        if counter > after_counter and hmac.compare_digest(_hotp(secret, counter), code):
            return counter
    return None


def otpauth_uri(secret: str, username: str) -> str:
    label = quote(f"CredVault:{username}")
    return f"otpauth://totp/{label}?secret={secret}&issuer=CredVault&digits=6&period={TOTP_STEP}"


# ---------------------------------------------------------------- password generator

SYMBOLS = "!@#$%^&*()-_=+[]{};:,.?"


def generate_password(length: int = 20) -> str:
    """Random password guaranteed to contain upper, lower, digit and symbol."""
    pools = [string.ascii_uppercase, string.ascii_lowercase, string.digits, SYMBOLS]
    alphabet = "".join(pools)
    chars = [secrets.choice(p) for p in pools] + [secrets.choice(alphabet) for _ in range(max(length, 8) - len(pools))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)
