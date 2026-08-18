# Preserving User Data Across Updates

## Problem

When users download a new version of Harvest Hero, the app shows a temporary password popup. This happens because:

1. User downloads new ZIP file
2. Extracts to a new folder
3. New folder has no database
4. App creates fresh database with random admin password
5. User sees password popup

## Solution

The database and user accounts are stored in a **persistent location** that survives updates.

### How It Works

**Database Location:**
- Windows: `C:\Users\[Username]\AppData\Local\HarvestHero\data\inventory.db`
- macOS: `~/Library/Application Support/HarvestHero/data/inventory.db`
- Linux: `~/.local/share/HarvestHero/data/inventory.db`

This location is defined in `paths.py` as `USER_DIR`.

**Key Point:** This is OUTSIDE the application folder, so it persists across updates.

### For Users

**When downloading a new version:**

1. Download new ZIP file
2. Extract to a NEW folder (don't overwrite old one)
3. Run the new version
4. ✅ App finds existing database in USER_DIR
5. ✅ User accounts are preserved
6. ✅ No password popup
7. ✅ Login with existing credentials

**Example:**
```
Old version: C:\Users\John\Downloads\HarvestHero-2.0.0\
New version: C:\Users\John\Downloads\HarvestHero-2.0.1\

Database: C:\Users\John\AppData\Local\HarvestHero\data\inventory.db
(Same location for both versions)
```

### For Deployment

**When deploying to client devices:**

1. First time setup:
   - User downloads ZIP
   - Extracts folder
   - Runs `py main.py`
   - App creates database in USER_DIR
   - Shows admin password popup
   - User logs in with that password

2. Future updates:
   - User downloads new ZIP
   - Extracts to new folder
   - Runs `py main.py`
   - App finds existing database
   - ✅ No password popup
   - ✅ Logs in with existing password

### Verify Data Persistence

**To check if database is in the right place:**

**Windows:**
```cmd
cd %APPDATA%\Local\HarvestHero\data
dir
```
Should show: `inventory.db`

**macOS/Linux:**
```bash
ls ~/Library/Application\ Support/HarvestHero/data/
# or
ls ~/.local/share/HarvestHero/data/
```
Should show: `inventory.db`

### What Gets Preserved

✅ User accounts and passwords  
✅ Inventory items  
✅ Shelf assignments  
✅ Transaction history  
✅ All settings  
✅ All data  

### What Gets Updated

✅ Application code  
✅ Features  
✅ Bug fixes  
✅ UI improvements  

### Troubleshooting

**If user sees password popup after update:**

1. Check if database exists:
   - Windows: `C:\Users\[Username]\AppData\Local\HarvestHero\data\inventory.db`
   - macOS: `~/Library/Application Support/HarvestHero/data/inventory.db`

2. If database exists but popup still shows:
   - Database might be corrupted
   - Try backing up and deleting it
   - App will create fresh database

3. If user needs to reset password:
   - Run: `py reset_admin_password.py`
   - Or use password reset feature in app

### Best Practices for Users

1. **Keep old version folder** until new version works
2. **Extract new version to different folder**
3. **Run new version** and verify everything works
4. **Delete old version** if happy with new one

### For Developers

The database path is defined in `paths.py`:

```python
# Windows
USER_DIR = os.path.join(os.environ.get('APPDATA'), 'HarvestHero')

# macOS
USER_DIR = os.path.expanduser('~/Library/Application Support/HarvestHero')

# Linux
USER_DIR = os.path.expanduser('~/.local/share/HarvestHero')
```

This ensures data persists across:
- ✅ Version updates
- ✅ Folder moves
- ✅ Reinstalls
- ✅ Multiple installations

---

## Summary

**Users don't need to do anything special!**

- Download new version
- Extract to new folder
- Run app
- ✅ All data is preserved
- ✅ No password popup
- ✅ Login with existing credentials

The system automatically handles data persistence across updates.
