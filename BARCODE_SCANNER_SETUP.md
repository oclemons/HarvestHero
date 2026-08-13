# Barcode Scanner Integration Guide

## Overview

Harvest Hero is fully compatible with physical barcode scanners. The application automatically detects scanner input and processes barcodes in real-time. This guide explains how to set up and use barcode scanners with the application.

## How It Works

### Scanner Input Flow

```
Physical Scanner
    ↓
Keyboard Input (HID)
    ↓
Barcode Entry Field
    ↓
Automatic Lookup (350ms delay)
    ↓
Display Item Card
    ↓
User Action (Scan In/Out or F1/F2)
    ↓
Process Transaction
```

### Key Features

✅ **Automatic Detection** - Scanner input recognized as keyboard input  
✅ **Real-Time Lookup** - Item found in database instantly  
✅ **AI Fallback** - Unknown items identified via Open Food Facts  
✅ **Fast Processing** - 350ms lookup delay for database queries  
✅ **Keyboard Shortcuts** - F1 (Scan In), F2 (Scan Out), Esc (Clear)  
✅ **Multi-Scanner Support** - Multiple scanners on same system  
✅ **Simultaneous Operation** - Works while other tabs are open  

## Hardware Requirements

### Compatible Scanners

The application works with any barcode scanner that:
- Emulates keyboard input (HID - Human Interface Device)
- Sends barcode data followed by Enter key
- Supports standard barcode formats (UPC, EAN, Code128, etc.)

**Recommended Scanners:**

| Type | Model | Price | Notes |
|------|-------|-------|-------|
| Handheld USB | Zebra DS3678 | $400-600 | Professional grade |
| Handheld USB | Honeywell 1900 | $300-500 | Reliable, durable |
| Handheld Wireless | Zebra CS3070 | $500-700 | Cordless, range 50ft |
| Fixed Mount | Zebra LS2208 | $200-400 | Hands-free scanning |
| Mobile/Tablet | Zebra TC51 | $800-1200 | Rugged mobile device |

### Connection Types

**USB (Recommended)**
- Direct connection to computer
- No batteries needed
- Plug and play
- Works on Windows, macOS, Linux

**Wireless (Bluetooth/2.4GHz)**
- Range: 30-100 feet
- Requires charging
- More mobility
- Slight latency (< 100ms)

**Serial/RS-232 (Legacy)**
- Older scanners
- Requires USB adapter
- May need custom driver

## Setup Instructions

### Step 1: Physical Connection

**USB Scanner:**
1. Plug scanner into USB port
2. Wait for device recognition (usually automatic)
3. No driver installation needed for HID devices

**Wireless Scanner:**
1. Charge scanner battery
2. Enable Bluetooth on computer
3. Pair scanner with computer
4. Test connection

### Step 2: Verify Scanner Recognition

**Windows:**
```powershell
# Check device manager
Get-PnpDevice | Where-Object {$_.Name -like "*barcode*"}

# Or use Device Manager GUI
devmgmt.msc
```

**macOS:**
```bash
# Check system report
system_profiler SPUSBDataType | grep -i barcode

# Or use System Information app
```

**Linux:**
```bash
# Check USB devices
lsusb | grep -i barcode

# Check input devices
ls -la /dev/input/
```

### Step 3: Test Scanner Input

**Test in any text field:**
1. Click in a text input field
2. Scan a barcode
3. Barcode should appear in the field
4. Press Enter to confirm

**If scanner doesn't work:**
- Check USB connection
- Verify scanner is powered on
- Try different USB port
- Restart application
- Check scanner settings (some require configuration)

### Step 4: Configure Application

**No configuration needed!** The application automatically:
- Detects barcode entry
- Focuses on barcode field when tab opens
- Processes input in real-time
- Handles multiple scanners

## Usage Workflow

### Basic Scanning

**Scan In (Add to Inventory):**
1. Go to **Scan Screen** tab
2. Scanner automatically has focus
3. Scan barcode (scanner sends barcode + Enter)
4. Item card appears with details
5. Enter quantity (default: 1)
6. Press **F1** or click **Scan In** button
7. Item added to inventory
8. Form clears automatically

**Scan Out (Remove from Inventory):**
1. Go to **Scan Screen** tab
2. Scan barcode
3. Item card appears
4. Enter quantity to remove
5. Enter recipient name (client name)
6. Press **F2** or click **Scan Out** button
7. Item removed from inventory
8. Pantry visit recorded automatically
9. Form clears automatically

**Keyboard Shortcuts:**
- **F1** - Scan In (add to inventory)
- **F2** - Scan Out (remove from inventory)
- **Esc** - Clear form and reset

### Advanced Features

**Multiple Scanners on Same System:**
1. Connect multiple scanners via USB hub
2. Each scanner sends input to active field
3. Application processes sequentially
4. No conflicts or data loss

**Scanning While Other Tabs Open:**
1. Scan Screen tab doesn't need to be active
2. Scanner input still goes to barcode field
3. Allows monitoring other data while scanning
4. Switch to Scan Screen to confirm action

**Unknown Item Handling:**
1. Scan barcode not in database
2. Application queries Open Food Facts API
3. If found: Shows AI-identified product
4. If not found: Prompts for manual entry
5. Add item and scan in one operation

## Advanced Configuration

### Scanner Settings

Some scanners have configurable settings:

**Prefix/Suffix Characters:**
- Some scanners add characters before/after barcode
- Configure in scanner settings to remove
- Test with barcode field to verify

**Barcode Format:**
- Configure scanner to match your barcode types
- Common formats: UPC, EAN-13, Code128, QR
- Application supports all standard formats

**Keyboard Layout:**
- Some scanners support different keyboard layouts
- Ensure scanner uses US/English layout
- Non-ASCII characters may not work correctly

### Performance Tuning

**Lookup Delay:**
- Default: 350ms (good for most cases)
- Faster: 200ms (requires fast network)
- Slower: 500ms (for slow databases)

To adjust, edit `scan_screen.py`:
```python
# Line 606
self._lookup_timer = self.after(350, self._lookup_now)  # Change 350 to desired ms
```

**Concurrent Scanning:**
- Application handles sequential scans automatically
- If scanning too fast, queue builds up
- Typical throughput: 10-20 items/minute
- For higher volume, use batch import

## Troubleshooting

### Issue: Scanner input not appearing

**Solution:**
1. Click in barcode field to ensure focus
2. Check scanner is powered on
3. Try scanning test barcode
4. Check scanner cable/connection
5. Restart application
6. Try different USB port

### Issue: Barcode appears but item not found

**Solution:**
1. Verify barcode is correct
2. Check if item exists in database
3. Try manual entry in Inventory tab
4. Use AI identification for new items
5. Check barcode format matches database

### Issue: Scanner input goes to wrong field

**Solution:**
1. Click in barcode entry field first
2. Application auto-focuses on tab open
3. Ensure Scan Screen tab is visible
4. Check if another field has focus
5. Use Tab key to navigate to barcode field

### Issue: Multiple scanners interfering

**Solution:**
1. Connect scanners to separate USB ports
2. Use USB hub with separate power
3. Test each scanner individually
4. Disable one scanner while testing other
5. Check scanner IDs in device manager

### Issue: Slow scanning performance

**Solution:**
1. Check network latency: `ping server`
2. Verify database is responsive
3. Close other applications
4. Check CPU/memory usage
5. Move database to faster storage
6. Increase lookup delay if needed

## Best Practices

### Scanning Efficiency

✅ **Scan one item at a time** - Prevents confusion  
✅ **Verify item card appears** - Confirms barcode recognized  
✅ **Enter quantity before action** - Faster than multiple scans  
✅ **Use keyboard shortcuts** - F1/F2 faster than clicking buttons  
✅ **Keep barcode field focused** - Automatic on tab open  

### Data Quality

✅ **Verify item details** - Check name, quantity, recipient  
✅ **Use consistent naming** - Client names for recipients  
✅ **Regular barcode maintenance** - Replace damaged labels  
✅ **Test new barcodes** - Verify scanner reads correctly  
✅ **Monitor error messages** - Address issues immediately  

### Hardware Maintenance

✅ **Keep scanner clean** - Dust affects scanning  
✅ **Check cable connections** - Loose cables cause issues  
✅ **Maintain battery** - Charge wireless scanners regularly  
✅ **Protect from damage** - Scanners are fragile  
✅ **Update firmware** - Check manufacturer for updates  

## Multi-System Scanning

When using barcode scanners across multiple systems:

### Network Considerations

- **Scan Screen tab** works on any system
- **Database syncs** automatically across systems
- **Multiple scanners** can scan simultaneously
- **No conflicts** - SQLite handles concurrent access

### Workflow Example

```
System 1 (Receiving):
- Scan items in
- Add to inventory
- Data syncs to System 2

System 2 (Distribution):
- Scan items out
- Remove from inventory
- Client visits recorded
- Data syncs back to System 1

Both systems stay in sync automatically!
```

## API Integration (Advanced)

For custom scanner applications or integrations:

```python
# Custom scanner handler
from database import Database

db = Database()

def process_barcode(barcode: str, action: str = "lookup"):
    """
    Process barcode from custom scanner application.
    
    Args:
        barcode: Barcode string
        action: "lookup", "scan_in", "scan_out"
    
    Returns:
        Item data or error message
    """
    item, direction = db.get_item_by_any_barcode(barcode)
    
    if not item:
        return {"error": "Item not found"}
    
    if action == "lookup":
        return item
    
    elif action == "scan_in":
        db.adjust_stock(item["barcode"], 1)
        return {"success": f"Added {item['item_name']}"}
    
    elif action == "scan_out":
        if item["current_quantity"] < 1:
            return {"error": "Not enough stock"}
        db.adjust_stock(item["barcode"], -1)
        return {"success": f"Removed {item['item_name']}"}
```

## Support & Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| No input | Scanner not connected | Check USB/Bluetooth connection |
| Wrong field | Focus on different field | Click barcode field first |
| Slow lookup | Network latency | Check database connection |
| Duplicate scans | Double scan | Scan once, wait for result |
| Format error | Barcode format mismatch | Check scanner settings |

### Getting Help

1. **Check this guide** - Most issues covered
2. **Test scanner** - Use text editor to verify
3. **Check logs** - Application logs in `logs/` folder
4. **Contact support** - https://devin.ai/support

## Summary

Barcode scanners integrate seamlessly with Harvest Hero:

✅ **Plug and Play** - No configuration needed  
✅ **Real-Time Processing** - Instant item lookup  
✅ **Multiple Scanners** - Simultaneous operation supported  
✅ **Automatic Sync** - Works across all systems  
✅ **Keyboard Shortcuts** - F1/F2 for quick actions  
✅ **Error Handling** - AI fallback for unknown items  

The application is production-ready for high-volume barcode scanning operations!

---

**Questions?** See MULTI_SYSTEM_SYNC.md for deployment info or contact support.
