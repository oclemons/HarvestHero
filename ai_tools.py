"""
ai_tools.py — Backend tools for Harvest AI conversational interface.

Provides READ-ONLY tools that allow the AI to query current pantry data
without sending the entire database with each request. Tools are called
by the AI when it needs to answer questions about inventory, clients,
or operations.

All tools are READ-ONLY and follow application authorization rules.
"""

from typing import List, Dict, Any, Optional


class AIToolsManager:
    """Manager for AI backend tools with database access."""

    def __init__(self, db):
        """Initialize tools manager with database reference.
        
        Args:
            db: Database instance for querying pantry data
        """
        self.db = db

    # -----------------------------------------------------------------------
    # Inventory Tools
    # -----------------------------------------------------------------------

    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get high-level inventory summary.
        
        Returns:
            Dictionary with total items, stock status counts, etc.
        """
        try:
            stats = self.db.get_stats()
            return {
                "total_items": stats.get("total_items", 0),
                "in_stock": stats.get("in_stock", 0),
                "low_stock": stats.get("low_stock", 0),
                "out_of_stock": stats.get("out_of_stock", 0),
                "overstock": stats.get("overstock", 0),
            }
        except Exception as e:
            return {"error": f"Failed to get inventory summary: {str(e)}"}

    def search_inventory(self, query: str) -> List[Dict[str, Any]]:
        """Search for items by name or barcode.
        
        Args:
            query: Search term (item name or barcode)
        
        Returns:
            List of matching items with details
        """
        try:
            results = []
            
            # Try searching by barcode first
            item = self.db.get_item_by_any_barcode(query)
            if item:
                results.append(self._format_item(item))
                return results
            
            # Search by name in all items
            all_items = self.db.get_all_items()
            query_lower = query.lower()
            for item in all_items:
                if query_lower in item.get("name", "").lower():
                    results.append(self._format_item(item))
            
            return results[:10]  # Limit to 10 results
        except Exception as e:
            return [{"error": f"Search failed: {str(e)}"}]

    def get_item_details(self, item_id: int) -> Dict[str, Any]:
        """Get detailed information about a specific item.
        
        Args:
            item_id: Item ID
        
        Returns:
            Detailed item information
        """
        try:
            item = self.db.get_item_by_id(item_id)
            if not item:
                return {"error": f"Item {item_id} not found"}
            return self._format_item(item)
        except Exception as e:
            return {"error": f"Failed to get item details: {str(e)}"}

    def get_item_location(self, item_id: int) -> Dict[str, Any]:
        """Get storage location of an item.
        
        Args:
            item_id: Item ID
        
        Returns:
            Location information (section, shelf, etc.)
        """
        try:
            item = self.db.get_item_by_id(item_id)
            if not item:
                return {"error": f"Item {item_id} not found"}
            
            return {
                "item_name": item.get("name"),
                "section": item.get("section"),
                "shelf": item.get("shelf"),
                "location": f"{item.get('section')} → Shelf {item.get('shelf')}",
            }
        except Exception as e:
            return {"error": f"Failed to get location: {str(e)}"}

    def get_low_stock_items(self) -> List[Dict[str, Any]]:
        """Get all items currently below low-stock threshold.
        
        Returns:
            List of low-stock items
        """
        try:
            items = self.db.get_low_stock_items()
            return [self._format_item(item) for item in items][:20]
        except Exception as e:
            return [{"error": f"Failed to get low-stock items: {str(e)}"}]

    def get_overstock_items(self) -> List[Dict[str, Any]]:
        """Get all items currently above overstock threshold.
        
        Returns:
            List of overstocked items
        """
        try:
            items = self.db.get_all_items()
            overstock = [
                item for item in items
                if item.get("quantity", 0) > item.get("overstock_threshold", float('inf'))
            ]
            return [self._format_item(item) for item in overstock][:20]
        except Exception as e:
            return [{"error": f"Failed to get overstock items: {str(e)}"}]

    def get_section_summary(self, section: str) -> Dict[str, Any]:
        """Get summary of a pantry section.
        
        Args:
            section: Section name
        
        Returns:
            Section summary with item counts and status
        """
        try:
            items = self.db.get_inventory_by_category(section)
            if not items:
                return {"error": f"Section '{section}' not found"}
            
            low = sum(1 for i in items if i.get("status") == "low")
            out = sum(1 for i in items if i.get("status") == "out")
            over = sum(1 for i in items if i.get("quantity", 0) > i.get("overstock_threshold", float('inf')))
            
            return {
                "section": section,
                "total_items": len(items),
                "low_stock": low,
                "out_of_stock": out,
                "overstock": over,
                "healthy": len(items) - low - out - over,
            }
        except Exception as e:
            return {"error": f"Failed to get section summary: {str(e)}"}

    def get_shelf_contents(self, section: str, shelf: int) -> List[Dict[str, Any]]:
        """Get all items on a specific shelf.
        
        Args:
            section: Section name
            shelf: Shelf number
        
        Returns:
            List of items on the shelf
        """
        try:
            all_items = self.db.get_all_items()
            shelf_items = [
                item for item in all_items
                if item.get("section") == section and item.get("shelf") == shelf
            ]
            return [self._format_item(item) for item in shelf_items]
        except Exception as e:
            return [{"error": f"Failed to get shelf contents: {str(e)}"}]

    def get_recent_inventory_activity(self, days: int = 1) -> List[Dict[str, Any]]:
        """Get recent inventory transactions.
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of recent transactions
        """
        try:
            transactions = self.db.get_recent_transactions(days)
            return [
                {
                    "item": t.get("item_name"),
                    "type": t.get("transaction_type"),
                    "quantity": t.get("quantity"),
                    "timestamp": t.get("timestamp"),
                }
                for t in transactions
            ][:50]
        except Exception as e:
            return [{"error": f"Failed to get activity: {str(e)}"}]

    # -----------------------------------------------------------------------
    # Distribution & Client Tools
    # -----------------------------------------------------------------------

    def get_distribution_summary(self) -> Dict[str, Any]:
        """Get summary of recent distributions.
        
        Returns:
            Summary of distribution activity
        """
        try:
            visits = self.db.get_recent_pantry_visits(days=1)
            if not visits:
                return {
                    "distributions_today": 0,
                    "clients_served": 0,
                    "message": "No distributions recorded today",
                }
            
            return {
                "distributions_today": len(visits),
                "clients_served": len(set(v.get("client_id") for v in visits)),
                "recent_visits": len(visits),
            }
        except Exception as e:
            return {"error": f"Failed to get distribution summary: {str(e)}"}

    def get_client_visit_statistics(self) -> Dict[str, Any]:
        """Get statistics about client visits.
        
        Returns:
            Client visit statistics
        """
        try:
            stats = self.db.get_stats()
            return {
                "total_clients": stats.get("total_clients", 0),
                "active_clients": stats.get("active_clients", 0),
                "visits_this_month": stats.get("visits_this_month", 0),
            }
        except Exception as e:
            return {"error": f"Failed to get client statistics: {str(e)}"}

    # -----------------------------------------------------------------------
    # Operational Tools
    # -----------------------------------------------------------------------

    def get_operational_summary(self) -> Dict[str, Any]:
        """Get comprehensive operational overview.
        
        Returns:
            Full operational summary
        """
        try:
            stats = self.db.get_stats()
            return {
                "inventory_health": {
                    "total_items": stats.get("total_items", 0),
                    "in_stock": stats.get("in_stock", 0),
                    "low_stock": stats.get("low_stock", 0),
                    "out_of_stock": stats.get("out_of_stock", 0),
                },
                "operations": {
                    "total_clients": stats.get("total_clients", 0),
                    "active_clients": stats.get("active_clients", 0),
                },
                "recent_activity": {
                    "transactions": stats.get("total_transactions", 0),
                },
            }
        except Exception as e:
            return {"error": f"Failed to get operational summary: {str(e)}"}

    # -----------------------------------------------------------------------
    # Helper Methods
    # -----------------------------------------------------------------------

    def _format_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Format item data for AI consumption.
        
        Args:
            item: Raw item data from database
        
        Returns:
            Formatted item data
        """
        return {
            "id": item.get("id"),
            "name": item.get("name"),
            "quantity": item.get("quantity", 0),
            "low_stock_threshold": item.get("low_stock_threshold", 0),
            "overstock_threshold": item.get("overstock_threshold", float('inf')),
            "status": item.get("status", "unknown"),
            "section": item.get("section"),
            "shelf": item.get("shelf"),
            "barcode": item.get("barcode"),
        }

    def get_available_tools(self) -> List[Dict[str, str]]:
        """Get list of available tools for AI.
        
        Returns:
            List of tool descriptions
        """
        return [
            {
                "name": "get_inventory_summary",
                "description": "Get high-level inventory summary (total items, stock status counts)",
            },
            {
                "name": "search_inventory",
                "description": "Search for items by name or barcode",
            },
            {
                "name": "get_item_details",
                "description": "Get detailed information about a specific item",
            },
            {
                "name": "get_item_location",
                "description": "Get storage location of an item (section, shelf)",
            },
            {
                "name": "get_low_stock_items",
                "description": "Get all items currently below low-stock threshold",
            },
            {
                "name": "get_overstock_items",
                "description": "Get all items currently above overstock threshold",
            },
            {
                "name": "get_section_summary",
                "description": "Get summary of a pantry section",
            },
            {
                "name": "get_shelf_contents",
                "description": "Get all items on a specific shelf",
            },
            {
                "name": "get_recent_inventory_activity",
                "description": "Get recent inventory transactions",
            },
            {
                "name": "get_distribution_summary",
                "description": "Get summary of recent distributions",
            },
            {
                "name": "get_client_visit_statistics",
                "description": "Get statistics about client visits",
            },
            {
                "name": "get_operational_summary",
                "description": "Get comprehensive operational overview",
            },
        ]
