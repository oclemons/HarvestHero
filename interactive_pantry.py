"""interactive_pantry.py — Live, interactive virtual pantry management system.

Provides a real-time graphical representation of the physical pantry with:
- Live inventory status (low, normal, overstock)
- Interactive item details with quantity controls
- Configurable low-stock and overstock thresholds
- Dynamic quantity updates with automatic UI refresh
- Shelf-level views
- Search with visual highlighting
- Filtering by status, section, shelf
- Inventory history tracking
- Backend validation and permission enforcement
"""

from typing import Dict, List, Tuple, Optional
import datetime
from dataclasses import dataclass


@dataclass
class InventoryStatus:
    """Represents the current inventory status of an item."""
    status: str  # "low", "normal", "overstock", "not_configured"
    quantity: int
    low_threshold: int
    overstock_threshold: int
    is_low: bool
    is_overstock: bool
    is_configured: bool


class InteractivePantry:
    """Core pantry management logic with inventory status calculation."""

    def __init__(self, db):
        self.db = db

    def get_item_status(self, item: dict) -> InventoryStatus:
        """Calculate the inventory status of an item.
        
        Status determination:
        - "not_configured": quantity not set (None or -1)
        - "low": 0 < quantity <= low_threshold
        - "overstock": quantity > overstock_threshold (if threshold set)
        - "normal": all other cases
        """
        qty = item.get("current_quantity")
        low_thresh = item.get("minimum_stock", 0) or 0
        over_thresh = item.get("overstock_threshold", 0) or 0

        # Not configured: quantity is None or negative
        if qty is None or qty < 0:
            return InventoryStatus(
                status="not_configured",
                quantity=0,
                low_threshold=low_thresh,
                overstock_threshold=over_thresh,
                is_low=False,
                is_overstock=False,
                is_configured=False,
            )

        qty = int(qty)
        is_low = (0 < qty <= low_thresh) if low_thresh > 0 else False
        is_overstock = (qty > over_thresh) if over_thresh > 0 else False

        if is_low:
            status = "low"
        elif is_overstock:
            status = "overstock"
        else:
            status = "normal"

        return InventoryStatus(
            status=status,
            quantity=qty,
            low_threshold=low_thresh,
            overstock_threshold=over_thresh,
            is_low=is_low,
            is_overstock=is_overstock,
            is_configured=True,
        )

    def update_quantity(self, item_id: int, delta: int, user: dict) -> Tuple[bool, str, Optional[int]]:
        """Update item quantity with validation.
        
        Args:
            item_id: Item ID to update
            delta: Change amount (positive to add, negative to remove)
            user: Current user dict with role and username
        
        Returns:
            (success, message, new_quantity)
        """
        # Permission check
        if user.get("role") not in ("admin", "staff"):
            return (False, "Insufficient permissions", None)

        # Get current item
        try:
            item = self.db.get_item_by_id(item_id)
        except Exception:
            return (False, "Item not found", None)

        if not item:
            return (False, "Item not found", None)

        current_qty = item.get("current_quantity", 0) or 0
        new_qty = current_qty + delta

        # Validation
        if new_qty < 0:
            return (False, f"Cannot remove {abs(delta)} units (only {current_qty} available)", None)

        # Update quantity
        try:
            self.db.adjust_stock(item["barcode"], delta)
            
            # Record transaction
            self._record_transaction(
                item_id, item["barcode"], item["item_name"],
                current_qty, new_qty, delta, user
            )
            
            return (True, f"Updated to {new_qty} units", new_qty)
        except Exception as e:
            return (False, f"Update failed: {str(e)}", None)

    def update_thresholds(self, item_id: int, low_threshold: int, overstock_threshold: int,
                         user: dict) -> Tuple[bool, str]:
        """Update low-stock and overstock thresholds.
        
        Args:
            item_id: Item ID
            low_threshold: New low-stock threshold (must be >= 0)
            overstock_threshold: New overstock threshold (must be > low_threshold or 0)
            user: Current user
        
        Returns:
            (success, message)
        """
        # Permission check
        if user.get("role") != "admin":
            return (False, "Only admins can modify thresholds")

        # Validation
        if low_threshold < 0:
            return (False, "Low-stock threshold cannot be negative")
        if overstock_threshold < 0:
            return (False, "Overstock threshold cannot be negative")
        if overstock_threshold > 0 and overstock_threshold <= low_threshold:
            return (False, "Overstock threshold must be greater than low-stock threshold")

        try:
            item = self.db.get_item_by_id(item_id)
            if not item:
                return (False, "Item not found")

            # Update in database
            conn = self.db._connect()
            conn.execute(
                """UPDATE inventory_items
                   SET minimum_stock = ?, overstock_threshold = ?,
                       updated_at = datetime('now', 'localtime')
                   WHERE id = ?""",
                (low_threshold, overstock_threshold, item_id),
            )
            conn.commit()
            conn.close()

            return (True, "Thresholds updated successfully")
        except Exception as e:
            return (False, f"Update failed: {str(e)}")

    def set_quantity(self, item_id: int, new_qty: int, user: dict) -> Tuple[bool, str, Optional[int]]:
        """Set item quantity to a specific value (admin only).
        
        Args:
            item_id: Item ID
            new_qty: New quantity (must be >= 0)
            user: Current user
        
        Returns:
            (success, message, new_quantity)
        """
        # Permission check
        if user.get("role") != "admin":
            return (False, "Only admins can set quantities directly", None)

        # Validation
        if new_qty < 0:
            return (False, "Quantity cannot be negative", None)

        try:
            item = self.db.get_item_by_id(item_id)
            if not item:
                return (False, "Item not found", None)

            current_qty = item.get("current_quantity", 0) or 0
            delta = new_qty - current_qty

            # Update quantity
            self.db.adjust_stock(item["barcode"], delta)

            # Record transaction
            self._record_transaction(
                item_id, item["barcode"], item["item_name"],
                current_qty, new_qty, delta, user
            )

            return (True, f"Quantity set to {new_qty} units", new_qty)
        except Exception as e:
            return (False, f"Update failed: {str(e)}", None)

    def _record_transaction(self, item_id: int, barcode: str, item_name: str,
                           old_qty: int, new_qty: int, delta: int, user: dict):
        """Record inventory transaction for audit trail."""
        try:
            conn = self.db._connect()
            conn.execute(
                """INSERT INTO transactions
                   (transaction_type, barcode, item_name, category, quantity,
                    username, notes, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))""",
                ("adjustment", barcode, item_name, "", delta,
                 user.get("username", "system"),
                 f"Adjusted from {old_qty} to {new_qty}"),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Transaction recording failure shouldn't block the update

    def get_pantry_summary(self) -> dict:
        """Get overall pantry statistics.
        
        Returns:
            {
                "total_items": int,
                "total_units": int,
                "low_stock_items": int,
                "normal_items": int,
                "overstock_items": int,
                "not_configured": int,
                "sections": int,
            }
        """
        try:
            items = self.db.get_all_items()
            
            total_items = len(items)
            total_units = sum(item.get("current_quantity", 0) or 0 for item in items)
            
            low_count = 0
            normal_count = 0
            overstock_count = 0
            not_configured_count = 0
            
            for item in items:
                status = self.get_item_status(item)
                if status.status == "not_configured":
                    not_configured_count += 1
                elif status.status == "low":
                    low_count += 1
                elif status.status == "overstock":
                    overstock_count += 1
                else:
                    normal_count += 1
            
            # Count unique sections
            sections = set()
            for item in items:
                loc = item.get("storage_location", "")
                if loc:
                    section_num, _ = self._parse_location(loc)
                    if section_num > 0:
                        sections.add(section_num)
            
            return {
                "total_items": total_items,
                "total_units": total_units,
                "low_stock_items": low_count,
                "normal_items": normal_count,
                "overstock_items": overstock_count,
                "not_configured": not_configured_count,
                "sections": len(sections),
            }
        except Exception:
            return {
                "total_items": 0,
                "total_units": 0,
                "low_stock_items": 0,
                "normal_items": 0,
                "overstock_items": 0,
                "not_configured": 0,
                "sections": 0,
            }

    def filter_items(self, items: List[dict], status_filter: Optional[str] = None,
                    section_filter: Optional[int] = None,
                    shelf_filter: Optional[int] = None) -> List[dict]:
        """Filter items by status, section, or shelf.
        
        Args:
            items: List of items to filter
            status_filter: "low", "normal", "overstock", "not_configured", or None
            section_filter: Section number or None
            shelf_filter: Shelf number or None
        
        Returns:
            Filtered list of items
        """
        filtered = items

        # Status filter
        if status_filter:
            filtered = [
                item for item in filtered
                if self.get_item_status(item).status == status_filter
            ]

        # Location filters
        if section_filter is not None or shelf_filter is not None:
            filtered_by_loc = []
            for item in filtered:
                loc = item.get("storage_location", "")
                section_num, shelf_num = self._parse_location(loc)

                if section_filter is not None and section_num != section_filter:
                    continue
                if shelf_filter is not None and shelf_num != shelf_filter:
                    continue

                filtered_by_loc.append(item)
            filtered = filtered_by_loc

        return filtered

    @staticmethod
    def _parse_location(location: str) -> Tuple[int, int]:
        """Parse storage location into (section, shelf)."""
        if not location:
            return (0, 0)

        location = location.strip().upper()

        # Try "Section XX, Shelf Y" format
        if "SECTION" in location and "SHELF" in location:
            parts = location.split(",")
            try:
                section = int("".join(c for c in parts[0] if c.isdigit()))
                shelf = int("".join(c for c in parts[1] if c.isdigit()))
                return (section, shelf)
            except (ValueError, IndexError):
                pass

        # Try "SXX-SY" format
        if location.startswith("S") and "-S" in location:
            try:
                parts = location.split("-")
                section = int(parts[0][1:])
                shelf = int(parts[1][1:])
                return (section, shelf)
            except (ValueError, IndexError):
                pass

        # Try "XX-Y" format
        if "-" in location:
            try:
                parts = location.split("-")
                section = int(parts[0])
                shelf = int(parts[1])
                return (section, shelf)
            except (ValueError, IndexError):
                pass

        # Try to extract any numbers
        numbers = [int(s) for s in location.split() if s.isdigit()]
        if len(numbers) >= 2:
            return (numbers[0], numbers[1])
        elif len(numbers) == 1:
            return (numbers[0], 0)

        return (0, 0)
