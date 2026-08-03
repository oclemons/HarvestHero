"""environment.py — License validation and environment locking."""

import hashlib
import json
import os
import socket
import uuid
import datetime
from typing import Tuple

_DIR = os.path.dirname(os.path.abspath(__file__))
LICENSE_PATH = os.path.join(_DIR, "license.json")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _machine_id() -> str:
    """Stable machine identifier (MAC address + hostname)."""
    mac  = uuid.getnode()
    host = socket.gethostname()
    raw  = f"{mac}:{host}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _sign(data: dict, secret: str = "ICC_INTERNAL_SALT_2024") -> str:
    payload = json.dumps(data, sort_keys=True)
    return hashlib.sha256((payload + secret).encode()).hexdigest()


# ---------------------------------------------------------------------------
# License generation (called once on the server to create license.json)
# ---------------------------------------------------------------------------

def generate_license(
    org_name: str,
    env_id:   str,
    expiry:   str = "",          # ISO date string, blank = never
    allowed_clients: list = None,
) -> dict:
    data = {
        "org_name":        org_name,
        "environment_id":  env_id,
        "host_machine_id": _machine_id(),
        "created_at":      datetime.datetime.now().isoformat(),
        "expiry":          expiry,
        "allowed_clients": allowed_clients or [],
    }
    data["signature"] = _sign(data)
    return data


def write_license(
    org_name: str,
    env_id:   str,
    expiry:   str = "",
) -> dict:
    lic = generate_license(org_name, env_id, expiry)
    with open(LICENSE_PATH, "w") as f:
        json.dump(lic, f, indent=2)
    return lic


# ---------------------------------------------------------------------------
# License reading and validation
# ---------------------------------------------------------------------------

def load_license() -> dict | None:
    if not os.path.exists(LICENSE_PATH):
        return None
    try:
        with open(LICENSE_PATH) as f:
            return json.load(f)
    except Exception:
        return None


def validate_license() -> Tuple[bool, str]:
    """
    Returns (ok, message).
    - ok=True  → license is valid, app may run
    - ok=False → app should block with the message
    """
    lic = load_license()

    # Host-mode: no license file → create a default one so the app can run
    if lic is None:
        _auto_create_license()
        return True, "License created (first-run)."

    # Signature check
    sig = lic.pop("signature", "")
    expected = _sign(lic)
    lic["signature"] = sig
    if sig != expected:
        return False, "License file has been tampered with."

    # Expiry check
    expiry = lic.get("expiry", "")
    if expiry:
        try:
            exp_date = datetime.date.fromisoformat(expiry)
            if datetime.date.today() > exp_date:
                return False, f"License expired on {expiry}."
        except ValueError:
            pass

    return True, "OK"


def _auto_create_license():
    """Create a default license for first-run host installations."""
    write_license(
        org_name="Inventory Control Center",
        env_id=str(uuid.uuid4())[:8].upper(),
    )


# ---------------------------------------------------------------------------
# Client registration
# ---------------------------------------------------------------------------

def get_client_info() -> dict:
    return {
        "machine_id": _machine_id(),
        "hostname":   socket.gethostname(),
        "ip":         _local_ip(),
    }


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def is_lan_ip(ip: str) -> bool:
    import ipaddress
    try:
        addr = ipaddress.ip_address(ip)
        return (
            addr.is_private or
            addr.is_loopback or
            addr.is_link_local
        )
    except ValueError:
        return False
