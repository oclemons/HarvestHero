"""Flask extension singletons.

Kept in their own module (no ``app.py`` import) so route modules can
grab them without pulling in the app factory and creating a circular
import. ``app.py`` calls ``.init_app(app)`` on each of them.
"""

from __future__ import annotations

from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect


login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Please sign in to continue."
login_manager.login_message_category = "info"


# CSRF protection is enabled globally in create_app(); every POST form
# must include {{ csrf_token() }}. Reads the same SECRET_KEY as the
# session cookie so tokens survive a worker restart just like sessions.
csrf = CSRFProtect()
