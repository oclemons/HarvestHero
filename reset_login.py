#!/usr/bin/env python3
"""Reset login throttle and verify admin credentials."""

import sys
from database import Database
from auth import verify_password, hash_password
import login_throttle

print("=" * 70)
print("🔐 LOGIN RESET & VERIFICATION TOOL")
print("=" * 70)

# Reset throttle
print("\n1️⃣  Resetting login throttle...")
login_throttle.reset_all()
print("   ✅ Throttle reset")

# Get admin user
print("\n2️⃣  Checking admin user...")
db = Database()
user = db.get_user("admin")

if not user:
    print("   ❌ Admin user not found!")
    sys.exit(1)

print(f"   ✅ Admin user found")
print(f"      Username: {user['username']}")
print(f"      Role: {user['role']}")
print(f"      Active: {'Yes' if user['is_active'] else 'No'}")

# Verify password
print("\n3️⃣  Verifying password...")
test_password = "admin123"
result = verify_password(test_password, user['password_hash'], user['salt'])

if result:
    print(f"   ✅ Password verification successful!")
else:
    print(f"   ❌ Password verification failed!")
    print(f"   🔧 Resetting password to: {test_password}")
    
    new_hash, new_salt = hash_password(test_password)
    ok, msg = db.update_user_password(user['id'], new_hash, new_salt)
    
    if ok:
        print(f"   ✅ Password reset successful!")
    else:
        print(f"   ❌ Password reset failed: {msg}")
        sys.exit(1)

# Final verification
print("\n4️⃣  Final verification...")
user = db.get_user("admin")
result = verify_password(test_password, user['password_hash'], user['salt'])

if result:
    print(f"   ✅ Login is working!")
else:
    print(f"   ❌ Login still not working!")
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ LOGIN RESET COMPLETE!")
print("=" * 70)
print("\n📋 LOGIN CREDENTIALS:")
print(f"   Username: admin")
print(f"   Password: admin123")
print("\n🚀 You can now sign in to the application!")
print("=" * 70)
