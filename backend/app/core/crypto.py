import base64
import os
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.credential_encryption_key.encode("utf-8")
    if len(key) < 32:
        key = key.ljust(32, b"0")
    else:
        key = key[:32]
    fkey = base64.urlsafe_b64encode(key)
    return Fernet(fkey)


def derive_pdk(password: str, salt_hex: str) -> bytes:
    """Derive a 32-byte Fernet key from password using PBKDF2-HMAC-SHA256."""
    salt_bytes = bytes.fromhex(salt_hex)
    pdk_raw = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        100_000,
        dklen=32
    )
    return base64.urlsafe_b64encode(pdk_raw)


def generate_random_key() -> str:
    """Generate a random 32-byte urlsafe base64-encoded key suitable for Fernet."""
    return Fernet.generate_key().decode("utf-8")


def generate_salt() -> str:
    """Generate a random 16-byte salt as hex string."""
    return os.urandom(16).hex()


def encrypt_uek(uek: str, pdk: bytes) -> str:
    f = Fernet(pdk)
    return f.encrypt(uek.encode("utf-8")).decode("utf-8")


def decrypt_uek(uek_encrypted: str, pdk: bytes) -> str:
    f = Fernet(pdk)
    return f.decrypt(uek_encrypted.encode("utf-8")).decode("utf-8")


def encrypt_secret(value: str, key: str = None) -> str:
    if key:
        f = Fernet(key.encode("utf-8"))
    else:
        f = _fernet()
    return f.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str, key: str = None) -> str:
    if key:
        try:
            f = Fernet(key.encode("utf-8"))
            return f.decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception:
            # If decryption fails with user-specific key, try legacy fallback
            pass
    f = _fernet()
    return f.decrypt(value.encode("utf-8")).decode("utf-8")


def encrypt_field(value: str | None, uek: str | None) -> str | None:
    if not value:
        return value
    if not uek:
        raise ValueError("Cannot encrypt data: User Encryption Key (UEK) is missing.")
    f = Fernet(uek.encode("utf-8"))
    return f.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_field_or_plaintext(value: str | None, uek: str | None) -> str | None:
    if not value:
        return value
    if uek:
        try:
            f = Fernet(uek.encode("utf-8"))
            return f.decrypt(value.encode("utf-8")).decode("utf-8")
        except Exception:
            pass
    # If decryption with uek fails or uek is missing, try legacy server key
    try:
        f = _fernet()
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except Exception:
        pass
    # If both decryption attempts fail, it's plaintext
    return value

