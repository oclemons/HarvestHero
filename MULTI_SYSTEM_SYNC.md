# Multi-System Synchronization Guide

## Overview

Harvest Hero is designed to work across multiple systems (Windows, macOS, Linux) while keeping all data synchronized in real-time. This guide explains how the sync system works and how to deploy it across multiple locations.

## Architecture

### Single Database Model (Recommended for LAN)

All systems connect to a **single shared database** on a central server:

```
┌─────────────────────────────────────────────────┐
│         Central Database Server                  │
│  (SQLite on network share or dedicated server)   │
└─────────────────────────────────────────────────┘
         ↑              ↑              ↑
         │              │              │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    │ System 1 │    │ System 2 │    │ System 3 │
    │(Windows) │    │(Windows) │    │(macOS)   │
    └──────────┘    └──────────┘    └──────────┘
```

**Benefits:**
- ✅ Real-time synchronization
- ✅ Single source of truth
- ✅ No conflicts or merge issues
- ✅ Instant updates across all systems
- ✅ Easy backup and recovery

**Requirements:**
- Network file share (SMB/CIFS) or dedicated database server
- All systems on same LAN
- Consistent network connectivity

### How It Works

1. **Database Location**: The SQLite database is stored on a shared network location
2. **Connection**: Each system connects to the same database file
3. **Real-Time Updates**: Changes made on one system appear instantly on others
4. **Locking**: SQLite handles concurrent access with file-level locking
5. **No Sync Needed**: All systems read/write to the same data

## Setup Instructions

### Step 1: Choose Database Location

#### Option A: Network File Share (SMB/CIFS)

**Windows:**
```
\\server\shared\inventory.db
```

**macOS/Linux:**
```
/Volumes/shared/inventory.db
or
smb://server/shared/inventory.db
```

#### Option B: Dedicated Database Server

Use a lightweight database server like:
- PostgreSQL (with Flask API)
- MySQL (with Flask API)
- SQLite on NAS device

### Step 2: Configure Database Path

Edit `paths.py` on each system:

```python
# paths.py
import os

# For network share
DB_PATH = "/Volumes/shared/inventory.db"  # macOS
# or
DB_PATH = "\\\\server\\shared\\inventory.db"  # Windows

# For dedicated server (requires API)
DB_PATH = "http://server:5000/api/db"
```

### Step 3: Deploy Application

1. **Install on each system:**
   ```bash
   # macOS/Linux
   bash build_release.sh
   
   # Windows
   build_release.bat
   ```

2. **Configure database path** in `paths.py` on each system

3. **Test connection:**
   - Launch application
   - Create a test client
   - Check if it appears on other systems
   - Verify in real-time

### Step 4: Network Configuration

**Ensure all systems can access the shared database:**

```bash
# Test network connectivity
ping server
ls /Volumes/shared  # macOS
dir \\server\shared  # Windows

# Test database access
python -c "import sqlite3; conn = sqlite3.connect('/path/to/shared/inventory.db'); print('✓ Connected')"
```

## Real-Time Synchronization

### How Changes Sync

1. **User Action** (System 1)
   - Scan item → Inventory updated
   - Record visit → Client history updated

2. **Database Write** (System 1)
   - Changes written to shared database
   - File locked during write
   - Lock released after commit

3. **Automatic Refresh** (All Systems)
   - Other systems detect file change
   - Reload data from database
   - UI updates automatically

### Refresh Mechanisms

The application uses multiple refresh strategies:

**1. Manual Refresh**
- User clicks "Refresh" button
- Reloads data from database

**2. Auto-Refresh on Tab Switch**
- When switching tabs, data reloads
- Ensures latest data is displayed

**3. Periodic Polling** (Optional)
- Background thread checks for changes
- Updates UI if data changed
- Can be configured in `app_window.py`

### Sync Latency

- **Same System**: Instant (< 100ms)
- **LAN Network**: < 500ms
- **WAN Network**: 1-5 seconds (not recommended)

## Data Consistency

### Conflict Prevention

SQLite prevents conflicts through:
- **File-level locking**: Only one writer at a time
- **Transaction isolation**: Changes are atomic
- **ACID compliance**: Data integrity guaranteed

### Best Practices

1. **Don't edit database directly**
   - Always use the application
   - Prevents corruption

2. **Ensure network stability**
   - Use wired connections when possible
   - Avoid wireless for critical operations

3. **Regular backups**
   - Backup shared database daily
   - Keep 7-day rotation
   - Test restore procedures

4. **Monitor database size**
   - SQLite works best < 1GB
   - Archive old data periodically
   - Use cleanup tools if needed

## Backup & Recovery

### Automated Backup

Create a backup script:

```bash
#!/bin/bash
# backup_inventory.sh

BACKUP_DIR="/path/to/backups"
DB_PATH="/Volumes/shared/inventory.db"
DATE=$(date +%Y%m%d_%H%M%S)

cp "$DB_PATH" "$BACKUP_DIR/inventory_$DATE.db"

# Keep only last 7 days
find "$BACKUP_DIR" -name "inventory_*.db" -mtime +7 -delete
```

### Recovery Procedure

1. **Stop all applications** on all systems
2. **Restore database** from backup:
   ```bash
   cp /path/to/backup/inventory_YYYYMMDD.db /Volumes/shared/inventory.db
   ```
3. **Restart applications** on all systems
4. **Verify data** integrity

## Troubleshooting

### Issue: Changes not syncing

**Solution:**
1. Check network connectivity
2. Verify database path is correct
3. Ensure file permissions allow read/write
4. Click "Refresh" button manually
5. Restart application

### Issue: Database locked error

**Solution:**
1. Wait 30 seconds (lock timeout)
2. Check if another system is writing
3. Restart application
4. If persistent, restore from backup

### Issue: Slow performance

**Solution:**
1. Check network latency: `ping server`
2. Move database to faster network
3. Use wired connection instead of wireless
4. Archive old data to reduce database size

### Issue: File permission denied

**Solution:**
1. Check folder permissions:
   ```bash
   ls -la /Volumes/shared/
   ```
2. Ensure user has read/write access
3. On Windows, check SMB share permissions
4. Add user to appropriate group

## Advanced: API-Based Sync

For WAN deployments or cloud sync, use Flask API:

```python
# server.py (on central server)
from flask import Flask, jsonify
import sqlite3

app = Flask(__name__)

@app.route('/api/items', methods=['GET'])
def get_items():
    conn = sqlite3.connect('/path/to/inventory.db')
    items = conn.execute("SELECT * FROM inventory_items").fetchall()
    conn.close()
    return jsonify(items)

@app.route('/api/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    # Update logic here
    pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

Then configure client to use API:

```python
# api_client.py
class ApiClient:
    def __init__(self, server_url):
        self.server_url = server_url
    
    def get_items(self):
        response = requests.get(f"{self.server_url}/api/items")
        return response.json()
```

## Deployment Checklist

- [ ] Choose database location (shared drive or server)
- [ ] Set up network share or database server
- [ ] Configure `paths.py` on each system
- [ ] Test database connectivity from each system
- [ ] Deploy application to each system
- [ ] Test real-time sync (add item on System 1, verify on System 2)
- [ ] Set up automated backups
- [ ] Document database location and credentials
- [ ] Train staff on multi-system workflow
- [ ] Monitor for sync issues in first week

## Support & Maintenance

### Regular Maintenance

- **Weekly**: Check database file size
- **Monthly**: Verify backups are working
- **Quarterly**: Archive old data
- **Annually**: Review and optimize database

### Monitoring

Monitor these metrics:

```bash
# Database size
du -h /Volumes/shared/inventory.db

# File access logs
tail -f /var/log/smb.log  # macOS/Linux

# Network latency
ping -c 5 server
```

## Summary

The Harvest Hero application is designed to work seamlessly across multiple systems by using a **single shared database**. All changes sync in real-time across all connected systems, ensuring data consistency and eliminating manual sync procedures.

For most deployments (LAN with 2-10 systems), the shared database approach is ideal. For larger deployments or WAN scenarios, consider the API-based approach with a dedicated database server.

---

**Questions?** Check the main README.md or contact support at https://devin.ai/support
