"""
ai_item_suggester.py — AI-powered item suggestion engine.

Combines OpenAI analysis with barcode lookup and brands database
to suggest product information based on brand input.
"""

from typing import List, Dict, Optional
import json
from barcode_lookup import BarcodeLookuper
from brands_database import BrandsDatabase


class ItemSuggester:
    """Suggests item information using AI and external data sources."""

    def __init__(self, db, ai_client=None):
        """Initialize item suggester.
        
        Args:
            db: Database instance
            ai_client: OpenAI client instance (optional)
        """
        self.db = db
        self.ai_client = ai_client
        self.barcode_lookuper = BarcodeLookuper()
        self.brands_db = BrandsDatabase()

    def suggest_items(
        self,
        brand: str,
        barcode: str = None,
        quantity: int = None,
        shelf: str = None,
        section: str = None
    ) -> List[Dict]:
        """Suggest item information based on brand.
        
        Args:
            brand: Brand name (required)
            barcode: Product barcode (optional)
            quantity: Quantity (optional)
            shelf: Shelf location (optional)
            section: Section location (optional)
            
        Returns:
            List of suggestion dictionaries with multiple options
        """
        if not brand or not brand.strip():
            return []
        
        suggestions = []

        # 1. Check brands database for cached data
        cached = self.brands_db.get_brand(brand)
        if cached:
            suggestions.append(self._format_suggestion(
                cached,
                source="Brands Database (Learned)",
                confidence=0.95
            ))

        # 2. Try barcode lookup if provided
        if barcode and barcode.strip():
            barcode_data = self.barcode_lookuper.lookup(barcode)
            if barcode_data:
                suggestions.append(self._format_suggestion(
                    barcode_data,
                    source="Barcode Lookup",
                    confidence=0.90
                ))

        # 3. Use OpenAI for analysis
        if self.ai_client:
            ai_suggestions = self._get_ai_suggestions(brand, barcode)
            suggestions.extend(ai_suggestions)

        # 4. If no suggestions, create a basic one
        if not suggestions:
            suggestions.append(self._create_basic_suggestion(brand))

        # Add user-provided data
        for suggestion in suggestions:
            if quantity:
                suggestion["current_quantity"] = quantity
            if shelf:
                suggestion["storage_location"] = shelf
            if section:
                suggestion["section"] = section

        return suggestions

    def _get_ai_suggestions(self, brand: str, barcode: str = None) -> List[Dict]:
        """Get suggestions from OpenAI.
        
        Args:
            brand: Brand name
            barcode: Product barcode
            
        Returns:
            List of AI-generated suggestions
        """
        if not self.ai_client:
            return []

        try:
            barcode_info = f" and barcode {barcode}" if barcode else ""
            prompt = f"""Based on the brand "{brand}"{barcode_info}, 
suggest 3 different products that this brand might sell.

For each product, provide:
1. Product name
2. Category (from: Grains & Cereals, Canned Goods, Dairy, Frozen, Beverages, Snacks, Baking, Condiments, Pasta, Beans & Legumes, Produce, Meat, Bread, Other)
3. Typical shelf life in days
4. Brief description

Format as JSON array with objects containing: name, category, shelf_life_days, description"""

            response = self.ai_client.ask(prompt)
            
            # Parse JSON response
            try:
                suggestions = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\[.*\]', response, re.DOTALL)
                if json_match:
                    suggestions = json.loads(json_match.group())
                else:
                    return []
            
            formatted = []
            for i, sugg in enumerate(suggestions[:3]):  # Limit to 3
                formatted.append(self._format_suggestion(
                    {
                        "item_name": sugg.get("name"),
                        "category": sugg.get("category"),
                        "shelf_life_days": sugg.get("shelf_life_days"),
                        "notes": sugg.get("description")
                    },
                    source="OpenAI Analysis",
                    confidence=0.85 - (i * 0.05)  # Decrease confidence for alternatives
                ))
            
            return formatted
        except Exception as e:
            print(f"AI suggestion error: {e}")
            return []

    def _format_suggestion(self, data: Dict, source: str, confidence: float) -> Dict:
        """Format suggestion data.
        
        Args:
            data: Raw suggestion data
            source: Source of suggestion
            confidence: Confidence score (0-1)
            
        Returns:
            Formatted suggestion
        """
        return {
            "item_name": data.get("item_name") or data.get("name", ""),
            "brand": data.get("brand", ""),
            "category": data.get("category", ""),
            "shelf_life_days": data.get("shelf_life_days") or data.get("shelf_life", 365),
            "notes": data.get("notes") or data.get("description", ""),
            "source": source,
            "confidence": confidence,
            "nutrition": data.get("nutrition", {})
        }

    def _create_basic_suggestion(self, brand: str) -> Dict:
        """Create a basic suggestion when no data is available.
        
        Args:
            brand: Brand name
            
        Returns:
            Basic suggestion
        """
        return {
            "item_name": brand,
            "brand": brand,
            "category": "Uncategorized",
            "shelf_life_days": 365,
            "notes": f"Product from {brand}",
            "source": "Manual Entry",
            "confidence": 0.5,
            "nutrition": {}
        }

    def save_selection(self, brand: str, selected_suggestion: Dict):
        """Save user's selection to brands database for future learning.
        
        Args:
            brand: Brand name
            selected_suggestion: The suggestion user selected
        """
        self.brands_db.add_brand(brand, {
            "item_name": selected_suggestion.get("item_name"),
            "brand": selected_suggestion.get("brand", brand),
            "category": selected_suggestion.get("category"),
            "shelf_life_days": selected_suggestion.get("shelf_life_days"),
            "notes": selected_suggestion.get("notes"),
            "nutrition": selected_suggestion.get("nutrition", {})
        })

    def get_brand_history(self, brand: str) -> Optional[Dict]:
        """Get previously saved information for a brand.
        
        Args:
            brand: Brand name
            
        Returns:
            Brand data or None
        """
        return self.brands_db.get_brand(brand)

    def get_brands_stats(self) -> Dict:
        """Get brands database statistics.
        
        Returns:
            Statistics dictionary
        """
        return self.brands_db.get_stats()
