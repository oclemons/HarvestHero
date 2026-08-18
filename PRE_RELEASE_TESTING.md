# Pre-Release Testing Checklist

**DO NOT RELEASE TO PRODUCTION WITHOUT COMPLETING ALL TESTS**

---

## 1. Database & Authentication Tests

### Test 1.1: Admin Login
- [ ] Start application
- [ ] Login with: admin / admin123
- [ ] ✅ Should login successfully
- [ ] ✅ Should see dashboard

### Test 1.2: Staff Login
- [ ] Create staff account: staff / password123
- [ ] Logout
- [ ] Login with staff credentials
- [ ] ✅ Should login successfully
- [ ] ✅ Should see staff dashboard (limited features)

### Test 1.3: Password Reset
- [ ] Click "Forgot Password?"
- [ ] Enter admin username
- [ ] ✅ Should receive email with reset link
- [ ] Click link and reset password
- [ ] ✅ Should be able to login with new password

### Test 1.4: Admin Password Management
- [ ] As admin, go to Admin → Users
- [ ] Create new user
- [ ] ✅ Should be able to set password
- [ ] Try as staff user
- [ ] ✅ Should NOT be able to change password

---

## 2. Inventory Management Tests

### Test 2.1: Add Item
- [ ] Click "Add Item"
- [ ] Fill in all fields:
  - Barcode: TEST001
  - Item Name: Test Item
  - Category: Test
  - Starting Quantity: 10
  - Minimum Stock: 5
  - Storage Location: Section 1, Shelf A
- [ ] Click "Add Item"
- [ ] ✅ Should see success message
- [ ] ✅ Item should appear in inventory list

### Test 2.2: Edit Item
- [ ] Double-click the item you just added
- [ ] Change item name to "Test Item Updated"
- [ ] Click "Save Changes"
- [ ] ✅ Should see success message
- [ ] ✅ Item name should update in list

### Test 2.3: Delete Item
- [ ] Right-click item
- [ ] Select "Delete"
- [ ] Confirm deletion
- [ ] ✅ Item should be removed from list

---

## 3. Shelf Management Tests

### Test 3.1: Create Shelf
- [ ] Go to Admin → Manage Shelves
- [ ] Click "Add Shelf"
- [ ] Select Section: Section 1
- [ ] Enter Shelf Name: Test Shelf
- [ ] Click "Add"
- [ ] ✅ Should see success message
- [ ] ✅ Shelf should appear in list
- [ ] ✅ Check command prompt for debug messages (should show ✅ SHELF CREATED SUCCESSFULLY!)

### Test 3.2: Storage Location Sync
- [ ] Keep Manage Shelves open
- [ ] Open Add Item in another window
- [ ] Add item with storage location: Section 1, New Shelf
- [ ] ✅ Within 2 seconds, new shelf should appear in Manage Shelves
- [ ] ✅ No need to manually refresh

### Test 3.3: Delete Shelf
- [ ] In Manage Shelves, find an empty shelf
- [ ] Click "Delete" button
- [ ] Confirm deletion
- [ ] ✅ Shelf should be removed

---

## 4. Barcode Scanning Tests

### Test 4.1: Manual Barcode Entry
- [ ] On Dashboard, click Barcode field
- [ ] Type: TEST001
- [ ] Press Enter
- [ ] ✅ Should find the item
- [ ] ✅ Item details should appear

### Test 4.2: Scan In
- [ ] Enter quantity: 5
- [ ] Click "Scan In"
- [ ] ✅ Should see success message
- [ ] ✅ Quantity should increase by 5

### Test 4.3: Scan Out
- [ ] Enter quantity: 2
- [ ] Enter recipient: John Doe
- [ ] Click "Scan Out"
- [ ] ✅ Should see success message
- [ ] ✅ Quantity should decrease by 2

---

## 5. Shopping List Tests

### Test 5.1: Auto Low-Stock Detection
- [ ] Add item with:
  - Current Quantity: 3
  - Minimum Stock: 10
- [ ] ✅ Item should automatically appear in Shopping List
- [ ] ✅ Quantity needed should be 7 (10 - 3)

### Test 5.2: Manual Sync
- [ ] Go to Shopping List
- [ ] Click "Generate Low Stock"
- [ ] ✅ Should show all low-stock items
- [ ] ✅ Should not show items above minimum

### Test 5.3: Remove from Shopping List
- [ ] In Shopping List, click delete on an item
- [ ] ✅ Item should be removed
- [ ] ✅ Should not reappear until item is low again

---

## 6. Dashboard Tests

### Test 6.1: Dashboard Widgets
- [ ] Go to Dashboard
- [ ] ✅ Should see KPI widgets:
  - Client Visits (this month)
  - Pounds Received
  - Current Inventory
  - Discarded Pounds

### Test 6.2: Dashboard Stats
- [ ] Add some transactions
- [ ] ✅ Dashboard should update
- [ ] ✅ Stats should be accurate

---

## 7. Reports Tests

### Test 7.1: Generate Report
- [ ] Go to Reports
- [ ] Select a report type
- [ ] Click "Generate"
- [ ] ✅ Should generate without errors
- [ ] ✅ Should show accurate data

### Test 7.2: Export Report
- [ ] In report, click "Export to Excel"
- [ ] ✅ Should download Excel file
- [ ] ✅ File should contain correct data

---

## 8. Multi-User Tests

### Test 8.1: Concurrent Access
- [ ] Login as admin in one window
- [ ] Login as staff in another window
- [ ] Make changes in both
- [ ] ✅ Both should work without conflicts
- [ ] ✅ Changes should sync properly

### Test 8.2: Role-Based Access
- [ ] As staff, try to:
  - [ ] Add item (should work)
  - [ ] Edit item (should work)
  - [ ] Delete item (should NOT work)
  - [ ] Manage users (should NOT work)
  - [ ] Manage shelves (should NOT work)

---

## 9. Data Persistence Tests

### Test 9.1: Data Survives Restart
- [ ] Add an item
- [ ] Close application
- [ ] Restart application
- [ ] ✅ Item should still be there
- [ ] ✅ All data should be intact

### Test 9.2: Database Backup
- [ ] Check that data folder exists
- [ ] ✅ Should contain inventory.db
- [ ] ✅ Database should be readable

---

## 10. Performance Tests

### Test 10.1: Large Dataset
- [ ] Add 100+ items to inventory
- [ ] ✅ Should load quickly (< 2 seconds)
- [ ] ✅ Search should work smoothly
- [ ] ✅ No lag or freezing

### Test 10.2: Report Generation
- [ ] Generate report with 100+ items
- [ ] ✅ Should complete in < 5 seconds
- [ ] ✅ Should not freeze UI

---

## 11. Error Handling Tests

### Test 11.1: Invalid Input
- [ ] Try to add item with empty name
- [ ] ✅ Should show error message
- [ ] ✅ Should not crash

### Test 11.2: Duplicate Barcode
- [ ] Try to add item with existing barcode
- [ ] ✅ Should show error message
- [ ] ✅ Should not crash

### Test 11.3: Database Error Recovery
- [ ] Manually corrupt database (if possible)
- [ ] Restart application
- [ ] ✅ Should handle gracefully
- [ ] ✅ Should show error message

---

## 12. UI/UX Tests

### Test 12.1: Navigation
- [ ] Test all menu items
- [ ] ✅ All should work
- [ ] ✅ No broken links

### Test 12.2: Responsive Design
- [ ] Resize window
- [ ] ✅ UI should adapt
- [ ] ✅ No overlapping elements

### Test 12.3: Accessibility
- [ ] Test keyboard navigation
- [ ] ✅ Should be able to navigate without mouse
- [ ] ✅ Tab order should be logical

---

## 13. Security Tests

### Test 13.1: Password Security
- [ ] Check that passwords are hashed
- [ ] ✅ Should NOT see plain text passwords in database

### Test 13.2: Access Control
- [ ] Try to access admin features as staff
- [ ] ✅ Should be denied
- [ ] ✅ Should show permission error

### Test 13.3: Session Management
- [ ] Login as user
- [ ] Close browser/window
- [ ] Reopen application
- [ ] ✅ Should require login again

---

## 14. Update System Tests

### Test 14.1: Check for Updates
- [ ] Start application
- [ ] ✅ Should check GitHub for updates
- [ ] ✅ Should show notification if update available

### Test 14.2: Update Installation
- [ ] If update available, click "Update"
- [ ] ✅ Should download files
- [ ] ✅ Should restart with new version

---

## 15. Client Device Tests

### Test 15.1: Fresh Installation
- [ ] On a clean Windows machine:
  - [ ] Download application
  - [ ] Install Python
  - [ ] Install dependencies
  - [ ] Run application
- [ ] ✅ Should work without errors

### Test 15.2: Desktop Shortcut
- [ ] Create desktop shortcut
- [ ] Double-click shortcut
- [ ] ✅ Should launch application
- [ ] ✅ Should not require command prompt

---

## Test Results Summary

| Test Category | Status | Notes |
|---|---|---|
| Database & Auth | ⬜ | |
| Inventory Mgmt | ⬜ | |
| Shelf Mgmt | ⬜ | |
| Barcode Scanning | ⬜ | |
| Shopping List | ⬜ | |
| Dashboard | ⬜ | |
| Reports | ⬜ | |
| Multi-User | ⬜ | |
| Data Persistence | ⬜ | |
| Performance | ⬜ | |
| Error Handling | ⬜ | |
| UI/UX | ⬜ | |
| Security | ⬜ | |
| Update System | ⬜ | |
| Client Device | ⬜ | |

---

## Sign-Off

**Tested By:** _______________  
**Date:** _______________  
**All Tests Passed:** ☐ YES ☐ NO  

**If NO, list failures:**
```
1. 
2. 
3. 
```

**Approved for Production:** ☐ YES ☐ NO  

---

## Notes

- Run all tests on a clean system
- Test on Windows (primary platform)
- Test with multiple users if possible
- Document any issues found
- Do NOT release if any critical tests fail
- Critical tests: Auth, Inventory, Shelf, Data Persistence

---

**REMEMBER: Do not release to production without completing ALL tests!**
