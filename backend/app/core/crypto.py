import base64
import os
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger("ai_ensemble.crypto")


def _fernet() -> Fernet:
    key = settings.credential_encryption_key.encode("utf-8")
    # Use SHA-256 to derive a proper 32-byte key instead of manual padding
    key = hashlib.sha256(key).digest()
    fkey = base64.urlsafe_b64encode(key)
    return Fernet(fkey)


def derive_pdk(password: str, salt_hex: str, iterations: int = 600_000) -> bytes:
    """Derive a 32-byte Fernet key from password using PBKDF2-HMAC-SHA256.

    Default iteration count is 600,000 (OWASP 2023+ guidance).
    Legacy users derived with 100,000 iterations are migrated on next login.
    """
    salt_bytes = bytes.fromhex(salt_hex)
    pdk_raw = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt_bytes,
        iterations,
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
        except (InvalidToken, ValueError) as e:
            logger.debug("User key decryption failed, trying legacy: %s", e)
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
        except (InvalidToken, ValueError):
            pass
    # If decryption with uek fails or uek is missing, try legacy server key
    try:
        f = _fernet()
        return f.decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        pass
    # If both decryption attempts fail, it's plaintext
    return value

