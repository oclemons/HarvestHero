import hashlib
import hmac
import re
import secrets

# Current work factor for password hashing. OWASP's 2024 baseline for
# PBKDF2-HMAC-SHA256 is 600,000. Older records that were hashed at
# 100,000 (see LEGACY_PBKDF2_ITERATIONS below) are still accepted and
# transparently re-hashed at this stronger factor on the next successful
# login (see needs_rehash / rehash_password).
PBKDF2_ITERATIONS = 600_000
LEGACY_PBKDF2_ITERATIONS = 100_000
_ITERS_SEP = "$"

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


def _split_stored(stored_hash: str) -> tuple[int, str]:
    """Parse `iterations$hex` records. If no separator is present the
    record predates the encoded-iterations format and used the legacy
    work factor (100k). New records always carry their iteration count."""
    if _ITERS_SEP in stored_hash:
        iters_str, _, hex_part = stored_hash.partition(_ITERS_SEP)
        try:
            return int(iters_str), hex_part
        except ValueError:
            pass
    return LEGACY_PBKDF2_ITERATIONS, stored_hash


def hash_password(password: str) -> tuple:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt at
    the current work factor.

    Returns:
        (stored_hash, hex_salt), where stored_hash is "iterations$hex".
    """
    salt = secrets.token_hex(32)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return f"{PBKDF2_ITERATIONS}{_ITERS_SEP}{pwd_hash.hex()}", salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Return True if *password* matches the stored hash.

    Handles both the new "iterations$hex" format and the legacy raw hex
    format from records created before we bumped the work factor. Uses
    hmac.compare_digest for a constant-time comparison so an attacker
    cannot infer the stored hash byte-by-byte from timing variations
    on repeated login attempts.
    """
    iters, expected = _split_stored(stored_hash)
    pwd_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iters
    )
    return hmac.compare_digest(pwd_hash.hex(), expected)


def needs_rehash(stored_hash: str) -> bool:
    """Return True if a stored password was hashed at a weaker work
    factor than we use today. login_screen calls this after a
    successful login and, if True, transparently re-hashes the password
    at the current PBKDF2_ITERATIONS."""
    iters, _ = _split_stored(stored_hash)
    return iters < PBKDF2_ITERATIONS
