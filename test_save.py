#!/usr/bin/env python3
"""test_save.py — Test if item edits are being saved to database."""

import sys
from database import Database

def test_save():
    """Test item saving."""
    try:
        db = Database()
        
        print("🔍 Testing Item Save Functionality")
        print("=" * 50)
        print()
        
        # Get first item
        items = db.get_all_items()
        if not items:
            print("❌ No items in database!")
            return False
        
        item = items[0]
        print(f"✅ Found item: {item['item_name']} (ID: {item['id']})")
        print(f"   Current name: {item['item_name']}")
        print(f"   Current category: {item['category']}")
        print(f"   Current notes: {item['notes']}")
        print()
        
        # Try to update the item
        new_name = f"{item['item_name']} [EDITED]"
        new_category = "TEST_CATEGORY"
        new_notes = "TEST_NOTES"
        
        print(f"Updating item...")
        print(f"   New name: {new_name}")
        print(f"   New category: {new_category}")
        print(f"   New notes: {new_notes}")
        print()
        
        db.update_item(
            item['id'],
            new_name,
            new_category,
            item['minimum_stock'],
            new_notes,
            item.get('barcode_out', '')
        )
        
        print("✅ Update executed")
        print()
        
        # Reload and check
        print("Reloading from database...")
        updated_item = db.get_item_by_id(item['id'])
        
        if not updated_item:
            print("❌ Item not found after update!")
            return False
        
        print(f"✅ Item reloaded")
        print(f"   Name: {updated_item['item_name']}")
        print(f"   Category: {updated_item['category']}")
        print(f"   Notes: {updated_item['notes']}")
        print()
        
        # Check if changes were saved
        if updated_item['item_name'] == new_name:
            print("✅ NAME SAVED CORRECTLY!")
        else:
            print(f"❌ NAME NOT SAVED! Expected '{new_name}', got '{updated_item['item_name']}'")
            return False
        
        if updated_item['category'] == new_category:
            print("✅ CATEGORY SAVED CORRECTLY!")
        else:
            print(f"❌ CATEGORY NOT SAVED! Expected '{new_category}', got '{updated_item['category']}'")
            return False
        
        if updated_item['notes'] == new_notes:
            print("✅ NOTES SAVED CORRECTLY!")
        else:
            print(f"❌ NOTES NOT SAVED! Expected '{new_notes}', got '{updated_item['notes']}'")
            return False
        
        print()
        print("=" * 50)
        print("✅ All tests passed! Database saving works correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_save()
    sys.exit(0 if success else 1)
