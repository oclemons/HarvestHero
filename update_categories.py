"""
update_categories.py — Update all inventory items with proper packaging-type categories.

This script analyzes each item name and assigns the correct packaging type category:
- Canned Item
- Boxed Item
- Bagged Item
- Jarred Item
- Bottled Item
- Dry Item
- Fresh Item
"""

from database import Database


def get_packaging_category(item_name: str) -> str:
    """Determine packaging type category from item name."""
    if not item_name:
        return "Uncategorized"
    
    item_lower = item_name.lower()
    
    # Packaging type keywords
    packaging_keywords = {
        "Canned Item": ["can", "canned", "tin", "soup", "stew", "chili", "ravioli"],
        "Boxed Item": ["box", "boxed", "mac & cheese", "helper", "meal", "ramen"],
        "Bagged Item": ["bag", "bagged", "cereal", "chips", "crackers", "snack", "flakes"],
        "Jarred Item": ["jar", "jarred", "peanut butter", "jelly", "sauce"],
        "Bottled Item": ["bottle", "bottled", "drink", "juice", "milk"],
        "Dry Item": ["dry", "dried", "bean", "lentil", "rice", "grain", "oatmeal", "grits", "pasta", "noodle"],
        "Fresh Item": ["fresh", "produce", "vegetable", "fruit"],
    }
    
    # Check packaging type
    for category, keywords in packaging_keywords.items():
        for keyword in keywords:
            if keyword in item_lower:
                return category
    
    return "Uncategorized"


def main():
    """Update all inventory items with proper categories."""
    db = Database()
    
    try:
        # Get all items
        items = db.get_all_items()
        print(f"Found {len(items)} items to update\n")
        
        # Update each item
        updated = 0
        for item in items:
            item_id = item.get('id')
            item_name = item.get('item_name', '')
            old_category = item.get('category', '')
            
            # Get new category
            new_category = get_packaging_category(item_name)
            
            # Update if different
            if old_category != new_category:
                conn = db._connect()
                conn.execute(
                    "UPDATE inventory_items SET category = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
                    (new_category, item_id)
                )
                conn.commit()
                conn.close()
                
                print(f"✓ {item_name:40} | {old_category:20} → {new_category}")
                updated += 1
            else:
                print(f"- {item_name:40} | Already: {new_category}")
        
        print(f"\n✅ Updated {updated} items")
        print(f"✅ All items now have proper packaging-type categories")
        
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()
