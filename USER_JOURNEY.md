# User Journey - From GitHub Link to Using the App

## Complete Step-by-Step Guide

This guide walks through the entire process of getting the app from GitHub and using it.

---

## Step 1: Get the GitHub Link

**You provide**: https://github.com/oclemons/HarvestHero

**User receives**: GitHub repository link

---

## Step 2: Download the App

### Option A: Windows Users (Easiest)

1. **Open the link**
   - Click: https://github.com/oclemons/HarvestHero
   - Or paste in browser

2. **Go to Releases**
   - Click "Releases" on the right side
   - Or go to: https://github.com/oclemons/HarvestHero/releases

3. **Download the .exe**
   - Look for latest release (e.g., "v2.0.0")
   - Click on `.exe` file (e.g., `HarvestHero-v2.0.0.exe`)
   - File downloads to Downloads folder

4. **Move to desired location** (Optional)
   - Cut/paste to Desktop or Program Files
   - Or leave in Downloads

### Option B: Mac/Linux Users

1. **Open the link**
   - Click: https://github.com/oclemons/HarvestHero
   - Or paste in browser

2. **Go to Releases**
   - Click "Releases" on the right side
   - Or go to: https://github.com/oclemons/HarvestHero/releases

3. **Download Source Code**
   - Click "Source code (zip)" under latest release
   - File downloads to Downloads folder

4. **Extract the ZIP**
   - Double-click the ZIP file
   - Folder extracts to Downloads

---

## Step 3: Run the Application

### Windows Users

1. **Double-click the .exe file**
   - File: `HarvestHero-v2.0.0.exe`
   - Location: Downloads or wherever you saved it

2. **Windows Security Warning** (May appear)
   - Click "More info"
   - Click "Run anyway"
   - Or click "Run" if prompted

3. **App launches**
   - Login screen appears
   - Wait a few seconds for full load

### Mac Users

1. **Open Terminal**
   - Applications → Utilities → Terminal
   - Or press Cmd+Space, type "Terminal", press Enter

2. **Navigate to folder**
   ```bash
   cd ~/Downloads/HarvestHero-main
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   python main.py
   ```

5. **App launches**
   - Login screen appears

### Linux Users

1. **Open Terminal**
   - Applications → Accessories → Terminal
   - Or press Ctrl+Alt+T

2. **Navigate to folder**
   ```bash
   cd ~/Downloads/HarvestHero-main
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   python main.py
   ```

5. **App launches**
   - Login screen appears

---

## Step 4: First Login

### Default Credentials

**Username**: `admin`
**Password**: (shown in popup on first launch)

### Login Steps

1. **App shows login screen**
2. **Popup appears** with default password
   - Write down the password
   - Or copy to clipboard
3. **Enter username**: `admin`
4. **Enter password**: (from popup)
5. **Click Login**
6. **App opens to Dashboard**

---

## Step 5: First-Time Setup

### Change Admin Password (IMPORTANT!)

1. **Click Admin** in left sidebar
2. **Click User Management**
3. **Find "admin" user**
4. **Click Edit**
5. **Enter new password**
   - Use strong password (12+ characters)
   - Include uppercase, lowercase, numbers, symbols
6. **Click Save**
7. **New password is active**

### Create Staff Accounts

1. **Still in User Management**
2. **Click + Add User**
3. **Enter username** (e.g., "john_intake")
4. **Enter password** (strong password)
5. **Select role**: **Staff**
   - Staff can only scan items in
   - Staff cannot edit inventory
   - Staff cannot see client info
6. **Click Create User**
7. **Repeat for each staff member**

### Set Organization Name

1. **Click Settings** in left sidebar
2. **Enter Organization Name**
   - Your pantry/organization name
3. **Click Save**

---

## Step 6: Add Inventory Items

### Option A: Add Items Manually

1. **Click Inventory** in left sidebar
2. **Click + Add Item**
3. **Enter item details**:
   - Scan-In Barcode (required)
   - Item Name (required)
   - Category (optional)
   - Starting Quantity
   - Minimum Stock
   - Notes (optional)
4. **Click Add Item**
5. **Repeat for each item**

### Option B: Import from CSV

1. **Click Inventory**
2. **Click Import CSV**
3. **Select CSV file** with item data
4. **Items imported automatically**

### Option C: Bulk Import Barcodes

1. **Click Inventory**
2. **Click Bulk Import**
3. **Upload CSV or paste data**
4. **Barcodes imported automatically**

---

## Step 7: Start Using the App

### Scan Items In (Receiving)

1. **Click Intake** in left sidebar
2. **Make sure SCAN_IN is selected**
3. **Click in Barcode field**
4. **Scan item** (or type barcode)
5. **Enter quantity**
6. **Click Add to Cart**
7. **Repeat for more items**
8. **Click Complete Transaction**
9. **Items added to inventory**

### Scan Items Out (Distribution)

**Note**: Only admins can do this. Staff cannot.

1. **Click Intake**
2. **Select SCAN_OUT mode**
3. **Select client** from dropdown
4. **Click in Barcode field**
5. **Scan items** (or type barcodes)
6. **Enter quantities**
7. **Add to cart**
8. **Enter total pounds** (optional)
9. **Click Complete Transaction**
10. **Distribution recorded**

### View Inventory

1. **Click Inventory**
2. **See all items** in table
3. **Search** for specific item
4. **Edit** item details
5. **View** storage location
6. **Check** current quantity

### Generate Reports

1. **Click Reports**
2. **Select report type**:
   - Dashboard Metrics
   - Current Inventory
   - Low Stock
   - Out of Stock
   - Scan In History
   - Scan Out History
   - Recipient History
3. **Click Export CSV** or **Export Excel**
4. **Save file** to computer

### Track Weights

1. **Click Weights** (admin only)
2. **Select item**
3. **Click Edit**
4. **Enter current pounds**
5. **Enter donated pounds**
6. **Enter discarded pounds**
7. **View calculated remaining**
8. **Click Save**

### Backup Data

1. **Click Settings**
2. **Click Backup Database Now**
3. **Save file** to safe location
4. **Store backup** in multiple places

---

## Step 8: Automatic Updates

### Update Notification

1. **App launches**
2. **Checks GitHub** for new version
3. **If update available**:
   - Notification dialog appears
   - Shows version number
   - Shows release notes

### Install Update

1. **Click Install Update**
2. **Download begins**
   - Progress bar shows download
3. **Installation happens**
   - Files extracted
   - New files copied
   - Version updated
4. **App restarts**
   - New version running
5. **No manual intervention needed**

---

## Step 9: Daily Operations

### Morning Routine

1. **Launch app**
2. **Check for updates** (automatic)
3. **Review Dashboard**
   - Check inventory status
   - See low stock items
4. **Check Shopping List**
   - See items to order

### During Day

1. **Scan items in** (receiving)
2. **Scan items out** (distribution)
3. **Update weights** (if needed)
4. **Check inventory** as needed

### End of Day

1. **Review transactions**
2. **Backup data** (daily recommended)
3. **Close app**

### Weekly

1. **Generate reports**
2. **Review inventory levels**
3. **Plan orders**
4. **Check for updates**

### Monthly

1. **Generate monthly weight report**
2. **Archive old data**
3. **Review statistics**
4. **Plan for next month**

---

## Step 10: Troubleshooting

### App Won't Start

**Problem**: Double-clicking .exe does nothing

**Solution**:
1. Right-click .exe
2. Select "Run as administrator"
3. Try again

### Can't Login

**Problem**: Username/password not working

**Solution**:
1. Check caps lock
2. Verify password is correct
3. If forgotten, delete database and reinstall

### Barcode Won't Scan

**Problem**: Scanner doesn't work

**Solution**:
1. Click in barcode field first
2. Try typing manually
3. Check barcode format in database
4. Test scanner in Notepad first

### Data Not Saving

**Problem**: Changes disappear

**Solution**:
1. Check disk space
2. Check folder permissions
3. Restart app
4. Restore from backup if needed

### Update Won't Install

**Problem**: Update fails

**Solution**:
1. Check internet connection
2. Check disk space (need 500 MB)
3. Try manual download
4. Contact support

---

## Getting Help

### Documentation
- **Quick Start**: QUICK_START.md
- **Installation**: INSTALLATION_GUIDE.md
- **Updates**: UPDATE_SYSTEM.md
- **This Guide**: USER_JOURNEY.md

### Online Resources
- GitHub: https://github.com/oclemons/HarvestHero
- Issues: https://github.com/oclemons/HarvestHero/issues

### Contact Support
- Email: (your email)
- Phone: (your phone)
- Hours: (your hours)

---

## Key Takeaways

✅ **Download**: GitHub releases page
✅ **Install**: Double-click .exe (Windows) or run from source (Mac/Linux)
✅ **Login**: admin / (password shown)
✅ **Setup**: Change password, create users, add items
✅ **Use**: Scan items, track inventory, generate reports
✅ **Updates**: Automatic, no manual intervention
✅ **Support**: Documentation and GitHub issues

---

## Quick Reference

| Task | Steps |
|------|-------|
| Download | GitHub → Releases → Download .exe |
| Install | Double-click .exe |
| Login | admin / (password shown) |
| Change Password | Admin → User Management → Edit |
| Add Item | Inventory → + Add Item |
| Scan In | Intake → Scan → Add to Cart → Complete |
| Scan Out | Intake → SCAN_OUT → Select Client → Complete |
| Report | Reports → Select Type → Export |
| Backup | Settings → Backup Database Now |
| Update | Click "Install Update" when prompted |

---

**Ready to get started?** Download now: https://github.com/oclemons/HarvestHero/releases

**Questions?** See INSTALLATION_GUIDE.md or contact support.

**Last Updated**: 2024-01-20
