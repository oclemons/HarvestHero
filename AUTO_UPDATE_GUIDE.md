# Automated Wireless Updates Guide

This guide explains how to set up automatic updates for your clients without them having to download manually.

---

## **How Automatic Updates Work**

### **Current System (Already Implemented)**

The app has a built-in update system that:

1. **Checks GitHub** for new releases (on startup)
2. **Detects new version** automatically
3. **Notifies user** if update available
4. **Downloads silently** in background
5. **Applies on restart** or user click

---

## **Update Methods**

### **Method 1: Manual Update (User Clicks)**

**User Experience:**
1. App starts
2. Notification: "Update available"
3. User clicks "Update"
4. App downloads and restarts
5. ✅ Latest version running

**Setup:** Just create GitHub Release (already done!)

---

### **Method 2: Scheduled Auto-Update (Recommended)**

**User Experience:**
1. App runs normally
2. At scheduled time (e.g., 2 AM), checks for updates
3. If available, downloads silently
4. On next restart, uses new version
5. ✅ User has latest version

**Benefits:**
✅ Automatic  
✅ Happens during off-hours  
✅ No disruption  
✅ User sees notification  

---

### **Method 3: Silent Auto-Update (Advanced)**

**User Experience:**
1. App runs normally
2. Checks for updates periodically
3. Downloads silently
4. Updates without restart
5. ✅ Always latest version

**Benefits:**
✅ Completely automatic  
✅ No user interaction  
✅ No downtime  

**Drawbacks:**
❌ Users might not know app updated  

---

## **Setup Instructions**

### **Step 1: Create GitHub Release**

1. Go to: https://github.com/oclemons/HarvestHero/releases
2. Click "Create a new release"
3. Fill in details (version, description, etc.)
4. Upload ZIP file
5. Publish release

**The app will automatically detect it!**

---

### **Step 2: Configure Update Settings**

Create `update_config.json` in the app folder:

```json
{
  "auto_update": true,
  "check_on_startup": true,
  "scheduled_check": true,
  "check_time": "02:00",
  "silent_update": false,
  "notify_user": true
}
```

**Settings:**
- `auto_update`: Enable automatic updates
- `check_on_startup`: Check when app starts
- `scheduled_check`: Check at specific time
- `check_time`: Time to check (24-hour format)
- `silent_update`: Update without notification
- `notify_user`: Show notification to user

---

### **Step 3: Users Get Updates Automatically**

**That's it!** Users don't need to do anything.

- App checks automatically
- Downloads updates
- Applies on restart
- Always latest version

---

## **Release Workflow**

### **When You Have New Features/Fixes**

1. **Test locally**
   - Run full test checklist
   - Verify all features work

2. **Update VERSION.json**
   ```json
   {
     "version": "2.0.2",
     "last_updated": "2024-08-15T00:00:00"
   }
   ```

3. **Commit and push**
   ```bash
   git add -A
   git commit -m "Version 2.0.2 - New features"
   git push origin main
   ```

4. **Create GitHub Release**
   - Tag: v2.0.2
   - Upload ZIP file
   - Publish

5. **Users get notification**
   - Next time they start app
   - Or at scheduled check time
   - They can click "Update" or wait for auto-update

---

## **Monitoring Updates**

### **Check Update Status**

1. Go to GitHub Releases
2. See download count
3. Monitor for issues

### **Rollback if Needed**

1. Create new release with previous version
2. Users will see downgrade option
3. Or fix issue and release new version

---

## **Troubleshooting**

### **Update Not Showing**

1. Check GitHub release is published
2. Check ZIP file is attached
3. Restart app to check again
4. Check internet connection

### **Update Failed**

1. Check disk space
2. Check write permissions
3. Check internet connection
4. Check app logs

### **Force Update Check**

Users can manually check:
1. Open app
2. Go to Settings
3. Click "Check for Updates"
4. App checks GitHub immediately

---

## **Best Practices**

### **For You (Developer)**

1. **Test before releasing**
   - Run full test suite
   - Test on clean system
   - Verify all features

2. **Clear release notes**
   - List new features
   - List bug fixes
   - Include version number

3. **Version numbering**
   - Major.Minor.Patch
   - 2.0.0 = major release
   - 2.0.1 = bug fix
   - 2.1.0 = new feature

4. **Regular releases**
   - Release updates regularly
   - Don't wait too long
   - Keep users updated

### **For Users**

1. **Keep app running**
   - App checks for updates
   - Downloads in background
   - Updates on restart

2. **Restart regularly**
   - Updates apply on restart
   - Restart daily or weekly
   - Ensures latest version

3. **Check for updates manually**
   - Settings → Check for Updates
   - If they want latest version immediately

---

## **Current Setup**

**Version:** 2.0.1  
**Auto-Update:** ✅ Enabled  
**GitHub Releases:** ✅ Configured  
**Update Check:** ✅ On startup  

### **What's Configured**

✅ App checks GitHub automatically  
✅ Detects new releases  
✅ Downloads updates  
✅ Notifies users  
✅ Applies on restart  

### **What You Need to Do**

1. Create GitHub Release (when you have updates)
2. Upload ZIP file
3. Publish release
4. Users get notified automatically

---

## **Example Update Cycle**

### **Day 1: You Find a Bug**
- Fix the bug
- Test locally
- Update VERSION.json to 2.0.2
- Commit and push

### **Day 2: Create Release**
- Go to GitHub Releases
- Create v2.0.2 release
- Upload ZIP file
- Publish

### **Day 3: Users Get Update**
- User starts app
- App checks GitHub
- Finds v2.0.2
- Shows notification
- User clicks "Update"
- App downloads and restarts
- ✅ Bug fixed!

---

## **Advanced: Silent Auto-Update**

If you want updates to happen **completely silently** without user interaction:

1. Set `silent_update: true` in config
2. App downloads updates automatically
3. Updates on next restart
4. User doesn't need to do anything

**Note:** This is more aggressive. Users might not know app updated.

---

## **Questions?**

For more info:
- **Update system:** See `update_manager.py`
- **Version management:** See `VERSION.json`
- **GitHub Releases:** See `RELEASE_GUIDE.md`
- **Testing:** See `PRE_RELEASE_TESTING.md`

---

## **Summary**

✅ **Automatic updates are already set up!**

**For clients:**
1. They download app once
2. App checks for updates automatically
3. Updates happen wirelessly
4. No manual downloads needed
5. Always latest version

**For you:**
1. Fix bugs/add features
2. Update VERSION.json
3. Create GitHub Release
4. Users get update automatically

**That's it!** 🚀
