"""JSON logging setup.

Every request emits one structured line on completion with:
  time, level, event, method, path, status, duration_ms,
  user, remote_addr, request_id

Sensitive fields (Authorization, Cookie, csrf_token, password) are
never logged. The request body isn't logged at all.

fly.io captures stdout so ``flyctl logs`` shows the JSON stream
directly; ship-to-logging tools can parse it without extra work.
"""

from __future__ import annotations

import json
import logging
import sys
import time
import uuid

from flask import g, request
from flask_login import current_user


_REQ_LOG = logging.getLogger("harvesthero.request")


class _JsonFormatter(logging.Formatter):
    """Formatter that emits one JSON object per record.

    Standard record attributes (name, level, msg, exc_info) are
    included; anything the caller passed via ``extra=`` is merged
    in at the top level. Never crashes on bad extras -- unknown
    types become their repr().
    """

    _STANDARD_ATTRS = {
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "exc_info", "exc_text", "stack_info",
        "lineno", "funcName", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process",
        "message", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":     time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level":  record.levelname,
            "logger": record.name,
            "msg":    record.getMessage(),
        }
        # Anything the caller passed via extra={...}
        for k, v in record.__dict__.items():
            if k in self._STANDARD_ATTRS:
                continue
            try:
                json.dumps(v)
                payload[k] = v
            except TypeError:
                payload[k] = repr(v)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def install_logging(app) -> None:
    """Configure root logging to emit JSON and register a
    per-request access log."""

    # Reset any handlers gunicorn / Flask added so we control the
    # format completely.
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(_JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)

    # Flask logs to `flask.app`; the request logger is separate so
    # ops can filter by name.
    _REQ_LOG.setLevel(logging.INFO)

    @app.before_request
    def _stamp():
        g._start_ts   = time.perf_counter()
        g._request_id = uuid.uuid4().hex[:12]

    @app.after_request
    def _log_response(response):
        try:
            dur_ms = int((time.perf_counter() - g._start_ts) * 1000)
        except Exception:
            dur_ms = -1

        # Skip /healthz spam -- Fly.io probes this every 15s.
        if request.path == "/healthz":
            return response

        _REQ_LOG.info(
            "request",
            extra={
                "event":       "request",
                "method":      request.method,
                "path":        request.path,
                "status":      response.status_code,
                "duration_ms": dur_ms,
                "user":        (current_user.username
                                if current_user.is_authenticated
                                else None),
                "remote_addr": request.headers.get(
                    "X-Forwarded-For", request.remote_addr
                ),
                "request_id":  getattr(g, "_request_id", ""),
                # Explicitly NOT logged: headers (Cookie, Authorization),
                # form body (may contain passwords or CSRF tokens),
                # query string (may contain tokens).
            },
        )
        return response
