import base64

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


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
