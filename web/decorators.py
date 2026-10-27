"""Role-based access control decorators.

Server-side enforcement of the RBAC rules from the Phase 2 spec:

  - admin       full pantry management, user administration, config,
                reporting, audit, backups, inventory adjustments,
                both scan-in and scan-out
  - student     scan-in only (donations/intake); read-only access
                to the information required to perform that task

Locked scan-in rule (from planning Q1):
  Students can scan IN. Only admins can scan OUT.
  ``@student_or_admin_required`` covers scan-in;
  ``@staff_or_admin_required``   covers scan-out, pantry, shopping list;
  ``@admin_required``            covers donations, activity, reports,
                                 user management, and other admin-only
                                 write routes.

Rules of use:

  * Always follow ``@login_required`` in the decorator stack. If the
    user isn't logged in at all, we want the login redirect from
    Flask-Login, not a bare 403 from here.
  * Never rely on hiding a button in the template. Every write route
    must carry the decorator.
"""

from __future__ import annotations

from functools import wraps

from flask import abort
from flask_login import current_user


def admin_required(fn):
    """Reject anyone whose role is not exactly 'admin' with a 403."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            # login_required should be layered above this; fall
            # through to abort so we don't silently allow the request.
            abort(403)
        if not getattr(current_user, "is_admin", False):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def staff_or_admin_required(fn):
    """Reject anyone who isn't admin or staff with a 403.

    Staff can access scan-out, pantry layout, shopping list, and other
    operational pages that require more than read-only access but are
    not admin-only features like donations, reports, or user management.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        role = getattr(current_user, "role", None)
        if role not in ("admin", "staff"):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper


def student_or_admin_required(fn):
    """Reject anyone who isn't admin, staff, or student with a 403."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            abort(403)
        role = getattr(current_user, "role", None)
        if role not in ("admin", "staff", "student"):
            abort(403)
        return fn(*args, **kwargs)
    return wrapper
