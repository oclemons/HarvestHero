"""ldap_auth.py — LDAP / Active Directory authentication integration.

Config is stored in config.json under the "ldap" key:
{
  "ldap": {
    "enabled":          true,
    "server_url":       "ldap://192.168.1.100",
    "port":             389,
    "use_ssl":          false,
    "use_tls":          false,
    "dn_format":        "{username}@company.com",
    "base_dn":          "DC=company,DC=com",
    "search_attr":      "sAMAccountName",
    "service_dn":       "",
    "service_password": "",
    "fallback_to_local": true
  }
}

dn_format examples:
  "{username}@company.com"             — UPN style (most common for AD)
  "{username}@DOMAIN"                  — NetBIOS domain
  "uid={username},ou=users,dc=co,dc=com" — OpenLDAP / POSIX
  "CN={username},OU=Users,DC=co,DC=com"  — full AD DN
"""

import json
import os
from typing import Optional, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_CFG  = os.path.join(_HERE, "config.json")


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def get_ldap_config() -> dict:
    """Load the 'ldap' block from config.json."""
    try:
        with open(_CFG) as f:
            return json.load(f).get("ldap", {})
    except Exception:
        return {}


def save_ldap_config(ldap_cfg: dict) -> None:
    """Persist the LDAP config block to config.json."""
    try:
        cfg: dict = {}
        if os.path.exists(_CFG):
            with open(_CFG) as f:
                cfg = json.load(f)
        cfg["ldap"] = ldap_cfg
        with open(_CFG, "w") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass


def is_ldap_enabled() -> bool:
    return bool(get_ldap_config().get("enabled", False))


# ---------------------------------------------------------------------------
# Connection test
# ---------------------------------------------------------------------------

def test_ldap_connection(config: dict) -> Tuple[bool, str]:
    """Verify connectivity using service account or anonymous bind.

    Returns:
        (success: bool, message: str)
    """
    try:
        from ldap3 import Server, Connection, Tls, SIMPLE  # noqa
        import ssl

        server_url   = (config.get("server_url") or "").strip()
        port         = int(config.get("port") or 389)
        use_ssl      = bool(config.get("use_ssl", False))
        use_tls      = bool(config.get("use_tls", False))
        service_dn   = (config.get("service_dn") or "").strip()
        service_pass = config.get("service_password") or ""

        if not server_url:
            return False, "Server URL is required."

        tls    = Tls(validate=ssl.CERT_NONE) if (use_ssl or use_tls) else None
        server = Server(server_url, port=port, use_ssl=use_ssl, tls=tls,
                        connect_timeout=6)

        if service_dn and service_pass:
            conn = Connection(server, user=service_dn, password=service_pass,
                              authentication=SIMPLE, raise_exceptions=False)
        else:
            conn = Connection(server, raise_exceptions=False)

        if use_tls and not use_ssl:
            conn.open()
            conn.start_tls()

        result = conn.bind()
        conn.unbind()

        if result:
            return True, "Connection successful — LDAP server is reachable."
        desc = (conn.result or {}).get("description", "Bind failed")
        return False, f"Bind failed: {desc}"

    except ImportError:
        return False, "ldap3 library not installed. Run:  pip install ldap3"
    except Exception as exc:
        return False, f"Connection error: {exc}"


# ---------------------------------------------------------------------------
# User authentication
# ---------------------------------------------------------------------------

def verify_ldap_credentials(
    username: str,
    password:  str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """Authenticate username + password against the configured LDAP server.

    Returns:
        (success, display_name_or_None, error_message_or_None)
    """
    config = get_ldap_config()

    if not config.get("enabled"):
        return False, None, "LDAP not enabled."

    if not password:
        return False, None, "Password required."

    try:
        from ldap3 import Server, Connection, Tls, SIMPLE, SUBTREE  # noqa
        import ssl

        server_url  = (config.get("server_url") or "").strip()
        port        = int(config.get("port") or 389)
        use_ssl     = bool(config.get("use_ssl", False))
        use_tls     = bool(config.get("use_tls", False))
        dn_format   = (config.get("dn_format") or "{username}").strip()
        base_dn     = (config.get("base_dn") or "").strip()
        search_attr = (config.get("search_attr") or "sAMAccountName").strip()

        if not server_url:
            return False, None, "LDAP server URL not configured."

        user_dn = dn_format.replace("{username}", username)
        tls     = Tls(validate=ssl.CERT_NONE) if (use_ssl or use_tls) else None
        server  = Server(server_url, port=port, use_ssl=use_ssl, tls=tls,
                         connect_timeout=8)
        conn    = Connection(server, user=user_dn, password=password,
                             authentication=SIMPLE, raise_exceptions=False)

        if use_tls and not use_ssl:
            conn.open()
            conn.start_tls()

        if not conn.bind():
            desc = (conn.result or {}).get("description", "Invalid credentials")
            conn.unbind()
            return False, None, desc

        # Attempt to retrieve display name via search
        display_name: Optional[str] = None
        if base_dn:
            try:
                conn.search(
                    search_base=base_dn,
                    search_filter=f"({search_attr}={username})",
                    search_scope=SUBTREE,
                    attributes=["displayName", "cn", "givenName", "sn"],
                )
                if conn.entries:
                    entry = conn.entries[0]
                    for attr in ("displayName", "cn"):
                        val = getattr(entry, attr, None)
                        if val and str(val) not in ("[]", ""):
                            display_name = str(val)
                            break
            except Exception:
                pass

        conn.unbind()
        return True, display_name, None

    except ImportError:
        return False, None, "ldap3 library not installed. Run:  pip install ldap3"
    except Exception as exc:
        return False, None, f"LDAP error: {exc}"
