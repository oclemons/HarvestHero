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

from config import Config
from extensions import login_manager


def create_app(config: type = Config) -> Flask:
    """Build a configured Flask app."""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config)
    config.warn_if_insecure()

    login_manager.init_app(app)

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
