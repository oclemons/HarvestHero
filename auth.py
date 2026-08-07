import hashlib
import hmac
import secrets


def hash_password(password: str) -> tuple:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt.

    Returns:
        (hex_hash, hex_salt)
    """
    salt = secrets.token_hex(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    )
    return pwd_hash.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Return True if *password* matches the stored hash.

    Uses hmac.compare_digest for a constant-time comparison so an
    attacker cannot infer the stored hash byte-by-byte from timing
    variations on repeated login attempts.
    """
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000
    )
    return hmac.compare_digest(pwd_hash.hex(), stored_hash)
