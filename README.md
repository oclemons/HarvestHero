# Harvest Hero — Pantry Intelligence Platform

A local desktop inventory management application built with Python, CustomTkinter, and SQLite.  
No internet connection required. All data is stored in `data/inventory.db` on the device where the app runs.

---

## 🚀 Quick Download & Install

### For Windows Users
1. Go to https://github.com/oclemons/HarvestHero/releases/latest
2. Download **`HarvestHeroSetup-<version>.exe`**.
3. Run it. Windows may show a SmartScreen warning the first time; click **More info → Run anyway** (the installer is not code-signed yet).
4. Launch **Harvest Hero** from the Start menu or the desktop shortcut.

Future updates are handled by the app itself — open Harvest Hero, click **Install Update** when prompted, and it swaps itself out automatically. No downloads, no CMD, no data loss.

### For Mac / Linux Users (developer / staff mode)
1. Clone the repo: `git clone https://github.com/oclemons/HarvestHero.git`
2. `cd HarvestHero`
3. `pip install -r requirements.txt`
4. `python main.py`

**📖 Full Installation Guide**: see [INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md).

---

## Table of Contents

1. [Quick Download & Install](#-quick-download--install)
2. [Requirements](#requirements)
3. [Quick Start](#quick-start)
4. [Default Login](#default-login)
5. [Automatic Updates](#automatic-updates)
6. [Using a USB Barcode Scanner](#using-a-usb-barcode-scanner)
7. [Feature Guide](#feature-guide)
8. [Packaging into a Windows .exe](#packaging-into-a-windows-exe)
9. [Sending the App to Someone](#sending-the-app-to-someone)
10. [File Structure](#file-structure)
11. [Troubleshooting](#troubleshooting)
12. [Documentation](#documentation)

---

## Requirements

- **Python 3.10 or newer** – download from https://www.python.org/downloads/
  - During installation on Windows, tick **"Add Python to PATH"**
- The libraries listed in `requirements.txt`

---

## Quick Start

### Easiest way (recommended for all platforms)

| Platform | What to do |
|---|---|
| **Mac / Linux** | Open Terminal in this folder → `chmod +x run.sh && ./run.sh` |
| **Windows** | Double-click **`run.bat`** |

The launcher script automatically creates a virtual environment, installs all dependencies, and starts the app. **No manual pip install needed.**

### Manual start (if you prefer)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the application
python main.py
```

> **Tip – Windows:** if `python` is not recognised, try `py` instead.

---

## Default Login

| Username | Password  | Role  |
|----------|-----------|-------|
| `admin`  | `admin123`| Admin |

**Change this password immediately** after your first login via *Manage Users → Reset Password*.

Passwords are hashed with PBKDF2-HMAC-SHA256 and are never stored in plain text.

---

## Automatic Updates

Installed Windows builds update themselves. On every launch the app calls the GitHub Releases API, compares the tag against its own `VERSION.json`, and — if a newer release is available — pops up an **Update Available** dialog.

When the user clicks **Install Update**:

1. The Windows installer (`HarvestHeroSetup-<new-version>.exe`) is downloaded to `%TEMP%\HarvestHero-update\`.
2. The SHA-256 of the downloaded file is checked against the `.sha256` sidecar attached to the release. A mismatch aborts before anything is installed.
3. The installer is launched with `/SILENT /RESTARTAPPLICATIONS /CLOSEAPPLICATIONS`. It closes the running app, replaces it, and relaunches the new version.
4. User data in `%APPDATA%\HarvestHero` is never touched by the installer.

If the download or checksum fails, the running install is unaffected — the user keeps working on the previous version and can retry later.

For developer / macOS installs there is no in-place upgrade path; the update dialog offers **Open Release Page** so devs can grab the installer or `git pull`.

See [UPDATE_SYSTEM.md](UPDATE_SYSTEM.md) for technical details and [PRESERVE_DATA_ON_UPDATE.md](PRESERVE_DATA_ON_UPDATE.md) for the data-persistence contract.

---

## Using a USB Barcode Scanner

USB barcode scanners work like a keyboard – they type the barcode number and then press **Enter**.

1. Launch the application and log in.
2. Click once inside the **Barcode** field on the dashboard.
3. Scan an item. The scanner types the barcode and hits Enter automatically.
4. The item details appear instantly. Press **Scan In** or **Scan Out**.
5. After each transaction the barcode field clears and refocuses so the next scan is immediate.

**You do not need any special software or drivers** for a standard USB HID barcode scanner.

---

## Feature Guide

### Dashboard
- **Barcode field** – click here before scanning.
- **Quantity** – defaults to 1; change before clicking Scan In / Scan Out.
- **Recipient** – required for Scan Out (records who received the item).
- **Status bar** – shows READY / ITEM NOT FOUND / OUT OF STOCK / LOW STOCK / SUCCESS / ERROR.
- **Low-stock badge** – shows how many items are at or below minimum stock.

### Scan In
Adds stock. Finds the item by barcode, adds the quantity, saves a transaction record, then clears the form.

### Scan Out
Removes stock. Requires a recipient name. Checks there is enough stock before deducting. Saves a transaction record.

### Add Item *(Admin only)*
Fill in the barcode, name, category, starting quantity, minimum stock, and notes.  
Duplicate barcodes are rejected automatically.

### View Inventory
Shows all items in a searchable table.  
- 🟡 Yellow rows = Low Stock  
- 🔴 Red rows = Out of Stock  
- Admins can **Edit** or **Delete** items (double-click to edit).

### Transaction History
Full log of every scan-in and scan-out with filters for date, type, and recipient.  
Export to **CSV** or **Excel**.

### Reports
Six built-in reports:
- Current Inventory
- Low Stock
- Out of Stock
- Scan In History
- Scan Out History
- Recipient Giveaway History

All reports export to **CSV** or **Excel**.

### Manage Users *(Admin only)*
- Add staff or admin accounts.
- Toggle accounts active / inactive.
- Flip between admin and staff roles.
- Reset passwords.

---

## Cutting a Release

Development happens on macOS; the Windows installer is built by GitHub Actions on a `windows-latest` runner. You do **not** need Windows to ship a release.

### 1. Merge everything to `main`

Make sure `VERSION.json` on `main` reflects the version you're about to ship. Follow semantic versioning — `MAJOR.MINOR.PATCH`:

- **PATCH** (`2.1.0` → `2.1.1`): bug fixes only.
- **MINOR** (`2.1.0` → `2.2.0`): new features, no breaking changes.
- **MAJOR** (`2.1.0` → `3.0.0`): breaking changes to data model, config, or public behaviour.

### 2. Tag and push

```bash
git tag v2.1.0
git push origin v2.1.0
```

That's it. Pushing a tag matching `v*.*.*` triggers the **Windows Release** workflow in `.github/workflows/windows-release.yml`, which:

1. Checks out the tag.
2. Sets up Python 3.11 on Windows.
3. Installs dependencies + PyInstaller.
4. Syncs `VERSION.json` to the tag.
5. Regenerates multi-resolution icons from `assets/HarvestHeroIcon.png`.
6. Runs `pyinstaller HarvestHero.spec` to produce `dist/HarvestHero/HarvestHero.exe`.
7. Installs Inno Setup 6 via Chocolatey.
8. Runs `iscc /DAppVersion=<ver> installer/HarvestHero.iss` to produce `dist/installer/HarvestHeroSetup-<ver>.exe`.
9. Computes the installer's SHA-256 and writes it to `.exe.sha256`.
10. Creates the GitHub Release, attaches the installer + checksum, and auto-fills release notes from commits.

Watch the workflow at **Actions → Windows Release**. On success the release is public and every already-installed client will offer the update on its next launch.

### 3. Local development build (optional)

If you want to build the exe locally on your Mac just to verify the spec parses, run:

```bash
pip install pyinstaller
python make_icons.py --no-build
pyinstaller --clean --noconfirm HarvestHero.spec
```

You'll get `dist/HarvestHero/` — but on macOS it's a Mac executable, not a Windows one. Cross-building Windows exes from Mac is not supported by PyInstaller; that's why we let the CI runner do it.

> **Note:** Windows SmartScreen may warn on freshly published unsigned installers. Get a code-signing certificate to eliminate the warning — see [SIGNING.md](SIGNING.md).

---

## Sending the App to Someone

**Option A – Send the .exe (recommended)**

1. Build the `.exe` as above.
2. Send them `InventoryControlCenter.exe`.
3. They double-click it. That's it.
4. The database file (`inventory.db`) is created next to the `.exe` on first run.

**Option B – Send the Python source**

1. Zip the entire `inventory_tracker` folder.
2. The recipient must install Python 3.10+ and run `pip install -r requirements.txt`.
3. Then they run `python main.py`.

---

## File Structure

```
inventory_tracker/
│
├── input/                   # Drop CSV files here to bulk-import inventory
│   ├── README.md            # Column reference and instructions
│   └── inventory_template.csv
│
├── output/                  # All generated files land here
│   ├── backups/             # Timestamped database backups
│   ├── exports/             # CSV / Excel transaction exports
│   └── reports/             # Generated reports
│
├── data/                    # Database (created automatically)
│   └── inventory.db
│
├── main.py                  # App entry point
├── paths.py                 # Centralised folder constants
├── database.py              # SQLite logic
├── auth.py                  # Password hashing
├── ldap_auth.py             # LDAP / Active Directory integration
├── theme.py                 # Color themes (Harvest Hero, Luxury Dark, etc.)
├── requirements.txt         # Python dependencies
├── run.sh                   # Mac / Linux one-click launcher
├── run.bat                  # Windows one-click launcher
└── README.md                # This file
```

---

## Troubleshooting

### "python is not recognized"
- Make sure Python is installed and was added to PATH during setup.
- Try `py main.py` instead of `python main.py` on Windows.

### "ModuleNotFoundError: No module named 'customtkinter'"
- Run `pip install -r requirements.txt` again.
- If you have multiple Python versions, use `pip3` or `py -m pip`.

### The app opens and immediately closes
- Run from a terminal so you can see the error message:  
  ```
  python main.py
  ```

### Barcode scanner not working
- The barcode field must have focus (click on it once before scanning).
- Make sure the scanner is set to USB HID (keyboard emulation) mode – most are by default.
- Test the scanner in Notepad first. If it types there, it will work here.

### "inventory.db" is missing or corrupted
- Run `python setup_db.py` to recreate the database.  
  ⚠ This will **not** delete existing data if the database file already exists.
- If the file is genuinely corrupted, delete `inventory.db` and run `setup_db.py` again (data will be lost).

### Excel export does not work
- Install the optional dependency: `pip install openpyxl`

### PyInstaller .exe triggers antivirus
- This is a known false positive with PyInstaller. Add an exception in your antivirus for the file.

### The .exe can't find the database / crashes on startup
- Make sure `inventory.db` is in the **same folder** as the `.exe`.
- Do not move the `.exe` without also moving `inventory.db`.

---

## 📚 Documentation

### For Users
- **[QUICK_START.md](QUICK_START.md)** - 30-second setup and first steps
- **[INSTALLATION_GUIDE.md](INSTALLATION_GUIDE.md)** - Detailed installation for all platforms
- **[UPDATE_SYSTEM.md](UPDATE_SYSTEM.md)** - How automatic updates work

### For Developers
- **[PHASE_8_IMPLEMENTATION_SUMMARY.md](PHASE_8_IMPLEMENTATION_SUMMARY.md)** - Weight tracking system
- **[PHASE_9_UPDATE_SYSTEM_SUMMARY.md](PHASE_9_UPDATE_SYSTEM_SUMMARY.md)** - Update system implementation

### Getting Help
1. Check the relevant documentation above
2. Search [GitHub Issues](https://github.com/oclemons/HarvestHero/issues)
3. Create a new issue with details about your problem

---

## 🔄 Automatic Updates

The app automatically checks for updates on startup. If a new version is available:
1. A notification appears
2. Click "Install Update"
3. Download and installation happen automatically
4. App restarts with new version

See [UPDATE_SYSTEM.md](UPDATE_SYSTEM.md) for details.

---

*Built with Python · CustomTkinter · SQLite*
