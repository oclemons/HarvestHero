"""
setup_db.py
-----------
Run this script once to initialise the SQLite database and create
the default admin account.

Usage:
    python setup_db.py
"""

from auth import hash_password
from database import Database


def main() -> None:
    print("Initialising Inventory Control Center database...")
    db = Database()

    users = db.get_all_users()
    if users:
        print(f"  Database already contains {len(users)} user(s). Skipping admin creation.")
    else:
        pwd_hash, salt = hash_password("admin123")
        ok, msg = db.create_user("admin", pwd_hash, salt, "admin")
        if ok:
            print("  Default admin account created:")
            print("    Username : admin")
            print("    Password : admin123")
            print()
            print("  *** IMPORTANT: Change this password after your first login! ***")
        else:
            print(f"  Could not create admin: {msg}")

    print()
    print("Database ready.  Run  python main.py  to start the application.")


if __name__ == "__main__":
    main()
