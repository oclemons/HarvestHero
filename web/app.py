"""Harvest Hero — web application entry point.

Uses a small app factory so tests can build isolated app instances
without touching the module-level state. The factory also handles the
import gymnastics that let us reuse ``database.py`` / ``auth.py`` from
the repo root without polluting sys.path in every caller.
"""

from __future__ import annotations

import os
import sys

# Make the repo root importable so we can reuse the desktop app's
# database and auth code.  Doing this in one place beats each route
# file re-doing sys.path.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from flask import Flask, redirect, url_for
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import csrf, limiter, login_manager, talisman


# Content Security Policy. Any script/style/font/image the app pulls
# in via the base template must be listed here or the browser will
# refuse to load it. Update alongside base.html.
_CSP = {
    "default-src":     "'self'",
    "script-src":      ["'self'", "https://cdn.tailwindcss.com",
                        "https://unpkg.com"],
    "style-src":       ["'self'", "'unsafe-inline'"],  # Tailwind CDN emits inline <style>
    "img-src":         ["'self'", "data:"],
    "font-src":        ["'self'", "data:"],
    "connect-src":     "'self'",
    "frame-ancestors": "'none'",
    "form-action":     "'self'",
    "base-uri":        "'self'",
    "object-src":      "'none'",
}

_PERMISSIONS_POLICY = {
    "geolocation":  "()",
    "microphone":   "()",
    "camera":       "()",
    "payment":      "()",
    "usb":          "()",
    "gyroscope":    "()",
    "magnetometer": "()",
}


def create_app(config: type = Config) -> Flask:
    """Build a configured Flask app."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config)
    config.warn_if_insecure()

    # Fly.io terminates TLS at the edge and forwards over HTTP with
    # X-Forwarded-Proto: https. Without ProxyFix, Flask/Talisman think
    # every request is plain HTTP -- so HSTS never emits, url_for
    # generates http:// links, and secure-cookie flags are misapplied.
    # trust=1 hop of proxy (Fly's edge), no more.
    app.wsgi_app = ProxyFix(
        app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
    )

    login_manager.init_app(app)
    # CSRF protection: every state-changing POST must carry the token
    # rendered by {{ csrf_token() }}. Reads SECRET_KEY from Config.
    csrf.init_app(app)

    # Security headers via Talisman. force_https lets tests + local
    # dev hit http:// without being kicked to https://; production
    # rides Fly.io's edge which is HTTPS-terminated anyway, and HSTS
    # keeps browsers locked to HTTPS for a year regardless.
    talisman.init_app(
        app,
        force_https=False,               # trust the reverse proxy
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,   # 1 year
        strict_transport_security_include_subdomains=True,
        content_security_policy=_CSP,
        content_security_policy_nonce_in=[],
        referrer_policy="strict-origin-when-cross-origin",
        permissions_policy=_PERMISSIONS_POLICY,
        frame_options="DENY",
        session_cookie_secure=Config.SESSION_COOKIE_SECURE,
        session_cookie_http_only=Config.SESSION_COOKIE_HTTPONLY,
    )

    # Rate limiting. Global default applies to everything; per-route
    # tighter limits are declared with @limiter.limit(...) on the
    # affected view functions (see routes/auth.py, routes/account.py).
    limiter.init_app(app)

    # Session-fixation defense (regenerate on login), global logout
    # on password change, and idle-timeout enforcement.
    from security import install_session_guards
    install_session_guards(app)

    # ── Blueprints ──────────────────────────────────────────────
    from routes.auth      import bp as auth_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.account   import bp as account_bp
    from routes.inventory import bp as inventory_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(inventory_bp)

    # ── Root redirect ───────────────────────────────────────────
    @app.route("/")
    def _index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard.home"))
        return redirect(url_for("auth.login"))

    # ── Health check for Fly.io / load balancers ────────────────
    @app.route("/healthz")
    def _healthz():
        return {"ok": True, "app": Config.APP_NAME,
                "version": Config.APP_VERSION}, 200

    # ── First-launch admin bootstrap ─────────────────────────────
    #   The Fly.io volume starts empty on first deploy, so the users
    #   table has no rows and no one could log in. Detect that case
    #   and mint a random admin password, printing it to stdout so
    #   it shows up in `flyctl logs`. Idempotent: subsequent starts
    #   see the existing admin and do nothing.
    _bootstrap_default_admin()

    return app


def _bootstrap_default_admin() -> None:
    import secrets as _secrets
    from database import Database
    from auth import hash_password as _hp
    db = Database()
    try:
        if db.get_all_users():
            return  # Already bootstrapped.
    except Exception as exc:  # pragma: no cover - defensive
        print(f"[bootstrap] could not query users table: {exc}")
        return
    pw = _secrets.token_urlsafe(12)
    ph, salt = _hp(pw)
    ok, msg = db.create_user("admin", ph, salt, "admin")
    if ok:
        print("=" * 72)
        print("  HARVEST HERO -- FIRST-LAUNCH ADMIN CREATED")
        print("     username: admin")
        print(f"     password: {pw}")
        print("  Log in at your app URL and change this password immediately.")
        print("  This password will NEVER be shown again -- save it now.")
        print("=" * 72)
    else:
        # Race with a sibling worker: harmless, someone else already made it.
        print(f"[bootstrap] admin not created ({msg}); assuming another "
              f"worker beat us to it")


# WSGI entry point — used by gunicorn in production.
app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
