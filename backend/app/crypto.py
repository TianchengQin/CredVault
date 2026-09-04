import base64
import hashlib
import hmac
import json
import os
import struct
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Argon2 key derivation for vault-unlock master passwords


def generate_salt() -> bytes:
    return os.urandom(16)


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte AES key from a master password + salt using Argon2."""
    from argon2.low_level import hash_secret_raw, Type
    return hash_secret_raw(
        secret=password.encode(), salt=salt, time_cost=3, memory_cost=65536,
        parallelism=2, hash_len=32, type=Type.ID,
    )


def encrypt_json(payload: dict, key: bytes) -> tuple[str, str]:
    """Encrypt a dict -> (ciphertext_b64, nonce_b64)."""
    data = json.dumps(payload).encode()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, data, None)
    return (
        base64.b64encode(ct).decode(),
        base64.b64encode(nonce).decode(),
    )


def decrypt_json(ciphertext_b64: str, nonce_b64: str, key: bytes) -> dict:
    ct = base64.b64decode(ciphertext_b64)
    nonce = base64.b64decode(nonce_b64)
    aesgcm = AESGCM(key)
    data = aesgcm.decrypt(nonce, ct, None)
    return json.loads(data.decode())


def encrypt_bytes(data: bytes, key: bytes) -> tuple[str, str]:
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ct = aesgcm.encrypt(nonce, data, None)
    return base64.b64encode(ct).decode(), base64.b64encode(nonce).decode()


def decrypt_bytes(ciphertext_b64: str, nonce_b64: str, key: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(
        base64.b64decode(nonce_b64), base64.b64decode(ciphertext_b64), None
    )


# ---- TOTP (RFC 6238) for optional 2FA ----

def generate_totp_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode()


def _totp(secret: str, counter: int) -> int:
    key = base64.b32decode(secret)
    msg = struct.pack(">Q", counter)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[19] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return value % 1_000_000


def totp_verify(secret: str, code: str, window: int = 1) -> bool:
    try:
        expected = int(str(code).strip())
    except (ValueError, TypeError):
        return False
    now = int(time.time()) // 30
    return any(_totp(secret, now + i) == expected for i in range(-window, window + 1))


def otpauth_uri(secret: str, username: str) -> str:
    return f"otpauth://totp/CredVault:{username}?secret={secret}&issuer=CredVault"


def generate_password(length: int = 20, upper=True, lower=True, digits=True, symbols=True) -> str:
    import secrets as _secrets
    import string as _string
    pools = ""
    if upper:
        pools += _string.ascii_uppercase
    if lower:
        pools += _string.ascii_lowercase
    if digits:
        pools += _string.digits
    if symbols:
        pools += "!@#$%^&*()-_=+[]{};:,.?"
    if not pools:
        pools = _string.ascii_letters + _string.digits
    return "".join(_secrets.choice(pools) for _ in range(length))
