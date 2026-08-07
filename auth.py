import hashlib
import hmac
import re
import secrets

MIN_PASSWORD_LENGTH = 8


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Return (ok, error_message).

    A password is accepted if it is at least MIN_PASSWORD_LENGTH characters
    long and contains at least three of the four character classes
    (lowercase letter, uppercase letter, digit, symbol). The requirement is
    intentionally moderate — strong enough to lock out trivial passwords
    like 'password1' without punishing users of long passphrases.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters."

    classes = sum([
        bool(re.search(r"[a-z]", password)),
        bool(re.search(r"[A-Z]", password)),
        bool(re.search(r"\d",   password)),
        bool(re.search(r"[^A-Za-z0-9]", password)),
    ])
    if classes < 3:
        return False, (
            "Password must include at least three of: lowercase, "
            "uppercase, digits, symbols."
        )
    return True, ""


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
