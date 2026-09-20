"""Runtime configuration for the Harvest Hero web app.

Everything comes from environment variables so the same image can run
locally, in CI, and on Fly.io without editing code.
"""

from __future__ import annotations

import os
import secrets


def _bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, "1" if default else "0").lower() in (
        "1", "true", "yes", "on"
    )


class Config:
    # ── Sessions ────────────────────────────────────────────────
    #   In production, set HARVESTHERO_SECRET_KEY to a long random
    #   string via `flyctl secrets set HARVESTHERO_SECRET_KEY=<val>`.
    #   Falling back to a per-process random key means restarting the
    #   server logs everyone out — deliberate for local dev but a
    #   disaster in prod, so we shout about it on startup.
    SECRET_KEY = os.environ.get("HARVESTHERO_SECRET_KEY") or secrets.token_urlsafe(48)
    SESSION_COOKIE_SECURE   = _bool("HARVESTHERO_COOKIE_SECURE", default=True)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 12  # 12 hours

    # ── App ─────────────────────────────────────────────────────
    APP_NAME    = "Harvest Hero"
    APP_VERSION = os.environ.get("APP_VERSION", "dev")

    # ── Ergonomics ──────────────────────────────────────────────
    TEMPLATES_AUTO_RELOAD = _bool("FLASK_TEMPLATES_AUTO_RELOAD", default=True)

    # ── CSRF (Flask-WTF) ────────────────────────────────────────
    # Enabled by default. Tests set app.config["WTF_CSRF_ENABLED"] = False
    # after create_app() to skip token generation without stripping the
    # <input> tags from templates. One dedicated test flips it back on
    # to prove CSRF actually blocks a tokenless POST.
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # tokens live as long as the session

    # ── Rate limiting (Flask-Limiter) ───────────────────────────
    # Enabled by default. Tests set app.config["RATELIMIT_ENABLED"] = False
    # to keep the test suite from tripping the per-route caps. A
    # dedicated test in test_rate_limit.py flips it back on to prove
    # the 11th login attempt in 5 minutes is rejected.
    RATELIMIT_ENABLED = True

    # ── Warnings ────────────────────────────────────────────────
    @classmethod
    def warn_if_insecure(cls) -> None:
        if not os.environ.get("HARVESTHERO_SECRET_KEY"):
            import warnings
            warnings.warn(
                "HARVESTHERO_SECRET_KEY is not set. Using a per-process "
                "random key. All sessions will be invalidated on restart. "
                "Set it via environment or `flyctl secrets set` before "
                "shipping.",
                RuntimeWarning,
            )
