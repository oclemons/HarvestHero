"""
fix_inventory.py — Fix inventory to match physical pantry layout.

1. Add missing items
2. Clean up items not in physical pantry
3. Standardize item names
"""

import sqlite3
from pathlib import Path


def fix_inventory(db_path: str = None):
    """Fix inventory to match physical pantry.
    
    Args:
        db_path: Path to inventory database
    """
    if db_path is None:
        db_path = Path(__file__).parent / "data" / "inventory.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("FIXING INVENTORY")
    print("=" * 80)
    print()
    
    # 1. Add missing item: Garbonzo / Chickpeas (dry)
    print("1. Adding missing item...")
    cursor.execute("""
        INSERT INTO inventory_items 
        (barcode, item_name, category, storage_location, current_quantity, minimum_stock)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "MISSING-GARBONZO",
        "Garbonzo / Chickpeas (dry)",
        "Beans & Legumes",
        "Section 9, Shelf 3c",
        0,
        0
    ))
    print("   ✅ Added: Garbonzo / Chickpeas (dry)")
    
    # 2. Remove items not in physical pantry
    print("\n2. Removing items not in physical pantry...")
    
    items_to_remove = [
        "Diapers",
        "Misc. Hygiene",
        "Misc. Products",
        "Hams",
    ]
    
    for item in items_to_remove:
        cursor.execute("DELETE FROM inventory_items WHERE LOWER(item_name) = LOWER(?)", (item,))
        print(f"   ✅ Removed: {item}")
    
    # 3. Standardize item names to match physical pantry
    print("\n3. Standardizing item names...")
    
    name_mappings = {
        "Baked goods": "Sweet baked goods",
        "Beef ramen": "Beef ramen noodles",
        "Black beans canned": "Black beans",
        "Black beans dry": "Black beans (dry)",
        "Breakfast drinks": "Breakfast drinks",
        "Chicken ramen": "Chicken ramen noodles",
        "Chickpeas dry": "Chickpeas",
        "Fruits": "Fruit",
        "Garbanzo / chickpeas (dry)": "Garbonzo / Chickpeas (dry)",
        "Lentils dry": "Lentils (dry)",
        "Mac & cheese": "Box mac & cheese",
        "Misc Vegetables": "Mixed vegetables",
        "Misc. Ramen": "Misc ramen noodles",
        "Mixed box meals": "Misc. Box meals",
        "Northern beans dry": "Northern beans (dry)",
        "Pinto beans dry": "Pinto beans (dry)",
        "Red kidney beans dry": "Red kidney beans (dry)",
        "Refried beans can": "Beans canned",
        "Snacks": "Snack",
        "Stuffing / Mashed potatoes": "Stuffing",
        "Sweet baked Goods": "Sweet baked goods",
        "beans canned": "Beans canned",
        "waffle / pancake mix": "Waffle / Pancake mix",
    }
    
    for old_name, new_name in name_mappings.items():
        cursor.execute(
            "UPDATE inventory_items SET item_name = ? WHERE LOWER(item_name) = LOWER(?)",
            (new_name, old_name)
        )
        print(f"   ✅ Renamed: {old_name} → {new_name}")
    
    conn.commit()
    
    print("\n" + "=" * 80)
    print("INVENTORY FIXED")
    print("=" * 80)
    
    conn.close()


if __name__ == "__main__":
    fix_inventory()
