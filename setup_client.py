#!/usr/bin/env python3
"""
setup_client.py — Harvest Hero Client Setup Wizard

Run this ONCE on each client PC to point it at the server.
No JSON editing required — just answer two questions.

    python setup_client.py        (Mac / Linux)
    py setup_client.py            (Windows, if 'python' not found)
"""

import json
import os
import socket
import urllib.error
import urllib.request

try:
    from paths import USER_DIR
    CFG_PATH = os.path.join(USER_DIR, "config.json")
except Exception:
    # paths.py has side effects; fall back to script-local if it fails
    CFG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

BANNER = """
╔══════════════════════════════════════════════════╗
║        Harvest Hero — Client Setup Wizard        ║
╚══════════════════════════════════════════════════╝
"""

def _load_existing():
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _test_connection(url: str) -> bool:
    """Quick TCP reachability check (does not require requests library)."""
    try:
        host = url.split("//")[-1].split(":")[0]
        port_str = url.split(":")[-1].rstrip("/")
        port = int(port_str) if port_str.isdigit() else 5000
        sock = socket.create_connection((host, port), timeout=3)
        sock.close()
        return True
    except Exception:
        return False


def main():
    print(BANNER)

    existing = _load_existing()
    current_mode = existing.get("mode", "local")
    current_url  = existing.get("server_url", "")

    if current_mode == "client" and current_url:
        print(f"  Current config: client → {current_url}")
        keep = input("  Keep existing settings? [Y/n]: ").strip().lower()
        if keep in ("", "y", "yes"):
            print("\n  No changes made. Run run.bat / run.sh to start the app.")
            return

    print("  You need the IP address of the PC running the Harvest Hero server.")
    print()
    print("  How to find it:")
    print("    Mac / Linux : open Terminal → type  ifconfig  → look for 'inet'")
    print("    Windows     : open cmd → type  ipconfig  → look for 'IPv4 Address'")
    print()

    while True:
        ip = input("  Enter server IP address (e.g. 192.168.1.10): ").strip()
        if ip:
            break
        print("  IP address cannot be empty.")

    port_raw = input("  Enter server port [press Enter for 5000]: ").strip()
    port = port_raw if port_raw.isdigit() else "5000"

    url = f"http://{ip}:{port}"

    print()
    print("  The server prints TWO tokens. Use the STAFF token on a staff")
    print("  PC (scanning + transactions) and the ADMIN token on the")
    print("  admin PC (user management, add/edit/delete inventory, settings).")
    print()
    token = input("  Paste the token for this PC: ").strip()
    while not token:
        print("  API token cannot be empty.")
        token = input("  Paste the token for this PC: ").strip()

    print(f"\n  Testing connection to {url} ...")
    try:
        req = urllib.request.Request(
            f"{url}/api/health",
            headers={"Authorization": f"Bearer {token}"},
        )
        urllib.request.urlopen(req, timeout=5)
        print("  ✓ Server reachable and token accepted!")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            print("  ✗ Invalid API token. Check the token shown on the server.")
        else:
            print(f"  ✗ Server returned error {e.code}.")
        proceed = input("\n  Save anyway? [y/N]: ").strip().lower()
        if proceed not in ("y", "yes"):
            print("\n  Cancelled. No changes saved.")
            return
    except Exception:
        print("  ✗ Could not reach the server.")
        print("    Make sure server.py is running on the host PC and")
        print("    both computers are on the same Wi-Fi / network.")
        proceed = input("\n  Save anyway? [y/N]: ").strip().lower()
        if proceed not in ("y", "yes"):
            print("\n  Cancelled. No changes saved.")
            return

    cfg = {"mode": "client", "server_url": url, "api_key": token}
    with open(CFG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    # Lock it — this file now holds the API token.
    try:
        os.chmod(CFG_PATH, 0o600)
    except OSError:
        pass

    print(f"\n  ✓ Saved! config.json now points to: {url}")
    print()
    print("  Next step: run the app with")
    print("    Mac / Linux : ./run.sh")
    print("    Windows     : double-click run.bat")
    print()


if __name__ == "__main__":
    main()
