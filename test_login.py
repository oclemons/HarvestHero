#!/usr/bin/env python3
"""test_login.py — Test if admin account exists and password works."""

import sys
from database import Database
from auth import verify_password

def test_login():
    """Test admin login."""
    try:
        print("🔍 Testing Admin Login")
        print("=" * 50)
        print()
        
        # Connect to database
        db = Database()
        print("✅ Database connected")
        print()
        
        # Get all users
        users = db.get_all_users()
        print(f"📊 Total users in database: {len(users)}")
        print()
        
        if not users:
            print("❌ No users found in database!")
            print("   The database is empty.")
            return False
        
        # List all users
        print("👥 Users in database:")
        for user in users:
            print(f"   - {user['username']} ({user['role']})")
        print()
        
        # Try to get admin
        admin = db.get_user("admin")
        if not admin:
            print("❌ Admin user not found!")
            return False
        
        print("✅ Admin user found")
        print(f"   Username: {admin['username']}")
        print(f"   Role: {admin['role']}")
        print(f"   Password hash: {admin['password_hash'][:50]}...")
        print(f"   Salt: {admin['salt'][:50]}...")
        print()
        
        # Test password verification
        test_password = input("Enter the password from the dialog: ").strip()
        if not test_password:
            print("❌ No password entered")
            return False
        
        print()
        print(f"Testing password: {test_password}")
        
        is_valid = verify_password(test_password, admin['password_hash'], admin['salt'])
        
        if is_valid:
            print("✅ Password is CORRECT!")
            print()
            print("The password should work. Try logging in again.")
            return True
        else:
            print("❌ Password is INCORRECT!")
            print()
            print("The password doesn't match. This is a database issue.")
            return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_login()
    sys.exit(0 if success else 1)
