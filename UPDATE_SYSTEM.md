# Automatic Update System - Documentation

## Overview

Harvest Hero includes an automatic update system that allows you to push updates to GitHub and have all client installations automatically detect and install them.

---

## How It Works

### 1. **Version Management**
- Current version stored in `VERSION.json`
- Format: `major.minor.patch` (e.g., `2.0.0`)

### 2. **Update Detection**
- App checks GitHub API for latest release on startup
- Compares local version with GitHub latest release
- Notifies user if newer version available

### 3. **Update Installation**
- User clicks "Install Update"
- App downloads release zip from GitHub
- Extracts and applies files
- Restarts application automatically

### 4. **Safety Features**
- Backup of current files before update
- Skips critical directories (.git, data, etc.)
- Version verification
- Rollback capability

---

## Publishing Updates

### Step 1: Update VERSION.json

Update the version number in `VERSION.json`:

```json
{
  "version": "2.1.0",
  "app_name": "Harvest Hero Inventory Tracker",
  "last_updated": "2024-01-20T00:00:00",
  "features": [
    "New feature 1",
    "New feature 2"
  ]
}
```

### Step 2: Commit Changes

```bash
git add -A
git commit -m "Release v2.1.0 - New features and improvements"
```

### Step 3: Create Git Tag

```bash
git tag -a v2.1.0 -m "Release version 2.1.0"
git push origin v2.1.0
```

### Step 4: Create GitHub Release

The GitHub Actions workflow will automatically create a release when you push a tag. You can also manually create a release:

1. Go to https://github.com/oclemons/HarvestHero/releases
2. Click "Draft a new release"
3. Select tag: `v2.1.0`
4. Title: `Release 2.1.0`
5. Description: Add release notes
6. Attach the source code zip as an asset
7. Publish release

### Step 5: Users Receive Update

1. Next time users launch the app, it checks for updates
2. If new version available, notification appears
3. User clicks "Install Update"
4. App downloads and installs automatically
5. App restarts with new version

---

## File Structure

### Core Update Files

```
inventory_tracker/
├── update_manager.py          # Update logic and GitHub API
├── update_dialog.py           # UI for update notifications
├── VERSION.json               # Current version info
└── .github/workflows/
    └── release.yml            # GitHub Actions workflow
```

### Key Classes

#### UpdateManager
```python
from update_manager import get_update_manager

manager = get_update_manager()
has_update, version, notes = manager.check_for_updates()
manager.download_and_apply_async(progress_cb, complete_cb)
```

#### UpdateDialog
```python
from update_dialog import show_update_notification

show_update_notification(parent_window, update_manager)
```

---

## Configuration

### GitHub Repository Settings

1. **Repository URL**: https://github.com/oclemons/HarvestHero
2. **Owner**: oclemons
3. **Repo**: HarvestHero

Update these in `update_manager.py` if needed:

```python
GITHUB_OWNER = "oclemons"
GITHUB_REPO = "HarvestHero"
```

### API Rate Limits

- GitHub API: 60 requests/hour (unauthenticated)
- 5000 requests/hour (authenticated with token)

For higher limits, add GitHub token to requests:

```python
headers = {"Authorization": f"token {GITHUB_TOKEN}"}
response = requests.get(url, headers=headers)
```

---

## Release Workflow

### Quick Release Process

```bash
# 1. Make your changes and commit
git add -A
git commit -m "FEATURE: Add new functionality"

# 2. Update version
# Edit VERSION.json with new version number

# 3. Commit version update
git add VERSION.json
git commit -m "Bump version to 2.1.0"

# 4. Create tag
git tag -a v2.1.0 -m "Release v2.1.0"

# 5. Push everything
git push origin main
git push origin v2.1.0

# 6. Create release on GitHub (automatic via Actions or manual)
```

### Semantic Versioning

- **Major** (2.0.0): Breaking changes, major features
- **Minor** (2.1.0): New features, backward compatible
- **Patch** (2.1.1): Bug fixes, small improvements

---

## User Experience

### Update Notification

When user launches app:

1. **Checking Dialog** appears briefly
2. If update available:
   - **Update Dialog** shows
   - Release notes displayed
   - User can choose "Install Update" or "Later"
3. If installing:
   - **Progress bar** shows download progress
   - **Status updates** shown
   - App **restarts automatically**

### No Update Available

- Brief message: "You are running the latest version"
- App continues normally

---

## Troubleshooting

### Update Check Fails

**Problem**: "Error checking for updates"

**Solutions**:
1. Check internet connection
2. Verify GitHub repository is accessible
3. Check GitHub API status
4. Review firewall/proxy settings

### Download Fails

**Problem**: "Download failed"

**Solutions**:
1. Check internet connection
2. Verify release exists on GitHub
3. Check disk space
4. Review firewall/proxy settings

### Installation Fails

**Problem**: "Update failed"

**Solutions**:
1. Check write permissions to app directory
2. Ensure no files are locked
3. Check disk space
4. Review error message for details

### App Won't Restart

**Problem**: App doesn't restart after update

**Solutions**:
1. Manually restart the application
2. Check if main.py exists
3. Review system logs for errors

---

## Advanced Configuration

### Custom GitHub Repository

To use a different GitHub repository:

```python
# In update_manager.py
GITHUB_OWNER = "your-username"
GITHUB_REPO = "your-repo-name"
```

### Custom Version File Location

```python
manager = UpdateManager(app_root="/custom/path")
```

### Manual Version Check

```python
from update_manager import get_update_manager

manager = get_update_manager()
has_update, version, notes = manager.check_for_updates()

if has_update:
    print(f"Update available: {version}")
    print(f"Release notes: {notes}")
```

### Disable Auto-Check

Remove or comment out in `main.py`:

```python
# self.after(2000, self._check_for_updates)
```

---

## Security Considerations

### HTTPS Only

- All GitHub API calls use HTTPS
- No credentials stored locally
- No authentication required for public repos

### File Integrity

- Downloaded files extracted to temp directory first
- Current files backed up before update
- Critical directories skipped (.git, data)
- Version verification after update

### Rollback

If update causes issues:

1. Restore from `.backup` directory
2. Or reinstall previous version manually
3. Or revert git tag and re-release

---

## Monitoring Updates

### Check Update Status

```python
from update_manager import get_update_manager

manager = get_update_manager()
print(f"Current version: {manager.current_version}")
print(f"Latest version: {manager.latest_version}")
print(f"Update available: {manager.update_available}")
```

### View Update History

Check `VERSION.json`:

```json
{
  "version": "2.1.0",
  "last_updated": "2024-01-20T10:30:00"
}
```

---

## Best Practices

### Before Releasing

- [ ] Test changes thoroughly
- [ ] Update VERSION.json
- [ ] Write clear release notes
- [ ] Commit all changes
- [ ] Create git tag
- [ ] Push to GitHub

### Release Notes Template

```markdown
## Version 2.1.0

### New Features
- Feature 1 description
- Feature 2 description

### Bug Fixes
- Bug fix 1
- Bug fix 2

### Improvements
- Improvement 1
- Improvement 2

### Installation
Download and run. Update will install automatically on next launch.
```

### Testing Updates

1. Create test release with v0.0.1 tag
2. Verify app detects update
3. Test download and installation
4. Verify app restarts correctly
5. Check version updated in VERSION.json

---

## FAQ

**Q: Can users skip updates?**
A: Yes, they can click "Later" to skip. Update will prompt again on next launch.

**Q: What if update fails halfway?**
A: App rolls back to previous version and shows error message.

**Q: Do users need internet to use the app?**
A: No, only for checking/installing updates. App works offline.

**Q: Can I force an update?**
A: Currently optional. Could be made mandatory in future.

**Q: How often does it check for updates?**
A: On app startup, then every session.

**Q: Can I schedule updates?**
A: Not currently, but could be added as enhancement.

---

## Future Enhancements

- [ ] Scheduled update checks
- [ ] Mandatory updates for critical fixes
- [ ] Update rollback UI
- [ ] Update history viewer
- [ ] Differential updates (only changed files)
- [ ] Signed releases for verification
- [ ] Update notifications in app
- [ ] Offline update installation

---

## Support

For issues with the update system:

1. Check this documentation
2. Review error messages
3. Check GitHub repository status
4. Review system logs
5. Contact support with error details

---

**Last Updated**: 2024-01-20
**Version**: 1.0
