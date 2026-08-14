#!/usr/bin/env python3
"""test_shelf_creation.py — Test shelf creation functionality."""

import sys
from database import Database

def test_shelf_creation():
    """Test creating a shelf."""
    try:
        db = Database()
        
        print("🔍 Testing Shelf Creation")
        print("=" * 60)
        print()
        
        # Test data
        section = "Section 1"
        shelf_name = "Test Shelf"
        storage_location = f"{section}, {shelf_name}"
        placeholder_barcode = f"SHELF_Section_1_Test_Shelf"
        
        print(f"📝 Test Parameters:")
        print(f"   Section: {section}")
        print(f"   Shelf Name: {shelf_name}")
        print(f"   Storage Location: {storage_location}")
        print(f"   Barcode: {placeholder_barcode}")
        print()
        
        # Step 1: Check if shelf already exists
        print("Step 1: Checking if shelf already exists...")
        all_items = db.get_all_items()
        existing_count = sum(1 for item in all_items 
                            if item.get("storage_location") == storage_location)
        print(f"   Found {existing_count} items with this storage location")
        
        if existing_count > 0:
            print("   ⚠️  Shelf already exists, skipping creation")
            print()
        else:
            print("   ✅ Shelf does not exist, proceeding with creation")
            print()
            
            # Step 2: Create placeholder item
            print("Step 2: Creating placeholder item...")
            ok, msg = db.add_item(
                barcode=placeholder_barcode,
                item_name=f"[Shelf Marker] {storage_location}",
                category="System",
                quantity=0,
                minimum_stock=0,
                notes="This is a shelf marker item. Do not distribute.",
                barcode_out="",
                storage_location=storage_location
            )
            
            print(f"   Result: ok={ok}, msg={msg}")
            
            if not ok:
                print(f"   ❌ Failed to create shelf: {msg}")
                return False
            
            print(f"   ✅ Placeholder item created")
            print()
            
            # Step 3: Verify shelf was created
            print("Step 3: Verifying shelf was created...")
            all_items = db.get_all_items()
            verify_count = sum(1 for item in all_items 
                              if item.get("storage_location") == storage_location)
            
            print(f"   Found {verify_count} items with this storage location")
            
            if verify_count > 0:
                print(f"   ✅ Shelf created successfully!")
                
                # Show the created item
                for item in all_items:
                    if item.get("storage_location") == storage_location:
                        print()
                        print(f"   Created Item Details:")
                        print(f"   - ID: {item['id']}")
                        print(f"   - Barcode: {item['barcode']}")
                        print(f"   - Name: {item['item_name']}")
                        print(f"   - Category: {item['category']}")
                        print(f"   - Storage Location: {item['storage_location']}")
                        break
            else:
                print(f"   ❌ Shelf not found after creation!")
                return False
        
        print()
        print("=" * 60)
        print("✅ Shelf creation test PASSED!")
        print()
        print("The shelf creation system is working correctly.")
        print("Users should now be able to add shelves successfully.")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_shelf_creation()
    sys.exit(0 if success else 1)
