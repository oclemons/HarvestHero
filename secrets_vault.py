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
    """Return the persistent machine-local Fernet key, creating one if needed.

    New keys are written to a temp file first and then renamed into
    place with os.replace(). A crash mid-write would otherwise leave
    a truncated .secret_key on disk — after which every future
    decrypt() would return "" and the operator would have to re-enter
    the LDAP service password from scratch to recover.
    """
    if os.path.exists(_KEY_PATH):
        with open(_KEY_PATH, "rb") as f:
            return f.read().strip()

    os.makedirs(DATA_DIR, exist_ok=True)
    key = Fernet.generate_key()
    tmp_path = _KEY_PATH + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(key)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    try:
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0600
    except OSError:
        pass
    # os.replace() is atomic on POSIX and Windows: the destination
    # either has the old file or the new file, never a partial one.
    os.replace(tmp_path, _KEY_PATH)
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
