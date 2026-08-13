"""
overstock_management.py — Comprehensive overstock management system.

Provides:
- Overstock detection and alerts
- Overstock threshold configuration
- Overstock reporting and analytics
- Overstock recommendations
- Integration with inventory management
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OverstockAlert:
    """Represents an overstock alert for an item."""
    item_id: int
    item_name: str
    current_quantity: int
    overstock_threshold: int
    excess_amount: int
    excess_percent: float
    severity: str  # "warning", "critical"
    category: str
    storage_location: str
    created_at: datetime


class OverstockManager:
    """Manages overstock detection, alerts, and recommendations."""

    def __init__(self, db):
        """Initialize overstock manager.
        
        Args:
            db: Database instance
        """
        self.db = db

    def get_overstock_items(self) -> List[Dict]:
        """Get all items currently in overstock.
        
        Returns:
            List of overstock items with details
        """
        try:
            items = self.db.get_all_items()
            overstock_items = []
            
            for item in items:
                qty = item.get("current_quantity", 0) or 0
                threshold = item.get("overstock_threshold", 0) or 0
                
                # Item is in overstock if threshold is set and qty exceeds it
                if threshold > 0 and qty > threshold:
                    overstock_items.append({
                        "id": item.get("id"),
                        "item_name": item.get("item_name"),
                        "current_quantity": qty,
                        "overstock_threshold": threshold,
                        "excess_amount": qty - threshold,
                        "excess_percent": round(((qty - threshold) / threshold * 100), 1),
                        "category": item.get("category"),
                        "storage_location": item.get("storage_location"),
                        "barcode": item.get("barcode"),
                        "brand": item.get("brand"),
                    })
            
            # Sort by excess amount (highest first)
            return sorted(overstock_items, key=lambda x: x["excess_amount"], reverse=True)
        except Exception as e:
            print(f"Error getting overstock items: {e}")
            return []

    def get_overstock_count(self) -> int:
        """Get total count of overstock items.
        
        Returns:
            Number of items in overstock
        """
        return len(self.get_overstock_items())

    def get_overstock_alerts(self) -> List[OverstockAlert]:
        """Get overstock alerts for critical items.
        
        Returns:
            List of overstock alerts
        """
        alerts = []
        overstock_items = self.get_overstock_items()
        
        for item in overstock_items:
            excess_percent = item["excess_percent"]
            
            # Determine severity
            if excess_percent >= 50:
                severity = "critical"
            else:
                severity = "warning"
            
            alert = OverstockAlert(
                item_id=item["id"],
                item_name=item["item_name"],
                current_quantity=item["current_quantity"],
                overstock_threshold=item["overstock_threshold"],
                excess_amount=item["excess_amount"],
                excess_percent=excess_percent,
                severity=severity,
                category=item["category"],
                storage_location=item["storage_location"],
                created_at=datetime.now()
            )
            alerts.append(alert)
        
        return alerts

    def get_overstock_by_category(self) -> Dict[str, List[Dict]]:
        """Get overstock items grouped by category.
        
        Returns:
            Dictionary of overstock items by category
        """
        overstock_items = self.get_overstock_items()
        by_category = {}
        
        for item in overstock_items:
            category = item.get("category", "Uncategorized")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(item)
        
        return by_category

    def get_overstock_by_section(self) -> Dict[str, List[Dict]]:
        """Get overstock items grouped by storage location/section.
        
        Returns:
            Dictionary of overstock items by section
        """
        overstock_items = self.get_overstock_items()
        by_section = {}
        
        for item in overstock_items:
            location = item.get("storage_location", "Unknown")
            if location not in by_section:
                by_section[location] = []
            by_section[location].append(item)
        
        return by_section

    def get_overstock_statistics(self) -> Dict:
        """Get overstock statistics and analytics.
        
        Returns:
            Dictionary of overstock statistics
        """
        overstock_items = self.get_overstock_items()
        alerts = self.get_overstock_alerts()
        
        if not overstock_items:
            return {
                "total_overstock_items": 0,
                "critical_alerts": 0,
                "warning_alerts": 0,
                "total_excess_units": 0,
                "average_excess_percent": 0,
                "most_overstocked": None,
                "categories_affected": 0,
            }
        
        critical = len([a for a in alerts if a.severity == "critical"])
        warning = len([a for a in alerts if a.severity == "warning"])
        total_excess = sum(item["excess_amount"] for item in overstock_items)
        avg_excess_percent = sum(item["excess_percent"] for item in overstock_items) / len(overstock_items)
        categories = len(set(item["category"] for item in overstock_items))
        
        return {
            "total_overstock_items": len(overstock_items),
            "critical_alerts": critical,
            "warning_alerts": warning,
            "total_excess_units": total_excess,
            "average_excess_percent": round(avg_excess_percent, 1),
            "most_overstocked": overstock_items[0] if overstock_items else None,
            "categories_affected": categories,
        }

    def set_overstock_threshold(self, item_id: int, threshold: int, user: dict) -> Tuple[bool, str]:
        """Set overstock threshold for an item.
        
        Args:
            item_id: Item ID
            threshold: New overstock threshold (0 to disable)
            user: Current user
            
        Returns:
            (success, message)
        """
        # Permission check
        if user.get("role") != "admin":
            return (False, "Only admins can set overstock thresholds")
        
        # Validation
        if threshold < 0:
            return (False, "Overstock threshold cannot be negative")
        
        try:
            item = self.db.get_item_by_id(item_id)
            if not item:
                return (False, "Item not found")
            
            low_threshold = item.get("minimum_stock", 0) or 0
            
            # Validate relationship
            if threshold > 0 and threshold <= low_threshold:
                return (False, f"Overstock threshold ({threshold}) must be greater than low-stock threshold ({low_threshold})")
            
            # Update in database
            conn = self.db._connect()
            conn.execute(
                """UPDATE inventory_items
                   SET overstock_threshold = ?, updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (threshold, item_id),
            )
            conn.commit()
            conn.close()
            
            return (True, f"Overstock threshold set to {threshold}")
        except Exception as e:
            return (False, f"Failed to set threshold: {str(e)}")

    def get_reduction_recommendations(self, item_id: int) -> Dict:
        """Get recommendations for reducing overstock.
        
        Args:
            item_id: Item ID
            
        Returns:
            Dictionary of recommendations
        """
        try:
            item = self.db.get_item_by_id(item_id)
            if not item:
                return {"error": "Item not found"}
            
            qty = item.get("current_quantity", 0) or 0
            threshold = item.get("overstock_threshold", 0) or 0
            
            if threshold == 0 or qty <= threshold:
                return {"status": "not_overstocked"}
            
            excess = qty - threshold
            excess_percent = (excess / threshold) * 100
            
            recommendations = {
                "item_name": item.get("item_name"),
                "current_quantity": qty,
                "overstock_threshold": threshold,
                "excess_amount": excess,
                "excess_percent": round(excess_percent, 1),
                "actions": []
            }
            
            # Generate recommendations based on excess amount
            if excess_percent >= 100:
                recommendations["actions"].append({
                    "priority": "critical",
                    "action": "Distribute to other locations",
                    "amount": excess // 2,
                    "reason": f"Item is {excess_percent:.0f}% over threshold"
                })
                recommendations["actions"].append({
                    "priority": "high",
                    "action": "Increase distribution to clients",
                    "amount": excess // 3,
                    "reason": "High overstock level"
                })
            elif excess_percent >= 50:
                recommendations["actions"].append({
                    "priority": "high",
                    "action": "Increase distribution to clients",
                    "amount": excess // 2,
                    "reason": f"Item is {excess_percent:.0f}% over threshold"
                })
            else:
                recommendations["actions"].append({
                    "priority": "medium",
                    "action": "Monitor and gradually reduce",
                    "amount": excess // 3,
                    "reason": "Moderate overstock level"
                })
            
            return recommendations
        except Exception as e:
            return {"error": f"Failed to get recommendations: {str(e)}"}

    def generate_overstock_report(self) -> str:
        """Generate a text report of overstock items.
        
        Returns:
            Formatted report string
        """
        stats = self.get_overstock_statistics()
        overstock_items = self.get_overstock_items()
        
        report = "=" * 80 + "\n"
        report += "OVERSTOCK REPORT\n"
        report += "=" * 80 + "\n\n"
        
        # Summary
        report += "SUMMARY\n"
        report += "-" * 80 + "\n"
        report += f"Total Overstock Items: {stats['total_overstock_items']}\n"
        report += f"Critical Alerts: {stats['critical_alerts']}\n"
        report += f"Warning Alerts: {stats['warning_alerts']}\n"
        report += f"Total Excess Units: {stats['total_excess_units']}\n"
        report += f"Average Excess: {stats['average_excess_percent']}%\n"
        report += f"Categories Affected: {stats['categories_affected']}\n\n"
        
        if not overstock_items:
            report += "✅ No overstock items detected!\n"
            return report
        
        # Detailed items
        report += "OVERSTOCK ITEMS\n"
        report += "-" * 80 + "\n"
        
        for i, item in enumerate(overstock_items, 1):
            report += f"\n{i}. {item['item_name']}\n"
            report += f"   Current: {item['current_quantity']} | Threshold: {item['overstock_threshold']}\n"
            report += f"   Excess: {item['excess_amount']} units ({item['excess_percent']}%)\n"
            report += f"   Category: {item['category']}\n"
            report += f"   Location: {item['storage_location']}\n"
        
        report += "\n" + "=" * 80 + "\n"
        return report
