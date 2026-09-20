"""Flask extension singletons.

Kept in their own module (no ``app.py`` import) so route modules can
grab them without pulling in the app factory and creating a circular
import. ``app.py`` calls ``.init_app(app)`` on each of them.
"""

from __future__ import annotations

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect


login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"


# CSRF protection is enabled globally in create_app(); every POST form
# must include {{ csrf_token() }}. Reads the same SECRET_KEY as the
# session cookie so tokens survive a worker restart just like sessions.
csrf = CSRFProtect()


# Security-headers middleware. Configuration lives in app.py because
# the CSP allowlist depends on which CDNs the templates load. We keep
# the object here so extensions.py stays the single source of truth.
talisman = Talisman()


# Rate limiter. Default per-IP; login route additionally throttles per
# username so a shared NAT'd office IP doesn't lock everyone out when
# one person fat-fingers their password ten times.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per minute"],
    storage_uri="memory://",   # single-process Fly.io app; fine.
    headers_enabled=True,      # emit RateLimit-* response headers
)
