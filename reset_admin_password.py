#!/usr/bin/env python3
"""reset_admin_password.py — Reset admin password to admin123 for testing/recovery."""

import os
import sys
from database import Database
from auth import hash_password

def reset_admin_password():
    """Reset admin password to admin123."""
    try:
        db = Database()
        
        # Check if admin exists
        admin = db.get_user("admin")
        if not admin:
            print("❌ Admin user not found!")
            print("Creating new admin account...")
            pwd_hash, salt = hash_password("admin123")
            db.create_user("admin", pwd_hash, salt, "admin")
            print("✅ Admin account created with password: admin123")
            return
        
        # Reset password
        pwd_hash, salt = hash_password("admin123")
        db.update_user_password("admin", pwd_hash, salt)
        
        print("✅ Admin password reset successfully!")
        print("\nLogin credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\n⚠️  Change this password immediately after logging in!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🔐 Harvest Hero - Admin Password Reset")
    print("=" * 40)
    print()
    reset_admin_password()
