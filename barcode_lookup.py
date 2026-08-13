"""
barcode_lookup.py — Barcode lookup integration for product information.

Supports multiple barcode APIs:
- Open Food Facts (free, no key required)
- Barcode Lookup API (requires key)
"""

import requests
from typing import Optional, Dict
import os


class BarcodeLookuper:
    """Looks up product information from barcodes."""

    def __init__(self):
        """Initialize barcode lookup."""
        self.open_food_facts_url = "https://world.openfoodfacts.org/api/v0/product"
        self.barcode_lookup_key = os.getenv("BARCODE_LOOKUP_KEY")

    def lookup_open_food_facts(self, barcode: str) -> Optional[Dict]:
        """Look up product using Open Food Facts API (free).
        
        Args:
            barcode: Product barcode (UPC/EAN)
            
        Returns:
            Product data or None if not found
        """
        if not barcode or not barcode.strip():
            return None
        
        try:
            url = f"{self.open_food_facts_url}/{barcode}.json"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                product = data.get("product", {})
                
                if product:
                    return {
                        "item_name": product.get("product_name", ""),
                        "brand": product.get("brands", ""),
                        "category": product.get("categories", ""),
                        "nutrition": {
                            "calories": product.get("nutriments", {}).get("energy-kcal_100g"),
                            "protein": product.get("nutriments", {}).get("proteins_100g"),
                            "carbs": product.get("nutriments", {}).get("carbohydrates_100g"),
                            "fat": product.get("nutriments", {}).get("fat_100g"),
                        },
                        "source": "Open Food Facts"
                    }
        except requests.exceptions.Timeout:
            print("Open Food Facts lookup timeout")
        except Exception as e:
            print(f"Open Food Facts lookup error: {e}")
        
        return None

    def lookup_barcode_lookup_api(self, barcode: str) -> Optional[Dict]:
        """Look up product using Barcode Lookup API (requires key).
        
        Args:
            barcode: Product barcode
            
        Returns:
            Product data or None if not found
        """
        if not self.barcode_lookup_key or not barcode or not barcode.strip():
            return None
        
        try:
            url = "https://api.barcodelookup.com/v3/products"
            params = {
                "barcode": barcode,
                "key": self.barcode_lookup_key
            }
            response = requests.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get("products", [])
                
                if products:
                    product = products[0]
                    return {
                        "item_name": product.get("title", ""),
                        "brand": product.get("brand", ""),
                        "category": product.get("category", ""),
                        "description": product.get("description", ""),
                        "source": "Barcode Lookup API"
                    }
        except requests.exceptions.Timeout:
            print("Barcode Lookup API timeout")
        except Exception as e:
            print(f"Barcode Lookup API error: {e}")
        
        return None

    def lookup(self, barcode: str) -> Optional[Dict]:
        """Look up product from barcode using available APIs.
        
        Args:
            barcode: Product barcode
            
        Returns:
            Product data or None if not found
        """
        if not barcode or not barcode.strip():
            return None
        
        # Try Open Food Facts first (free)
        result = self.lookup_open_food_facts(barcode)
        if result:
            return result
        
        # Try Barcode Lookup API if key is available
        result = self.lookup_barcode_lookup_api(barcode)
        if result:
            return result
        
        return None
