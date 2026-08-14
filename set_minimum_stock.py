#!/usr/bin/env python3
"""set_minimum_stock.py — Utility to set default minimum stock values for items.

This script sets intelligent default minimum stock thresholds based on item category.
Run this once to initialize minimum stock values for all items.
"""

import sqlite3
import os

# Default minimum stock values by category
DEFAULT_MINIMUMS = {
    "Canned Item": 20,      # High turnover, keep well-stocked
    "Dry Item": 15,         # Staple items
    "Boxed Item": 15,       # Common items
    "Bagged Item": 12,      # Moderate turnover
    "Bottled Item": 10,     # Beverages, moderate
    "Jarred Item": 8,       # Less common
    "Fresh Item": 5,        # Low stock (perishable)
    "Uncategorized": 10,    # Default
}

def set_minimum_stock():
    """Set minimum stock values for all items."""
    db_path = os.path.join(os.path.dirname(__file__), "data", "inventory.db")
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all items grouped by category
        cursor.execute("SELECT DISTINCT category FROM inventory_items ORDER BY category")
        categories = [row[0] for row in cursor.fetchall()]
        
        total_updated = 0
        
        for category in categories:
            minimum = DEFAULT_MINIMUMS.get(category, 10)
            
            # Update items in this category that don't have a minimum set
            cursor.execute(
                """UPDATE inventory_items 
                   SET minimum_stock = ? 
                   WHERE category = ? AND minimum_stock = 0""",
                (minimum, category)
            )
            
            updated = cursor.rowcount
            total_updated += updated
            
            if updated > 0:
                print(f"✓ {category}: Set {updated} items to minimum {minimum}")
            else:
                print(f"- {category}: No items to update")
        
        conn.commit()
        conn.close()
        
        print(f"\n✓ Successfully updated {total_updated} items with minimum stock values!")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Setting default minimum stock values...\n")
    success = set_minimum_stock()
    exit(0 if success else 1)
