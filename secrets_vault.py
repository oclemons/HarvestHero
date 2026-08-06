"""secrets_vault.py — Encrypt/decrypt local secrets at rest.

The LDAP service password and other locally-stored secrets used to be
saved in `config.json` in plaintext. This module encrypts those values
with Fernet (AES-128-CBC + HMAC-SHA256) using a machine-local key that
is generated on first use and stored with restricted file permissions.

Encrypted values are stored with the "enc:v1:" prefix so the app can
tell whether a value has already been migrated.
"""

from __future__ import annotations

import os
import stat

from cryptography.fernet import Fernet, InvalidToken

from paths import DATA_DIR

_KEY_PATH = os.path.join(DATA_DIR, ".secret_key")
_PREFIX = "enc:v1:"


def _load_or_create_key() -> bytes:
    """Return the persistent machine-local Fernet key, creating one if needed."""
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as f:
            return f.read().strip()

    os.makedirs(DATA_DIR, exist_ok=True)
    key = Fernet.generate_key()
    with open(_KEY_PATH, "wb") as f:
        f.write(key)
    try:
        os.chmod(_KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass
    return key


def _cipher() -> Fernet:
    return Fernet(_load_or_create_key())


def encrypt(value: str) -> str:
    """Encrypt `value` and return an `enc:v1:...` string.

    Empty strings are returned unchanged so we don't waste ciphertext
    on an unset field.
    """
    if not value:
        return ""
    token = _cipher().encrypt(value.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt(value: str) -> str:
    """Decrypt an `enc:v1:...` string. Plain strings pass through so
    old config files remain readable during migration."""
    if not value:
        return ""
    if not value.startswith(_PREFIX):
        return value  # legacy plaintext — caller may re-save encrypted
    try:
        return _cipher().decrypt(value[len(_PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken:
        return ""


def is_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(_PREFIX)
