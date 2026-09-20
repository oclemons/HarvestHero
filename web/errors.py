"""HTTP error handlers.

Every error path renders a small, consistent page and returns the
appropriate status code. The 500 handler is the important one: it
logs the full traceback server-side (visible via ``flyctl logs``)
but the response body is a generic message so a hostile client
never sees stack frames, file paths, or SQL text.

Register from ``create_app`` via ``install_error_handlers(app)``.
"""

from __future__ import annotations

import logging

from flask import render_template, request
from flask_wtf.csrf import CSRFError


_log = logging.getLogger("harvesthero.errors")


def install_error_handlers(app) -> None:

    # ── 400 Bad Request / CSRF failure ─────────────────────────
    @app.errorhandler(400)
    @app.errorhandler(CSRFError)
    def _400(e):
        reason = _short_reason(e, default="Bad request.")
        _log.info("400 %s %s: %s", request.method, request.path, reason)
        return render_template("errors/generic.html",
                               code=400, title="Bad request",
                               message=reason), 400

    # ── 403 Forbidden ──────────────────────────────────────────
    @app.errorhandler(403)
    def _403(e):
        _log.info("403 %s %s", request.method, request.path)
        return render_template("errors/generic.html",
                               code=403, title="Forbidden",
                               message="You don't have access to this page."
                               ), 403

    # ── 404 Not Found ──────────────────────────────────────────
    @app.errorhandler(404)
    def _404(e):
        # Info-level: 404s are noisy but useful for scanning attempts
        _log.info("404 %s %s", request.method, request.path)
        return render_template("errors/generic.html",
                               code=404, title="Page not found",
                               message="The page you asked for isn't here."
                               ), 404

    # ── 405 Method Not Allowed ─────────────────────────────────
    @app.errorhandler(405)
    def _405(e):
        _log.info("405 %s %s", request.method, request.path)
        return render_template("errors/generic.html",
                               code=405, title="Method not allowed",
                               message="That action isn't allowed on this URL."
                               ), 405

    # ── 429 Too Many Requests (from Flask-Limiter) ─────────────
    @app.errorhandler(429)
    def _429(e):
        reason = _short_reason(e,
                               default="Too many requests. Try again shortly.")
        _log.warning("429 %s %s from %s",
                     request.method, request.path,
                     request.headers.get("X-Forwarded-For",
                                         request.remote_addr))
        return render_template("errors/generic.html",
                               code=429, title="Slow down",
                               message=reason), 429

    # ── 500 Server Error ───────────────────────────────────────
    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def _500(e):
        # exc_info=True writes the traceback to the log.
        _log.exception("500 %s %s: unhandled exception",
                       request.method, request.path)
        # The client sees NOTHING about the exception -- no type,
        # no message, no traceback, no file paths, no SQL text.
        return render_template(
            "errors/generic.html",
            code=500, title="Something went wrong",
            message="An unexpected error occurred. The team has been "
                    "notified via server logs. Please try again.",
        ), 500


def _short_reason(exception, *, default: str) -> str:
    """Extract a short user-safe description from a werkzeug HTTPException
    or Flask-WTF CSRFError. Falls back to `default` for anything else."""
    try:
        # werkzeug HTTPExceptions have .description; CSRFError inherits.
        desc = getattr(exception, "description", None)
        if desc and isinstance(desc, str):
            return desc
    except Exception:
        pass
    return default
