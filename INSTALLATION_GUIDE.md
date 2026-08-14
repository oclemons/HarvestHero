# Harvest Hero Inventory Tracker - Installation Guide

## Quick Start

### For Windows Users (Recommended)

#### Option 1: Standalone Executable (Easiest)
1. Go to: https://github.com/oclemons/HarvestHero/releases
2. Download the latest `.exe` file
3. Double-click to run
4. No installation needed!

#### Option 2: From Source Code
1. Go to: https://github.com/oclemons/HarvestHero
2. Click **Code** → **Download ZIP**
3. Extract the ZIP file
4. Follow "Installation from Source" below

---

## Detailed Installation Instructions

### Prerequisites

#### Windows
- Windows 10 or later
- 500 MB free disk space
- Internet connection (for initial setup and updates)

#### macOS
- macOS 10.14 or later
- 500 MB free disk space
- Internet connection

#### Linux
- Ubuntu 18.04 or later (or equivalent)
- 500 MB free disk space
- Internet connection

---

## Installation Methods

### Method 1: Standalone Executable (Windows Only)

**Easiest method - No installation required!**

#### Steps:

1. **Download**
   - Visit: https://github.com/oclemons/HarvestHero/releases
   - Look for the latest release
   - Download `HarvestHero-v2.0.0.exe` (or latest version)

2. **Run**
   - Double-click the `.exe` file
   - Windows may show a security warning
   - Click "Run anyway" or "More info" → "Run anyway"

3. **First Launch**
   - App opens to login screen
   - Default admin account created automatically
   - Password shown in popup (save this!)

4. **Login**
   - Username: `admin`
   - Password: (shown in popup)
   - Click "Login"

5. **Change Password**
   - Go to Admin → User Management
   - Change default admin password immediately
   - Create additional user accounts

**That's it! App is ready to use.**

---

### Method 2: Download from GitHub (All Platforms)

#### Step 1: Download the Source Code

**Option A: Using Web Browser**
1. Go to: https://github.com/oclemons/HarvestHero
2. Click green **Code** button
3. Click **Download ZIP**
4. Save to your desired location
5. Extract the ZIP file

**Option B: Using Git (Advanced)**
```bash
git clone https://github.com/oclemons/HarvestHero.git
cd HarvestHero
```

#### Step 2: Install Python

**Windows:**
1. Download Python 3.10+ from: https://www.python.org/downloads/
2. Run installer
3. **IMPORTANT**: Check "Add Python to PATH"
4. Click "Install Now"

**macOS:**
```bash
# Using Homebrew (if installed)
brew install python3

# Or download from https://www.python.org/downloads/
```

**Linux:**
```bash
sudo apt-get install python3 python3-pip
```

#### Step 3: Install Dependencies

1. Open Command Prompt/Terminal
2. Navigate to the app directory:
   ```bash
   cd path/to/HarvestHero
   ```

3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

#### Step 4: Run the Application

```bash
python main.py
```

**First Launch:**
- Login screen appears
- Default admin account created
- Password shown in popup
- Login with admin account

---

### Method 3: Create Windows Shortcut (For Easy Access)

#### Steps:

1. **Create Shortcut**
   - Right-click on `HarvestHero.exe`
   - Select "Send to" → "Desktop (create shortcut)"
   - Shortcut appears on desktop

2. **Customize Shortcut**
   - Right-click shortcut
   - Select "Properties"
   - Change name to "Harvest Hero"
   - Click "Change Icon"
   - Select an icon (or use default)

3. **Pin to Taskbar** (Optional)
   - Right-click shortcut
   - Select "Pin to taskbar"
   - Appears in Windows taskbar for quick access

---

## First-Time Setup

### Initial Login

1. **Username**: `admin`
2. **Password**: (shown in popup on first launch)
3. Click **Login**

### Change Default Password

1. Click **Admin** in navigation
2. Click **User Management**
3. Find "admin" user
4. Click **Edit**
5. Enter new password
6. Click **Save**

### Create Additional Users

1. Go to **Admin** → **User Management**
2. Click **+ Add User**
3. Enter username and password
4. Select role: **Admin** or **Staff**
5. Click **Create User**

### Set Organization Name

1. Go to **Settings**
2. Enter your organization name
3. Click **Save**

---

## Automatic Updates

### How Updates Work

1. **Check for Updates**
   - App automatically checks on startup
   - Checks GitHub for new releases

2. **Update Notification**
   - If new version available, dialog appears
   - Shows version number and release notes
   - Click "Install Update" or "Later"

3. **Installation**
   - Download begins with progress bar
   - Files extracted and installed
   - App restarts automatically
   - New version running

### Manual Update Check

1. Go to **Settings**
2. Look for "Check for Updates" button
3. Click to manually check
4. Follow installation if update available

---

## Troubleshooting

### App Won't Start

**Problem**: Double-clicking .exe does nothing

**Solutions**:
1. Try right-click → "Run as administrator"
2. Check if Python is installed (if using source code)
3. Check Windows Defender/Antivirus isn't blocking
4. Restart computer and try again

### "Python not found" Error

**Problem**: Error when running `python main.py`

**Solutions**:
1. Install Python from https://www.python.org/downloads/
2. Make sure "Add Python to PATH" is checked during installation
3. Restart Command Prompt after installing Python
4. Try `python3 main.py` instead

### "Module not found" Error

**Problem**: Error like "No module named 'customtkinter'"

**Solutions**:
1. Make sure you're in the correct directory:
   ```bash
   cd path/to/HarvestHero
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Try with `pip3` if `pip` doesn't work:
   ```bash
   pip3 install -r requirements.txt
   ```

### Login Screen Appears Blank

**Problem**: Login screen doesn't show properly

**Solutions**:
1. Wait a few seconds for app to load
2. Restart the application
3. Check if database file exists (data/inventory.db)
4. Try running as administrator

### Can't Connect to Database

**Problem**: "Database error" or "Connection failed"

**Solutions**:
1. Check if `data/` folder exists
2. Check folder permissions (must be writable)
3. Close other instances of the app
4. Restart the application

### Update Won't Install

**Problem**: "Update failed" error

**Solutions**:
1. Check internet connection
2. Check disk space (need at least 500 MB)
3. Check folder permissions
4. Try manual update:
   - Download latest release manually
   - Extract over existing installation
   - Restart app

---

## System Requirements

### Minimum Requirements
- **OS**: Windows 10, macOS 10.14, or Ubuntu 18.04+
- **RAM**: 2 GB
- **Disk Space**: 500 MB
- **Internet**: Required for updates and GitHub sync

### Recommended Requirements
- **OS**: Windows 11, macOS 12+, or Ubuntu 20.04+
- **RAM**: 4 GB or more
- **Disk Space**: 1 GB
- **Internet**: Broadband connection

---

## Network Setup (Multi-System LAN)

### For Multiple Pantry Computers

#### Option 1: Shared Database (Recommended)

1. **Set up shared network folder**
   - Create shared folder on network drive
   - Give all computers access

2. **Configure each computer**
   - Edit `config.json`
   - Point to shared database location
   - Restart app

3. **All computers sync automatically**
   - Changes visible on all machines
   - Real-time inventory updates

#### Option 2: Standalone Installation

1. **Install on each computer**
   - Follow installation steps above
   - Each has local database

2. **Manual sync**
   - Export data from one computer
   - Import on other computers
   - Or use cloud sync service

---

## Uninstallation

### Windows Executable

1. Delete the `.exe` file
2. Delete the `data/` folder (if you want to remove database)
3. Done!

### From Source Code

1. Delete the entire `HarvestHero` folder
2. Done!

**Note**: Deleting the `data/` folder removes all inventory data. Back up first if needed!

---

## Backup & Recovery

### Backup Your Data

1. **Locate database file**
   - Windows: `C:\Users\YourName\AppData\Local\HarvestHero\data\inventory.db`
   - macOS: `~/Library/Application Support/HarvestHero/data/inventory.db`
   - Linux: `~/.local/share/HarvestHero/data/inventory.db`

2. **Copy to safe location**
   - External drive
   - Cloud storage
   - Network drive

3. **Backup frequency**
   - Daily recommended
   - Or use app's built-in backup (Settings → Backup & Export)

### Restore from Backup

1. **Close the app**
2. **Replace database file**
   - Copy backup `inventory.db` to data folder
   - Overwrite existing file
3. **Restart app**
   - Data restored

---

## Getting Help

### Documentation
- **Installation**: This file
- **Update System**: UPDATE_SYSTEM.md
- **Features**: README.md
- **Troubleshooting**: See section above

### GitHub Issues
1. Go to: https://github.com/oclemons/HarvestHero/issues
2. Click "New Issue"
3. Describe your problem
4. Include error messages
5. Submit

### Contact Support
- Email: (add your email)
- Phone: (add your phone)
- Hours: (add your hours)

---

## Advanced Configuration

### Custom Database Location

Edit `config.json`:
```json
{
  "database": {
    "type": "sqlite",
    "path": "/custom/path/to/inventory.db"
  }
}
```

### Network Database (PostgreSQL)

Edit `config.json`:
```json
{
  "database": {
    "type": "postgresql",
    "host": "192.168.1.100",
    "port": 5432,
    "user": "admin",
    "password": "password",
    "database": "harvest_hero"
  }
}
```

### LDAP Authentication

Edit `config.json`:
```json
{
  "auth": {
    "type": "ldap",
    "server": "ldap.example.com",
    "port": 389,
    "base_dn": "dc=example,dc=com"
  }
}
```

---

## Security Best Practices

### Passwords
- Change default admin password immediately
- Use strong passwords (12+ characters)
- Include uppercase, lowercase, numbers, symbols

### Access Control
- Create separate user accounts for each person
- Use appropriate roles (admin/staff)
- Disable inactive accounts

### Data Protection
- Regular backups (daily recommended)
- Secure backup storage
- Encrypt sensitive data

### Network Security
- Use VPN for remote access
- Firewall protection
- Regular security updates

---

## Performance Tips

### Optimize Performance

1. **Regular Maintenance**
   - Clear old transaction history
   - Archive old inventory items
   - Optimize database (Settings → Maintenance)

2. **Network Optimization**
   - Use wired connection when possible
   - Reduce network traffic
   - Cache frequently accessed data

3. **Hardware Optimization**
   - Close unnecessary programs
   - Allocate sufficient RAM
   - Use SSD for database

---

## Frequently Asked Questions

**Q: Is the app free?**
A: Yes, Harvest Hero is free and open-source.

**Q: Do I need internet to use the app?**
A: No, only for checking updates and GitHub sync.

**Q: Can I use on multiple computers?**
A: Yes, install on each computer or use shared database.

**Q: How do I backup my data?**
A: Use Settings → Backup & Export or copy database file.

**Q: Can I restore from backup?**
A: Yes, copy backup file back to data folder.

**Q: What if I forget my password?**
A: Delete database and reinstall (creates new admin account).

**Q: How do I update the app?**
A: App checks automatically. Click "Install Update" when prompted.

**Q: Can I customize the app?**
A: Yes, edit config.json or modify source code.

**Q: Is my data secure?**
A: Data stored locally. Use strong passwords and backups.

**Q: What if I find a bug?**
A: Report on GitHub Issues or contact support.

---

## Version Information

**Current Version**: 2.0.0
**Release Date**: 2024-01-20
**Python Version**: 3.10+
**License**: Open Source

---

## Next Steps

1. **Download and Install**
   - Follow installation method above
   - Complete first-time setup

2. **Create User Accounts**
   - Admin for managers
   - Staff for intake workers

3. **Configure Settings**
   - Organization name
   - Appearance preferences
   - Database location

4. **Add Inventory**
   - Import from CSV
   - Or add items manually
   - Set barcodes

5. **Start Using**
   - Begin scanning items
   - Track inventory
   - Generate reports

---

**For more information, visit**: https://github.com/oclemons/HarvestHero

**Last Updated**: 2024-01-20
**Version**: 1.0
