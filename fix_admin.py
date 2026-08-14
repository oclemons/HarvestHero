#!/usr/bin/env python3
"""fix_admin.py — Fix admin account issues by recreating the database."""

import os
import sys
import shutil
from database import Database
from auth import hash_password

def fix_admin():
    """Fix admin account by recreating database if needed."""
    try:
        print("🔧 Harvest Hero - Admin Account Fix")
        print("=" * 50)
        print()
        
        # Path to database
        db_path = os.path.join("data", "inventory.db")
        
        # Backup existing database
        if os.path.exists(db_path):
            backup_path = db_path + ".backup"
            print(f"📦 Backing up existing database to {backup_path}...")
            shutil.copy(db_path, backup_path)
            print(f"✅ Backup created")
            print()
        
        # Delete the database to force recreation
        if os.path.exists(db_path):
            print(f"🗑️  Deleting existing database...")
            os.remove(db_path)
            print(f"✅ Database deleted")
            print()
        
        # Create new database
        print("📝 Creating new database...")
        db = Database()
        print("✅ Database created")
        print()
        
        # Check if admin exists
        print("👤 Checking for admin account...")
        admin = db.get_user("admin")
        
        if admin:
            print("⚠️  Admin account already exists")
            print(f"   Username: {admin['username']}")
            print(f"   Role: {admin['role']}")
        else:
            print("❌ Admin account not found, creating...")
            pwd_hash, salt = hash_password("admin123")
            db.create_user("admin", pwd_hash, salt, "admin")
            print("✅ Admin account created")
        
        print()
        print("=" * 50)
        print("✅ Setup complete!")
        print()
        print("Login credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print()
        print("⚠️  Change this password immediately after logging in!")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    fix_admin()
