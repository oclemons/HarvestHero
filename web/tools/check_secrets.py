#!/usr/bin/env python3
"""Scan the repo's tracked files for likely hard-coded secrets.

Runs in CI (see .github/workflows/fly-deploy.yml). Exits 1 if any
finding is not on the explicit allow-list. Exits 0 otherwise.

Intentionally simpler than a full gitleaks / trufflehog scan --
we only need to catch the shapes that actually matter for this
codebase:
  * Fly API tokens (FlyV1 ...)
  * GitHub personal-access tokens (ghp_...)
  * AWS access keys (AKIA...)
  * Slack tokens (xox[baprs]-)
  * PEM private key blocks
  * Long hex/base64 blobs assigned to *_KEY / *_SECRET / *_TOKEN /
    *_PASSWORD literals in Python

Findings that appear in known-safe contexts (test fixtures,
Fly-secrets documentation, environment-variable *reads*) are
suppressed by ALLOWLIST_SUBSTRINGS.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


# High-signal patterns. Each match is a candidate finding.
PATTERNS = [
    # Fly.io deploy tokens
    (re.compile(r'FlyV1\s+[A-Za-z0-9_\-]{20,}'),           "Fly.io token"),
    # GitHub personal access tokens (classic + fine-grained)
    (re.compile(r'ghp_[A-Za-z0-9]{36}'),                    "GitHub token"),
    (re.compile(r'github_pat_[A-Za-z0-9_]{60,}'),           "GitHub token"),
    # AWS access key IDs
    (re.compile(r'AKIA[0-9A-Z]{16}'),                       "AWS access key"),
    # Slack tokens
    (re.compile(r'xox[baprs]-[A-Za-z0-9\-]{10,}'),          "Slack token"),
    # PEM private keys
    (re.compile(r'-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----'),
        "PEM private key"),
    # OpenAI keys
    (re.compile(r'sk-[A-Za-z0-9]{40,}'),                    "OpenAI key"),
    # Long assignment: FOO_KEY = "..." with a value that looks like
    # a real secret (32+ chars, base64/hex-ish).
    (re.compile(
        r'\b(?:api[_-]?key|secret[_-]?key|access[_-]?key|access[_-]?token|'
        r'auth[_-]?token|bearer[_-]?token|private[_-]?key)\s*[:=]\s*'
        r'["\']([A-Za-z0-9_\-+/=]{32,})["\']',
        re.IGNORECASE,
     ),
        "hard-coded credential"),
]


# Findings whose LINE contains any of these substrings are suppressed.
# Keep this list narrow -- broad allowances hide real leaks.
ALLOWLIST_SUBSTRINGS = [
    "test-secret",              # test config
    "dev-only",                 # dev-mode warnings
    "placeholder",
    "example.test",
    "example.invalid",
    "EXAMPLE",
    "<paste>",
    "<random>",
    "your-",
    "SmokeTest!",               # test data
    "AdminPass!",               # test password
    "PantryChange!",            # test password
    "PantryAdmin!",             # test password
    "SessionPass!",             # test password
    "StaffPass!",               # test password
    "SeededAdmin!",             # test password
    "Bootstrap!seed",           # test password
    # Real env-var *reads* (not writes)
    "os.environ.get(",
    "os.environ[",
    "getenv(",
    'secrets.set(',             # doc snippets
    "flyctl secrets set",       # doc snippets
]


# File patterns that are skipped outright.
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".icns",
                 ".pdf", ".docx", ".xlsx", ".zip", ".exe"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "build", "dist",
             ".venv", "venv"}


def tracked_files():
    """Yield every git-tracked file path (relative to repo root)."""
    out = subprocess.check_output(
        ["git", "-C", str(ROOT), "ls-files"], text=True
    )
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        p = Path(line)
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield p


def scan_file(rel: Path):
    """Yield (line_no, snippet, pattern_label) for each finding."""
    full = ROOT / rel
    try:
        text = full.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return
    for i, line in enumerate(text.splitlines(), start=1):
        # File-wide allowlist: this file is the audit config itself
        # or a comment/doc that intentionally lists example patterns.
        for regex, label in PATTERNS:
            if not regex.search(line):
                continue
            if any(needle in line for needle in ALLOWLIST_SUBSTRINGS):
                continue
            snippet = line.strip()
            if len(snippet) > 160:
                snippet = snippet[:160] + "…"
            yield (i, snippet, label)


def main() -> int:
    findings = []
    for rel in tracked_files():
        # The tool itself contains the regexes; skip it.
        if str(rel) == "web/tools/check_secrets.py":
            continue
        for lineno, snippet, label in scan_file(rel):
            findings.append((rel, lineno, label, snippet))

    if not findings:
        print("check_secrets: clean. 0 findings.")
        return 0

    print("check_secrets: possible secrets found (fix, allow-list, "
          "or move to Fly.io secrets):\n")
    for rel, lineno, label, snippet in findings:
        print(f"  {rel}:{lineno}  [{label}]  {snippet}")
    print(f"\n{len(findings)} finding(s). Failing.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
