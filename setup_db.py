"""
setup_db.py
-----------
Run this script once to initialise the SQLite database and create
the default admin account.

Usage:
    python setup_db.py
"""

import secrets

from auth import hash_password
from database import Database


def main() -> None:
    print("Initialising Inventory Control Center database...")
    db = Database()

    users = db.get_all_users()
    if users:
        print(f"  Database already contains {len(users)} user(s). Skipping admin creation.")
    else:
        # Generate a random per-install admin password. The old default
        # ("admin123") was a well-known credential that shipped with the
        # code and gave any attacker who could reach the app instant
        # admin access.
        random_pwd = secrets.token_urlsafe(12)
        pwd_hash, salt = hash_password(random_pwd)
        ok, msg = db.create_user("admin", pwd_hash, salt, "admin")
        if ok:
            print("  Default admin account created:")
            print("    Username : admin")
            print(f"    Password : {random_pwd}")
            print()
            print("  *** IMPORTANT: Log in and change this password now. It is")
            print("      shown only once and is not stored in plaintext. ***")
        else:
            print(f"  Could not create admin: {msg}")

    print()
    print("Database ready.  Run  python main.py  to start the application.")


if __name__ == "__main__":
    main()
