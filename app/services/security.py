"""
Security service for handling encryption and decryption of sensitive data (like API secrets).
"""

from __future__ import annotations

from cryptography.fernet import Fernet
from app.config import get_settings
from app.logger import get_logger

log = get_logger("security")

_fernet: Fernet | None = None
_cached_key: str | None = None


def get_fernet() -> Fernet:
    global _fernet, _cached_key
    settings = get_settings()
    key = settings.security.fernet_key
    if not key:
        raise ValueError("security.fernet_key is not configured in settings.json")
    if _fernet is None or _cached_key != key:
        _fernet = Fernet(key.encode("utf-8"))
        _cached_key = key
    return _fernet


def encrypt_data(raw_data: str) -> str:
    """Encrypts string data using Fernet symmetric encryption."""
    if not raw_data:
        return ""
    f = get_fernet()
    encrypted = f.encrypt(raw_data.encode("utf-8"))
    return encrypted.decode("utf-8")


def decrypt_data(encrypted_data: str) -> str:
    """Decrypts string data using Fernet symmetric encryption."""
    if not encrypted_data:
        return ""
    f = get_fernet()
    decrypted = f.decrypt(encrypted_data.encode("utf-8"))
    return decrypted.decode("utf-8")
