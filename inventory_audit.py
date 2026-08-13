"""
inventory_audit.py — Comprehensive inventory audit against physical pantry layout.

Verifies that all items from the physical pantry are in the database,
organized by section and shelf as documented.
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple


class InventoryAudit:
    """Audits inventory against physical pantry layout."""

    # Physical pantry layout from handwritten notes
    PHYSICAL_PANTRY = {
        "Section 1": {
            "Shelf 1": ["Sweet corn"],
            "Shelf 2": ["Whole corn"],
            "Shelf 3": ["Cream corn"],
            "Shelf 4": []
        },
        "Section 2": {
            "Shelf 1": ["French green beans"],
            "Shelf 2": ["Cut green beans"],
            "Shelf 3": ["Peas"],
            "Shelf 4": []
        },
        "Section 3": {
            "Shelf 1": ["Carrots"],
            "Shelf 1b": ["Mixed vegetables"],
            "Shelf 2": ["Hominy"],
            "Shelf 2b": ["Chickpeas"],
            "Shelf 2c": ["Lima beans"],
            "Shelf 3": ["Beans"],
            "Shelf 3b": ["Black beans"],
            "Shelf 3c": ["Potatoes"],
            "Shelf 3d": ["Yams"],
            "Shelf 3e": ["Beans canned"],
            "Shelf 4": []
        },
        "Section 4": {
            "Shelf 1": ["Tomatoes"],
            "Shelf 1b": ["Chili"],
            "Shelf 1c": ["Meals in can"],
            "Shelf 2": ["Soup"],
            "Shelf 2b": ["Cranberry sauce"],
            "Shelf 2c": ["Fruit"],
            "Shelf 3": ["Ravioli / Spaghetti"],
            "Shelf 3b": ["Spaghetti sauce"],
            "Shelf 3c": ["Cooking oil"],
            "Shelf 4": []
        },
        "Section 5": {
            "Shelf 1": ["Can fish"],
            "Shelf 1b": ["Can meat"],
            "Shelf 2": ["Salt"],
            "Shelf 2b": ["Pepper"],
            "Shelf 2c": ["Seasonings"],
            "Shelf 3": ["Sugar substitute"],
            "Shelf 3b": ["Flour"],
            "Shelf 3c": ["Sugar"],
            "Shelf 4": []
        },
        "Section 6": {
            "Shelf 1": ["Baking soda"],
            "Shelf 1b": ["Baking powder"],
            "Shelf 1c": ["Cornstarch"],
            "Shelf 2": ["Peanut butter"],
            "Shelf 2b": ["Crunchy peanut butter"],
            "Shelf 2c": ["Peanut butter / Jelly mix"],
            "Shelf 2d": ["Jelly"],
            "Shelf 3": ["Condiments"],
            "Shelf 3b": ["Waffle / Pancake mix"],
            "Shelf 4": []
        },
        "Section 7": {
            "Shelf 1": ["Box mac & cheese"],
            "Shelf 1b": ["Hamburger helper"],
            "Shelf 2": ["Chicken helper"],
            "Shelf 2b": ["Tuna helper"],
            "Shelf 2c": ["Misc. Box meals"],
            "Shelf 3": ["Chicken ramen noodles"],
            "Shelf 3b": ["Beef ramen noodles"],
            "Shelf 4": []
        },
        "Section 8": {
            "Shelf 1": ["Misc ramen noodles"],
            "Shelf 1b": ["Stuffing"],
            "Shelf 2": ["Rice"],
            "Shelf 2b": ["Mash potatoes"],
            "Shelf 3": [],
            "Shelf 4": []
        },
        "Section 9": {
            "Shelf 1": ["Asian food"],
            "Shelf 1b": ["Mexican food"],
            "Shelf 2": ["Northern beans (dry)"],
            "Shelf 2b": ["Lentils (dry)"],
            "Shelf 2c": ["Split pea (dry)"],
            "Shelf 2d": ["Pinto beans (dry)"],
            "Shelf 3": ["Red kidney beans (dry)"],
            "Shelf 3b": ["Black eyed peas (dry)"],
            "Shelf 3c": ["Garbonzo / Chickpeas (dry)"],
            "Shelf 3d": ["Black beans (dry)"],
            "Shelf 4": []
        },
        "Section 10": {
            "Shelf 1": ["Crackers"],
            "Shelf 2": ["Pasta"],
            "Shelf 3": ["Misc. Food"],
            "Shelf 4": []
        },
        "Section 11": {
            "Shelf 1": ["Desserts"],
            "Shelf 1b": ["Sweet baked goods"],
            "Shelf 2": ["Snack"],
            "Shelf 3": ["Snack bars / Chips"],
            "Shelf 4": []
        },
        "Section 12": {
            "Shelf 1": ["Box cereal"],
            "Shelf 1b": ["Breakfast drinks"],
            "Shelf 2": ["Bag cereal"],
            "Shelf 2b": ["Grits"],
            "Shelf 3": ["Oatmeal"],
            "Shelf 4": []
        }
    }

    def __init__(self, db_path: str = None):
        """Initialize audit.
        
        Args:
            db_path: Path to inventory database
        """
        if db_path is None:
            db_path = Path(__file__).parent / "data" / "inventory.db"
        
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def get_database_items(self) -> Dict[str, List[str]]:
        """Get all items from database, grouped by category.
        
        Returns:
            Dictionary of items by category
        """
        self.cursor.execute("""
            SELECT DISTINCT LOWER(item_name) as item_name, category
            FROM inventory_items
            WHERE item_name IS NOT NULL AND item_name != ''
            ORDER BY category, item_name
        """)
        
        items_by_category = {}
        for row in self.cursor.fetchall():
            category = row['category'] or 'Uncategorized'
            item = row['item_name']
            
            if category not in items_by_category:
                items_by_category[category] = []
            items_by_category[category].append(item)
        
        return items_by_category

    def normalize_item_name(self, name: str) -> str:
        """Normalize item name for comparison.
        
        Args:
            name: Item name to normalize
            
        Returns:
            Normalized name
        """
        return name.lower().strip()

    def find_item_in_database(self, item_name: str) -> Tuple[bool, str]:
        """Find item in database.
        
        Args:
            item_name: Item to find
            
        Returns:
            Tuple of (found, database_name)
        """
        normalized = self.normalize_item_name(item_name)
        
        self.cursor.execute("""
            SELECT item_name FROM inventory_items
            WHERE LOWER(item_name) = ?
            LIMIT 1
        """, (normalized,))
        
        result = self.cursor.fetchone()
        if result:
            return True, result['item_name']
        
        return False, None

    def run_audit(self) -> Dict:
        """Run comprehensive inventory audit.
        
        Returns:
            Audit results dictionary
        """
        print("=" * 80)
        print("INVENTORY AUDIT - PHYSICAL PANTRY vs DATABASE")
        print("=" * 80)
        print()
        
        missing_items = []
        found_items = []
        total_items = 0
        
        # Check each section
        for section, shelves in self.PHYSICAL_PANTRY.items():
            print(f"\n📦 {section}")
            print("-" * 80)
            
            for shelf, items in shelves.items():
                if not items:
                    continue
                
                print(f"  {shelf}:")
                
                for item in items:
                    total_items += 1
                    found, db_name = self.find_item_in_database(item)
                    
                    if found:
                        print(f"    ✅ {item}")
                        found_items.append({
                            "section": section,
                            "shelf": shelf,
                            "item": item,
                            "db_name": db_name
                        })
                    else:
                        print(f"    ❌ {item} - NOT IN DATABASE")
                        missing_items.append({
                            "section": section,
                            "shelf": shelf,
                            "item": item
                        })
        
        # Summary
        print("\n" + "=" * 80)
        print("AUDIT SUMMARY")
        print("=" * 80)
        print(f"\nTotal items in physical pantry: {total_items}")
        print(f"Items found in database: {len(found_items)}")
        print(f"Items MISSING from database: {len(missing_items)}")
        print(f"Coverage: {len(found_items)}/{total_items} ({100*len(found_items)//total_items}%)")
        
        if missing_items:
            print("\n" + "=" * 80)
            print("MISSING ITEMS (Not in database)")
            print("=" * 80)
            
            for item in missing_items:
                print(f"\n{item['section']} - {item['shelf']}")
                print(f"  Item: {item['item']}")
        
        # Check for extra items in database
        print("\n" + "=" * 80)
        print("DATABASE ITEMS NOT IN PHYSICAL PANTRY")
        print("=" * 80)
        
        db_items = self.get_database_items()
        physical_items_normalized = set()
        
        for section, shelves in self.PHYSICAL_PANTRY.items():
            for shelf, items in shelves.items():
                for item in items:
                    physical_items_normalized.add(self.normalize_item_name(item))
        
        extra_items = []
        self.cursor.execute("""
            SELECT DISTINCT LOWER(item_name) as item_name, item_name as original_name
            FROM inventory_items
            WHERE item_name IS NOT NULL AND item_name != ''
        """)
        
        for row in self.cursor.fetchall():
            if row['item_name'] not in physical_items_normalized:
                extra_items.append(row['original_name'])
        
        if extra_items:
            print(f"\nFound {len(extra_items)} items in database not in physical pantry:")
            for item in sorted(extra_items):
                print(f"  - {item}")
        else:
            print("\n✅ All database items are in physical pantry!")
        
        return {
            "total_physical": total_items,
            "found": len(found_items),
            "missing": len(missing_items),
            "extra": len(extra_items),
            "coverage_percent": 100 * len(found_items) // total_items if total_items > 0 else 0,
            "missing_items": missing_items,
            "extra_items": extra_items
        }

    def generate_missing_items_sql(self) -> str:
        """Generate SQL to add missing items.
        
        Returns:
            SQL insert statements
        """
        audit = self.run_audit()
        missing = audit['missing_items']
        
        if not missing:
            return "-- No missing items"
        
        sql = "-- SQL to add missing items\n\n"
        
        for item in missing:
            section = item['section']
            shelf = item['shelf']
            item_name = item['item']
            
            # Extract section number
            section_num = section.split()[-1]
            
            sql += f"INSERT INTO inventory_items (item_name, category, storage_location, section, current_quantity, minimum_quantity, status) VALUES ('{item_name}', 'Uncategorized', '{shelf}', 'Section {section_num}', 0, 0, 'OUT OF STOCK');\n"
        
        return sql

    def close(self):
        """Close database connection."""
        self.conn.close()


if __name__ == "__main__":
    audit = InventoryAudit()
    results = audit.run_audit()
    
    print("\n" + "=" * 80)
    print("AUDIT COMPLETE")
    print("=" * 80)
    
    audit.close()
