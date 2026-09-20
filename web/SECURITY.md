# HarvestHero web app — security posture

This document describes the security controls in place on the
production web app at **https://harvestheropantry.com**, how each
one is verified, and what still needs work.

## Threat model at a glance

HarvestHero is a small-population college-food-pantry app. The most
likely threats and how we defend against each are:

| Threat | Impact | Primary defense |
|---|---|---|
| Credential stuffing / brute force on login | Full account takeover | PBKDF2 password hashing (600k iterations) + Flask-Limiter rate cap (10 attempts / 5 min per IP) + LDAP (Phase 2C) |
| Session hijack (fixation / theft) | Full account takeover | Session cookie is `HttpOnly` + `Secure` + `SameSite=Lax`; session ID regenerated on every login (2A.4); password change kicks other sessions |
| CSRF on write routes | Silent data modification via forged form | Flask-WTF CSRF token on every POST form (2A.1) |
| XSS via inventory / user input | Session cookie theft, arbitrary JS | Jinja auto-escaping (default) + strict CSP (2A.2) with `frame-ancestors 'none'` |
| SQL injection | Full DB read/write | Every query uses `sqlite3` parameterized queries (`?` placeholders); grep-audit runs in CI |
| Broken access control (student → admin) | PII exposure, inventory tampering | Server-side `@admin_required` decorator (Phase 2B); every admin route has a raw-HTTP RBAC test |
| Traceback / stack leak on error | System info to attacker | `errors.py` renders a generic template; 500 handler logs traceback server-side only (2A.5) |
| Rate-limit bypass via forged headers | Brute force | Rate limiter keys on `X-Forwarded-For` only because `ProxyFix(x_for=1)` trusts exactly one hop of proxy (Fly's edge) |
| Hard-coded credential in source | Instant compromise | `web/tools/check_secrets.py` scans tracked files in CI (2A.6/7); no secrets committed |
| Vulnerable dependency | RCE / data leak via lib | `pip-audit --strict` in CI (2A.6); failing scan blocks deploy |

## Controls in place (as of v3.1.0)

### Transport
* **HTTPS terminated at Fly.io edge.** All prod traffic is HTTPS.
* **HSTS** header (`max-age=31536000; includeSubDomains`) so browsers
  refuse to hit the HTTP variant even if the user typed `http://`.
* **ProxyFix** trusts one hop of proxy (Fly's edge) so `url_for`,
  cookie flags, and rate-limit keys use the client's real IP and
  scheme (`X-Forwarded-For`, `X-Forwarded-Proto`).

### Session
* Cookie flags: `Secure`, `HttpOnly`, `SameSite=Lax`.
* Absolute lifetime: 12 hours.
* Idle timeout: 30 min. Enforced by `web/security.py:install_session_guards`.
* Session ID regenerated on login (fixation defense).
* Every session stores a prefix of the current password hash. When a
  password changes, all other sessions holding the old prefix are
  logged out on their next request.

### Authentication
* **Local password**: PBKDF2-HMAC-SHA256, 600k iterations, per-user
  salt. Legacy 100k records are re-hashed automatically on successful
  login (see `auth.py`).
* Password strength: at least 8 characters and at least 3 of the 4
  character classes (lowercase, uppercase, digit, symbol). Enforced
  on change-password.
* **LDAP**: not yet wired into the web app. `ldap_auth.py` exists
  and is used by the frozen desktop; Phase 2C will wire it in.
* Rate limit: 10 attempts per 5 minutes per IP on `POST /login`;
  20 attempts per 15 minutes on `POST /account/password`; global
  default 200 req/min.

### Authorization
* Every write route is `@login_required`.
* Role split into admin/student lands in Phase 2B; `@admin_required`
  decorator + raw-HTTP RBAC tests will enforce server-side.
* Note: currently every authenticated user can add/edit/delete
  inventory. This is deliberate for v3.0/3.1 (single-admin pilot).

### CSRF
* Flask-WTF `CSRFProtect` enabled globally.
* Every POST form renders `{{ csrf_token() }}`; missing/forged →
  400 with a friendly page (never leaks server internals).

### Headers
Emitted by Flask-Talisman on every response:

* `Content-Security-Policy` — see full policy in `web/app.py:_CSP`.
  Allowlist: `'self'` + `cdn.tailwindcss.com` + `unpkg.com` for
  scripts. Every other external host is blocked.
* `X-Frame-Options: DENY`
* `X-Content-Type-Options: nosniff`
* `Referrer-Policy: strict-origin-when-cross-origin`
* `Permissions-Policy` denies geolocation, mic, camera, payment,
  USB, gyroscope, magnetometer.
* `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  (secure requests only)

Verified by `web/tests/test_security_headers.py` on every push.

### Error handling
* Custom 400/403/404/405/429/500 handlers in `web/errors.py`.
* 500 renders a generic template; the exception + traceback go to
  the JSON log only. Test `tests/test_errors.py` asserts a
  forbidden-strings list ("Traceback", exception message, source
  path) never appears in the response body.

### Logging
* `web/logging_config.py` emits one JSON line per request:
  `{ts, level, logger, event, method, path, status, duration_ms,
   user, remote_addr, request_id}`.
* `/healthz` is not logged (probe noise).
* Cookies, `Authorization`, request bodies, and query strings are
  **never** written to the log. Test proves it: `tests/test_logging.py`.

### Secrets management
* No secret is committed to source. Enforced by
  `web/tools/check_secrets.py` in CI.
* Session key, LDAP service password, OpenAI key, Fly deploy token
  all live in Fly.io secrets or GitHub Action secrets.
* On the developer machine, the LDAP service password is stored
  encrypted with `secrets_vault.py` (Fernet), not plaintext.

### Dependency hygiene
* `web/requirements.txt` is pinned to upper bounds so no unreviewed
  major-version bumps slip in.
* `pip-audit --strict` runs on every push (`.github/workflows/fly-deploy.yml`).
  A CVE finding blocks deploy.

### Backup (partial, full story lands in Phase 2N)
* Fly.io volume snapshots are enabled (default). Retention =
  Fly's default (5 daily) until Phase 2N adds off-Fly encrypted
  copies to R2.

## OWASP Top 10 (2021) coverage matrix

| # | Category | Status | Where it's addressed |
|---|---|---|---|
| **A01** | Broken Access Control | 🟡 partial | Every route `@login_required`. Role split + `@admin_required` lands in Phase 2B; raw-HTTP RBAC tests come with it. |
| **A02** | Cryptographic Failures | 🟢 ok | HTTPS + HSTS; PBKDF2-HMAC-SHA256 (600k) for passwords; Fernet for stored secrets; session cookies signed with `SECRET_KEY`. |
| **A03** | Injection | 🟢 ok | 100% parameterized SQL queries in `database.py`. Jinja auto-escaping on every rendered variable. Grep audit for `execute(f"...")` runs in CI. |
| **A04** | Insecure Design | 🟡 partial | Threat model above. Full architecture review + STRIDE-style analysis scheduled for Phase 2O sign-off. |
| **A05** | Security Misconfiguration | 🟢 ok | Talisman headers + Flask debug forced off in production + generic error pages + secure cookie flags. |
| **A06** | Vulnerable Components | 🟢 ok | `pip-audit --strict` in CI blocks any known-CVE dependency. Requirements pinned. |
| **A07** | Identification and Authentication Failures | 🟢 ok | PBKDF2 + rate limit + session fixation defense + idle timeout + password-change invalidates concurrent sessions. |
| **A08** | Software and Data Integrity | 🟡 partial | Dependency scan (see A06); no supply-chain provenance yet (SLSA/sigstore out of scope for pilot). |
| **A09** | Security Logging and Monitoring Failures | 🟡 partial | Structured JSON request log (`logging_config.py`). Rich audit log with before/after values lands in Phase 2I. Alerting via Fly.io only for now. |
| **A10** | SSRF | 🟢 ok | No user-controlled URLs are fetched by the server today. When AI (Phase 2L) or webhooks are added, we allowlist explicitly. |

🟢 = fully covered in v3.1.0 &nbsp;&nbsp; 🟡 = partially covered; remainder scheduled &nbsp;&nbsp; 🔴 = not covered

## What's still open

Tracked in `/Users/octayviaclemons/.devin/plans/plan-8429f1f9fb7f924d.md`
under the numbered phase items. The security-relevant open items:

| Phase | What lands |
|---|---|
| 2A.12 | Verify Fly.io volume snapshot retention (currently Fly default) |
| 2A.13 | Set `FLY_API_TOKEN` GitHub secret so CI can auto-deploy |
| 2A.14 | Confirm bootstrap admin password is rotated |
| 2B | Server-side RBAC decorator + role split + raw-HTTP RBAC tests (A01) |
| 2C | LDAP as primary auth (A07 stronger) |
| 2I | Audit log with before/after values (A09 stronger) |
| 2N | Off-Fly encrypted backups + tested restore drill |
| 2O | Formal security-testing sweep (SQLi/XSS/session/URL/header fuzz) before v4.0.0 sign-off |

## Rotating secrets

**Session `SECRET_KEY`** (invalidates every existing session):
```bash
flyctl secrets set \
    HARVESTHERO_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')" \
    --app harvest-hero-pantry
```

**Fly deploy token** (GitHub Actions):
```bash
flyctl tokens revoke <old-token-id>   # find via `flyctl tokens list`
flyctl tokens create deploy --name "github-actions" --app harvest-hero-pantry
# Paste new token into GitHub Settings > Secrets > FLY_API_TOKEN
```

**Local admin password**: `/account/settings` → Change password. Or,
worst case, run `flyctl ssh console` → `python3 -c "from database
import Database; from auth import hash_password; db = Database();
ph, salt = hash_password('NEW_PW'); db.update_user_password(1, ph,
salt)"`.

**LDAP service password** (Phase 2C): `flyctl secrets set
LDAP_SERVICE_PASSWORD=... --app harvest-hero-pantry`.

**OpenAI API key** (Phase 2L): `flyctl secrets set OPENAI_API_KEY=...
--app harvest-hero-pantry`.

## Contact / disclosure

Security issues: open a private GitHub Security Advisory on the
`oclemons/HarvestHero` repository (**not** a public issue). The
maintainer will acknowledge within one business day.
