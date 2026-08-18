# Release Guide - Pushing Updates to Users

This guide explains how to release updates to end users without them having to download from GitHub again.

---

## Quick Summary

**Best Method: GitHub Releases + Built-in Auto-Update**

The application has a built-in update system that:
1. Checks GitHub for new releases
2. Notifies users of updates
3. Downloads and installs automatically
4. Restarts with new version

---

## Step 1: Prepare the Release

### Update Version Number

Edit `VERSION.json`:
```json
{
  "version": "2.0.1",
  "app_name": "Harvest Hero Inventory Tracker",
  "last_updated": "2024-08-14T00:00:00",
  "features": [...],
  "recent_fixes": [...]
}
```

### Commit Changes

```bash
git add -A
git commit -m "UPDATE: Version 2.0.1 - Description of changes"
git push origin main
```

---

## Step 2: Create GitHub Release

### Via GitHub Web Interface

1. **Go to GitHub Repository**
   - https://github.com/oclemons/HarvestHero

2. **Click "Releases"** (on right side)

3. **Click "Create a new release"**

4. **Fill in Details:**
   - **Tag version:** v2.0.1
   - **Release title:** Version 2.0.1 - Shelf Management Improvements
   - **Description:** 
     ```
     ## New Features
     - Edit and rename shelves
     - Sync storage locations across views
     - Improved shelf management UI

     ## Bug Fixes
     - Fixed Add Shelf dialog buttons visibility
     - Fixed shelf creation and editing
     - Fixed storage location syncing
     - Fixed database column errors

     ## Installation
     Users will see an update notification in the app.
     Click "Update" to download and install automatically.
     ```

5. **Upload ZIP File:**
   - Click "Attach binaries by dropping them here or selecting them"
   - Create ZIP of latest code:
     ```bash
     cd /Users/octayviaclemons/CascadeProjects
     zip -r HarvestHero-2.0.1.zip inventory_tracker/
     ```
   - Upload the ZIP file

6. **Click "Publish release"**

---

## Step 3: Users Get Notified

### What Happens Automatically

1. **App checks for updates** (on startup)
2. **Finds new release** on GitHub
3. **Shows notification** to user
4. **User clicks "Update"**
5. **App downloads ZIP**
6. **App extracts files**
7. **App restarts** with new version

### User Experience

```
┌─────────────────────────────────┐
│  Update Available               │
├─────────────────────────────────┤
│ Version 2.0.1 is available      │
│ Current: 2.0.0                  │
│                                 │
│ [Update Now]  [Later]           │
└─────────────────────────────────┘
```

---

## Alternative Methods

### Method 2: Manual Git Update (If Git Installed)

Users run:
```bash
cd HarvestHero
git pull origin main
python main.py
```

### Method 3: Batch Update Script

Create `update.bat`:
```batch
@echo off
echo Updating Harvest Hero...
cd /d "%~dp0"
git pull origin main
echo Update complete! Restarting...
timeout /t 3
python main.py
```

Users double-click `update.bat`

### Method 4: Network Shared Folder

1. Create shared network folder
2. Put latest code there
3. Users run sync script
4. Script pulls files
5. App restarts

---

## Release Checklist

Before releasing:

- [ ] Update VERSION.json
- [ ] Test all features locally
- [ ] Run PRE_RELEASE_TESTING.md checklist
- [ ] Commit all changes
- [ ] Push to GitHub
- [ ] Create GitHub Release
- [ ] Upload ZIP file
- [ ] Publish release
- [ ] Test update on client device

---

## Monitoring Updates

### Check Release Status

1. Go to GitHub Releases
2. See download count
3. Monitor for issues

### Rollback if Needed

If update causes problems:

1. Create new release with previous version
2. Users can downgrade
3. Or fix issue and release new version

---

## Update System Details

### How App Checks for Updates

File: `update_manager.py`

```python
# Checks GitHub API
https://api.github.com/repos/oclemons/HarvestHero/releases/latest

# Looks for ZIP file in assets
# Downloads if new version available
# Extracts and restarts
```

### Configuration

File: `VERSION.json`

- Current version
- Last updated date
- Features list
- Recent fixes

---

## Troubleshooting

### Update Not Showing

- Check GitHub release is published
- Check ZIP file is attached
- Restart app to check again
- Check internet connection

### Update Failed

- Check disk space
- Check write permissions
- Check internet connection
- Try manual update

### Rollback to Previous Version

1. Go to GitHub Releases
2. Find previous version
3. Create new release with old version
4. Users will see downgrade option

---

## Best Practices

1. **Always test before releasing**
   - Run full test checklist
   - Test on clean system
   - Verify all features work

2. **Clear release notes**
   - List new features
   - List bug fixes
   - Include installation instructions

3. **Version numbering**
   - Major.Minor.Patch
   - 2.0.0 = major release
   - 2.0.1 = patch/bug fix
   - 2.1.0 = minor feature

4. **Regular releases**
   - Release updates regularly
   - Don't wait too long
   - Keep users updated

5. **Communication**
   - Tell users about updates
   - Explain what changed
   - Provide support if issues

---

## Current Release

**Version:** 2.0.1  
**Date:** 2024-08-14  
**Status:** Ready for release

### What's New
- Edit and rename shelves
- Sync storage locations
- Improved shelf UI
- Bug fixes

### How to Release
1. Follow "Step 1: Prepare Release" (already done)
2. Follow "Step 2: Create GitHub Release"
3. Users will see update notification

---

## Questions?

For more info on:
- **Auto-update system:** See `update_manager.py`
- **Version management:** See `VERSION.json`
- **Testing:** See `PRE_RELEASE_TESTING.md`
- **Deployment:** See `CLIENT_SETUP.md`

---

**Ready to release? Follow Step 2 above!** 🚀
