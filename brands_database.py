"""
brands_database.py — Persistent brands database that grows over time.

Stores brand information learned from user selections and AI suggestions.
Learns from every item added to improve future suggestions.
"""

import json
import os
from typing import Dict, List, Optional
from datetime import datetime


class BrandsDatabase:
    """Manages a persistent database of brands and their attributes."""

    def __init__(self, db_path: str = None):
        """Initialize brands database.
        
        Args:
            db_path: Path to brands.json file
        """
        if db_path is None:
            db_path = os.path.join(
                os.path.dirname(__file__),
                "data",
                "brands.json"
            )
        
        self.db_path = db_path
        self.brands = self._load_brands()

    def _load_brands(self) -> Dict:
        """Load brands from JSON file."""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading brands database: {e}")
                return {}
        return {}

    def _save_brands(self):
        """Save brands to JSON file."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, 'w') as f:
                json.dump(self.brands, f, indent=2)
        except Exception as e:
            print(f"Error saving brands database: {e}")

    def get_brand(self, brand_name: str) -> Optional[Dict]:
        """Get brand information.
        
        Args:
            brand_name: Brand name to look up
            
        Returns:
            Brand data or None if not found
        """
        return self.brands.get(brand_name.lower())

    def add_brand(self, brand_name: str, data: Dict):
        """Add or update brand information.
        
        Args:
            brand_name: Brand name
            data: Brand data (category, shelf_life, nutrition, etc.)
        """
        key = brand_name.lower()
        existing = self.brands.get(key, {})
        
        self.brands[key] = {
            **data,
            "added_at": existing.get("added_at", datetime.now().isoformat()),
            "updated_at": datetime.now().isoformat(),
            "usage_count": existing.get("usage_count", 0) + 1
        }
        self._save_brands()

    def search_brands(self, query: str) -> List[Dict]:
        """Search for brands matching query.
        
        Args:
            query: Search query
            
        Returns:
            List of matching brands
        """
        query_lower = query.lower()
        results = []
        
        for brand_name, data in self.brands.items():
            if query_lower in brand_name:
                results.append({
                    "name": brand_name,
                    **data
                })
        
        # Sort by usage count (most used first)
        return sorted(results, key=lambda x: x.get("usage_count", 0), reverse=True)

    def get_category_suggestions(self, brand_name: str) -> List[str]:
        """Get category suggestions for a brand.
        
        Args:
            brand_name: Brand name
            
        Returns:
            List of suggested categories
        """
        brand = self.get_brand(brand_name)
        if brand and "categories" in brand:
            return brand["categories"]
        return []

    def get_shelf_life_for_category(self, category: str) -> Optional[int]:
        """Get typical shelf life for a category.
        
        Args:
            category: Product category
            
        Returns:
            Shelf life in days or None
        """
        # Common shelf life defaults
        shelf_life_defaults = {
            "Grains & Cereals": 365,
            "Canned Goods": 730,
            "Dairy": 30,
            "Frozen": 365,
            "Beverages": 180,
            "Snacks": 180,
            "Baking": 365,
            "Condiments": 365,
            "Pasta": 365,
            "Beans & Legumes": 365,
            "Produce": 14,
            "Meat": 7,
            "Bread": 7,
        }
        return shelf_life_defaults.get(category, 365)

    def get_all_brands(self) -> List[str]:
        """Get all known brands."""
        return list(self.brands.keys())

    def get_stats(self) -> Dict:
        """Get database statistics."""
        sorted_brands = sorted(
            self.brands.items(),
            key=lambda x: x[1].get("usage_count", 0),
            reverse=True
        )
        
        return {
            "total_brands": len(self.brands),
            "most_used": [
                {"name": name, "count": data.get("usage_count", 0)}
                for name, data in sorted_brands[:10]
            ]
        }

    def clear(self):
        """Clear all brands from database."""
        self.brands = {}
        self._save_brands()
