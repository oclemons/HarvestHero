"""login_throttle.py — In-memory failed-login tracking for the login screen.

A determined attacker who reaches the login screen used to be able to
guess passwords as fast as they could type. This module tracks failed
attempts per username in-process and returns a `locked_seconds`
countdown once the threshold is exceeded.

State resets when the app restarts (this is a desktop app, not a public
service), which is a deliberate trade-off: it prevents a locked-out
legitimate user from being permanently blocked by a stale counter, and
still forces an attacker to pay a real time cost.
"""

from __future__ import annotations

import time
from typing import Dict

# 5 attempts, then a 30-second cooldown that doubles each further block.
_MAX_ATTEMPTS = 5
_BASE_LOCK_SECONDS = 30
_MAX_LOCK_SECONDS = 15 * 60  # cap at 15 minutes

# {username: {"count": int, "locked_until": epoch_seconds, "blocks": int}}
_state: Dict[str, dict] = {}


def _entry(username: str) -> dict:
    key = username.strip().lower()
    e = _state.get(key)
    if e is None:
        e = {"count": 0, "locked_until": 0.0, "blocks": 0}
        _state[key] = e
    return e


def locked_seconds(username: str) -> int:
    """Return the number of seconds left in the current lockout for
    `username`, or 0 if the account is not currently locked."""
    e = _entry(username)
    remaining = e["locked_until"] - time.monotonic()
    return int(remaining) if remaining > 0 else 0


def record_failure(username: str) -> int:
    """Increment the failed-attempt counter and, if the threshold is
    crossed, arm a lockout with exponential back-off. Returns the
    number of seconds the account is locked for (0 if not yet locked)."""
    e = _entry(username)
    e["count"] += 1
    if e["count"] >= _MAX_ATTEMPTS:
        e["blocks"] += 1
        lock_for = min(_BASE_LOCK_SECONDS * (2 ** (e["blocks"] - 1)),
                       _MAX_LOCK_SECONDS)
        e["locked_until"] = time.monotonic() + lock_for
        e["count"] = 0  # start the next window fresh
        return int(lock_for)
    return 0


def record_success(username: str) -> None:
    """Clear all failure state for `username` after a successful login."""
    _state.pop(username.strip().lower(), None)


def reset_all() -> None:
    """Test helper. Clear the entire in-memory state."""
    _state.clear()
