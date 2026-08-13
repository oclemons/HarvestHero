"""
cleanup_duplicates.py — Remove duplicate inventory entries.

Identifies and removes duplicate items, keeping the most recent entry
and combining quantities.
"""

import sqlite3
from pathlib import Path
from datetime import datetime


def cleanup_duplicates(db_path: str = None):
    """Clean up duplicate inventory entries.
    
    Args:
        db_path: Path to inventory database
    """
    if db_path is None:
        db_path = Path(__file__).parent / "data" / "inventory.db"
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("🔍 Scanning for duplicate entries...")
    
    # Find duplicates
    cursor.execute("""
        SELECT LOWER(item_name) as item_lower, item_name, COUNT(*) as count, GROUP_CONCAT(id) as ids
        FROM inventory_items
        GROUP BY LOWER(item_name)
        HAVING count > 1
        ORDER BY count DESC
    """)
    
    duplicates = cursor.fetchall()
    print(f"Found {len(duplicates)} items with duplicates\n")
    
    total_removed = 0
    
    for dup in duplicates:
        item_name = dup['item_name']
        count = dup['count']
        ids = [int(x) for x in dup['ids'].split(',')]
        
        print(f"Processing: {item_name} ({count} entries)")
        
        # Get all entries for this item
        cursor.execute("""
            SELECT id, item_name, current_quantity, created_at
            FROM inventory_items
            WHERE LOWER(item_name) = LOWER(?)
            ORDER BY created_at DESC
        """, (item_name,))
        
        entries = cursor.fetchall()
        
        # Keep the first (most recent), remove the rest
        keep_id = entries[0]['id']
        keep_qty = entries[0]['current_quantity']
        
        # Sum quantities from all entries
        total_qty = sum(e['current_quantity'] for e in entries)
        
        print(f"  Keeping: ID {keep_id} (Qty: {keep_qty})")
        print(f"  Total quantity: {total_qty}")
        
        # Update the kept entry with total quantity
        cursor.execute("""
            UPDATE inventory_items
            SET current_quantity = ?
            WHERE id = ?
        """, (total_qty, keep_id))
        
        # Remove duplicates
        for entry in entries[1:]:
            dup_id = entry['id']
            dup_qty = entry['current_quantity']
            print(f"  Removing: ID {dup_id} (Qty: {dup_qty})")
            
            cursor.execute("DELETE FROM inventory_items WHERE id = ?", (dup_id,))
            total_removed += 1
        
        print()
    
    conn.commit()
    
    print(f"✅ Cleanup complete!")
    print(f"   Removed {total_removed} duplicate entries")
    print(f"   Remaining items: {get_item_count(cursor)}")
    
    conn.close()


def get_item_count(cursor) -> int:
    """Get total count of items."""
    cursor.execute("SELECT COUNT(*) as count FROM inventory_items")
    return cursor.fetchone()['count']


def verify_cleanup(db_path: str = None):
    """Verify that duplicates have been removed.
    
    Args:
        db_path: Path to inventory database
    """
    if db_path is None:
        db_path = Path(__file__).parent / "data" / "inventory.db"
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("\n🔍 Verifying cleanup...")
    
    cursor.execute("""
        SELECT LOWER(item_name) as item_lower, COUNT(*) as count
        FROM inventory_items
        GROUP BY LOWER(item_name)
        HAVING count > 1
    """)
    
    remaining = cursor.fetchall()
    
    if remaining:
        print(f"⚠️  Still found {len(remaining)} items with duplicates:")
        for item in remaining:
            print(f"   {item['item_lower']}: {item['count']} entries")
    else:
        print("✅ No duplicates found! Database is clean.")
    
    # Show total items
    cursor.execute("SELECT COUNT(*) as count FROM inventory_items")
    total = cursor.fetchone()['count']
    print(f"\nTotal items in inventory: {total}")
    
    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("INVENTORY DUPLICATE CLEANUP")
    print("=" * 60)
    print()
    
    # Run cleanup
    cleanup_duplicates()
    
    # Verify
    verify_cleanup()
    
    print("\n" + "=" * 60)
    print("Cleanup finished!")
    print("=" * 60)
