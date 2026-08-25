# 🔐 Login Troubleshooting Guide

**Status:** ✅ Login System Verified & Working  
**Date:** August 25, 2026  

---

## ✅ Current Status

The login system is **working correctly**!

**Admin Credentials:**
- Username: `admin`
- Password: `admin123`

---

## 🔧 If Login Isn't Working

### Issue 1: Account Locked (Too Many Failed Attempts)

**Symptom:** "Too many failed attempts. Try again in X seconds."

**Solution:**
```bash
# Run the reset script
python reset_login.py
```

This will:
- ✅ Reset the login throttle
- ✅ Verify admin credentials
- ✅ Reset password if needed
- ✅ Clear all lockouts

### Issue 2: Incorrect Password

**Symptom:** "Invalid username or password."

**Solution:**
```bash
# Run the reset script to reset password
python reset_login.py
```

The script will reset the admin password to `admin123`.

### Issue 3: Account Disabled

**Symptom:** "This account has been deactivated."

**Solution:**
```bash
# Run this Python code to reactivate
python3 << 'EOF'
from database import Database

db = Database()
user = db.get_user("admin")

if user:
    # Update user to active
    conn = db._connect()
    conn.execute(
        "UPDATE users SET is_active = 1 WHERE username = 'admin'"
    )
    conn.commit()
    conn.close()
    print("✅ Admin account reactivated!")
else:
    print("❌ Admin user not found!")
EOF
```

### Issue 4: Database Not Initialized

**Symptom:** "Error loading user data" or database errors

**Solution:**
```bash
# Initialize the database
python3 << 'EOF'
from database import Database
from auth import hash_password

db = Database()
print("✅ Database initialized!")

# Create admin user
password = "admin123"
password_hash, salt = hash_password(password)

ok, msg = db.create_user(
    username="admin",
    password_hash=password_hash,
    salt=salt,
    role="admin"
)

print(f"Result: {msg}")
if ok:
    print("✅ Admin user created!")
EOF
```

---

## 🚀 Quick Fix: Reset Everything

If you're having any login issues, run this one command:

```bash
python reset_login.py
```

This script will:
1. ✅ Reset login throttle
2. ✅ Verify admin user exists
3. ✅ Verify password works
4. ✅ Reset password if needed
5. ✅ Confirm login is working

---

## 📋 How Login Works

### Authentication Flow

```
User enters credentials
    ↓
Check if account is locked (throttle)
    ↓
If locked: Show "Try again in X seconds"
    ↓
If not locked: Check LDAP (if enabled)
    ↓
If LDAP fails: Check local database
    ↓
Verify password hash using PBKDF2-HMAC-SHA256
    ↓
If correct: Login successful
    ↓
If incorrect: Record failure & lock if needed
```

### Password Security

- **Algorithm:** PBKDF2-HMAC-SHA256
- **Iterations:** 600,000 (OWASP 2024 baseline)
- **Salt:** Random 64-character hex
- **Comparison:** Constant-time (hmac.compare_digest)

### Login Throttle

- **Max attempts:** 5
- **Base lockout:** 30 seconds
- **Exponential backoff:** Doubles each block
- **Max lockout:** 15 minutes
- **Resets on:** App restart or successful login

---

## 🔑 Default Credentials

**Username:** `admin`  
**Password:** `admin123`  

⚠️ **Important:** Change this password after first login!

---

## 📊 Verify Login is Working

Run this to verify:

```bash
python3 << 'EOF'
from database import Database
from auth import verify_password

db = Database()
user = db.get_user("admin")

if user:
    result = verify_password("admin123", user['password_hash'], user['salt'])
    print(f"Login test: {'✅ WORKING' if result else '❌ FAILED'}")
else:
    print("❌ Admin user not found!")
EOF
```

---

## 🆘 Still Having Issues?

### Check Database

```bash
python3 << 'EOF'
from database import Database

db = Database()
user = db.get_user("admin")

if user:
    print("✅ Admin user found")
    print(f"   Username: {user['username']}")
    print(f"   Role: {user['role']}")
    print(f"   Active: {user['is_active']}")
else:
    print("❌ Admin user not found!")
EOF
```

### Check Throttle

```bash
python3 << 'EOF'
import login_throttle

wait = login_throttle.locked_seconds("admin")
print(f"Account locked for: {wait} seconds")

if wait > 0:
    print("❌ Account is locked!")
    print("   Run: python reset_login.py")
else:
    print("✅ Account is not locked")
EOF
```

### Check Password

```bash
python3 << 'EOF'
from database import Database
from auth import verify_password

db = Database()
user = db.get_user("admin")

if user:
    result = verify_password("admin123", user['password_hash'], user['salt'])
    print(f"Password: {'✅ CORRECT' if result else '❌ INCORRECT'}")
else:
    print("❌ Admin user not found!")
EOF
```

---

## 📝 Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| Too many attempts | "Try again in X seconds" | Run `python reset_login.py` |
| Wrong password | "Invalid username or password" | Run `python reset_login.py` |
| Account disabled | "Account has been deactivated" | Reactivate with SQL |
| Database error | "Error loading user data" | Run `python reset_login.py` |
| Throttle stuck | Can't login even with correct password | Restart app or run reset script |

---

## ✅ Verification Checklist

- [x] Admin user exists
- [x] Admin user is active
- [x] Password is correct
- [x] Password verification works
- [x] Login throttle is working
- [x] Database is initialized
- [x] All authentication modules are working

---

## 🎯 Summary

**The login system is working correctly!**

✅ Admin user exists  
✅ Password is correct  
✅ Authentication is working  
✅ Throttle is working  
✅ Database is initialized  

**If you're having issues:**
1. Run `python reset_login.py`
2. Use credentials: `admin` / `admin123`
3. Change password after first login

---

Generated with [Devin](https://devin.ai)
