"""Streaming encryption for MongoDB backup archives.

The backup contains every collection (users, portfolios, alerts and encrypted
exchange API keys), so it must not be left as a plain ``.json.gz`` file on the
host.  AES-GCM is used in 1 MiB chunks; the key comes from the
``BACKUP_ENCRYPTION_KEY`` environment variable and is never persisted next to
the archive.

Accepted key formats (32 bytes):
  * base64 / urlsafe-base64 (with or without padding)
  * 64 hex characters

If ``BACKUP_ENCRYPTION_KEY`` is empty, callers fall back to plaintext for
backwards compatibility but log a warning.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"FNBK1\x00"
CHUNK_SIZE = 1024 * 1024
_NONCE_PREFIX_SIZE = 4
_COUNTER_SIZE = 8
# AES-GCM adds a 16-byte authentication tag to every chunk.
_MAX_CHUNK = CHUNK_SIZE + 16


def decode_key(raw: str) -> bytes:
    """Decode a 32-byte key from base64/urlsafe-base64/hex."""
    raw = (raw or "").strip()
    if not raw:
        raise ValueError("empty backup encryption key")

    if len(raw) == 64:
        try:
            key = bytes.fromhex(raw)
            if len(key) == 32:
                return key
        except ValueError:
            pass

    padded = raw + "=" * (-len(raw) % 4)
    for decoder in (base64.urlsafe_b64decode, base64.b64decode):
        try:
            key = decoder(padded)
        except Exception:
            continue
        if len(key) == 32:
            return key

    raise ValueError(
        "BACKUP_ENCRYPTION_KEY must be 32 bytes encoded as base64 or 64 hex chars"
    )


def get_backup_key() -> bytes | None:
    """Return the configured key, or None when encryption is disabled."""
    raw = os.environ.get("BACKUP_ENCRYPTION_KEY", "").strip()
    return decode_key(raw) if raw else None


def is_encrypted(path: Path) -> bool:
    """Return True when *path* starts with the backup ciphertext magic."""
    try:
        with open(path, "rb") as f:
            return f.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def encrypt_file(src: Path, dst: Path, key: bytes) -> None:
    """Encrypt *src* into *dst* using chunked AES-GCM."""
    aes = AESGCM(key)
    nonce_prefix = os.urandom(_NONCE_PREFIX_SIZE)

    dst_fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with open(src, "rb") as fin, os.fdopen(dst_fd, "wb") as fout:
        fout.write(MAGIC)
        fout.write(nonce_prefix)

        counter = 0
        while True:
            chunk = fin.read(CHUNK_SIZE)
            if not chunk:
                break
            nonce = nonce_prefix + counter.to_bytes(_COUNTER_SIZE, "big")
            ciphertext = aes.encrypt(nonce, chunk, None)
            fout.write(len(ciphertext).to_bytes(4, "big"))
            fout.write(ciphertext)
            counter += 1

        fout.flush()
        os.fsync(fout.fileno())


def decrypt_file(src: Path, dst: Path, key: bytes) -> None:
    """Decrypt a chunked AES-GCM archive created by :func:`encrypt_file`."""
    aes = AESGCM(key)

    with open(src, "rb") as fin:
        if fin.read(len(MAGIC)) != MAGIC:
            raise ValueError("not an encrypted backup archive")
        nonce_prefix = fin.read(_NONCE_PREFIX_SIZE)
        if len(nonce_prefix) != _NONCE_PREFIX_SIZE:
            raise ValueError("truncated encrypted backup header")

        dst_fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(dst_fd, "wb") as fout:
            counter = 0
            while True:
                raw_len = fin.read(4)
                if not raw_len:
                    break
                if len(raw_len) != 4:
                    raise ValueError("truncated encrypted backup chunk length")
                chunk_len = int.from_bytes(raw_len, "big")
                if chunk_len <= 0 or chunk_len > _MAX_CHUNK:
                    raise ValueError("invalid encrypted backup chunk size")

                ciphertext = fin.read(chunk_len)
                if len(ciphertext) != chunk_len:
                    raise ValueError("truncated encrypted backup chunk")

                nonce = nonce_prefix + counter.to_bytes(_COUNTER_SIZE, "big")
                fout.write(aes.decrypt(nonce, ciphertext, None))
                counter += 1

            fout.flush()
            os.fsync(fout.fileno())
