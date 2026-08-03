# Harvest Hero — Pantry Intelligence Platform

A local desktop inventory management application built with Python, CustomTkinter, and SQLite.  
No internet connection required. All data is stored in `data/inventory.db` on the device where the app runs.

---

## Table of Contents

1. [Requirements](#requirements)
2. [Quick Start](#quick-start)
3. [Default Login](#default-login)
4. [Using a USB Barcode Scanner](#using-a-usb-barcode-scanner)
5. [Feature Guide](#feature-guide)
6. [Packaging into a Windows .exe](#packaging-into-a-windows-exe)
7. [Sending the App to Someone](#sending-the-app-to-someone)
8. [File Structure](#file-structure)
9. [Troubleshooting](#troubleshooting)

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

## Packaging into a Windows .exe

This lets you send the program to someone who does not have Python installed.

### Step 1 – Install PyInstaller

```
pip install pyinstaller
```

### Step 2 – Build the executable

Run this from inside the `inventory_tracker` folder:

```
pyinstaller --onefile --windowed --name "InventoryControlCenter" main.py
```

| Flag | Purpose |
|------|---------|
| `--onefile` | Bundle everything into a single `.exe` file |
| `--windowed` | Hide the terminal/console window |
| `--name` | Name of the output file |

### Step 3 – Find your .exe

After the build finishes, look in the `dist/` folder:

```
inventory_tracker/
  dist/
    InventoryControlCenter.exe   ← this is the file to send
```

### Step 4 – Test it

Double-click `InventoryControlCenter.exe`.  
On first launch it creates `inventory.db` in the same folder as the `.exe`.

> **Note:** Windows Defender or antivirus software may flag a freshly built `.exe`. This is a false positive common with PyInstaller. You can whitelist the file or use a code-signing certificate to prevent warnings.

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

*Built with Python · CustomTkinter · SQLite*
