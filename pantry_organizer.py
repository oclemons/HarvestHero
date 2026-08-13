"""pantry_organizer.py — Virtual pantry organization and overstock detection.

Organizes inventory items into a virtual pantry grid based on storage_location
(e.g., "Section 20, Shelf 2"). Detects overstock conditions and provides
visual feedback for pantry management.
"""

from typing import Dict, List, Tuple, Optional
import datetime


class PantrySection:
    """Represents a section in the pantry (e.g., Section 20)."""

    def __init__(self, section_num: int):
        self.section_num = section_num
        self.shelves: Dict[int, List[dict]] = {}  # shelf_num -> [items]

    def add_item(self, shelf_num: int, item: dict):
        """Add an item to a specific shelf."""
        if shelf_num not in self.shelves:
            self.shelves[shelf_num] = []
        self.shelves[shelf_num].append(item)

    def get_shelves(self) -> List[int]:
        """Return sorted list of shelf numbers."""
        return sorted(self.shelves.keys())

    def get_items_on_shelf(self, shelf_num: int) -> List[dict]:
        """Get all items on a specific shelf."""
        return self.shelves.get(shelf_num, [])

    def get_all_items(self) -> List[dict]:
        """Get all items in this section."""
        items = []
        for shelf_num in self.get_shelves():
            items.extend(self.shelves[shelf_num])
        return items


class PantryOrganizer:
    """Organizes inventory into a virtual pantry grid."""

    def __init__(self, db):
        self.db = db
        self.sections: Dict[int, PantrySection] = {}

    def organize(self, items: List[dict]) -> Dict[int, PantrySection]:
        """Organize items into sections/shelves based on storage_location.
        
        Expected format: "Section 20, Shelf 2" or similar.
        Falls back to "Unorganized" section if location is missing.
        
        Returns:
            Dict mapping section number to PantrySection
        """
        self.sections = {}

        for item in items:
            section_num, shelf_num = self._parse_location(item.get("storage_location", ""))

            if section_num not in self.sections:
                self.sections[section_num] = PantrySection(section_num)

            self.sections[section_num].add_item(shelf_num, item)

        return self.sections

    @staticmethod
    def _parse_location(location: str) -> Tuple[int, int]:
        """Parse storage location string into (section, shelf) numbers.
        
        Handles formats like:
        - "Section 20, Shelf 2"
        - "S20-S2"
        - "20-2"
        - Falls back to (0, 0) for unorganized items
        """
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

        return (0, 0)  # Unorganized

    def get_sections(self) -> List[int]:
        """Return sorted list of section numbers."""
        return sorted(self.sections.keys())

    def get_section(self, section_num: int) -> Optional[PantrySection]:
        """Get a specific section."""
        return self.sections.get(section_num)

    def detect_overstock(self, item: dict) -> bool:
        """Detect if an item is overstocked.
        
        An item is considered overstocked if:
        - Current quantity > (minimum_stock * 2.5)
        
        This allows for reasonable buffer stock while flagging excessive quantities.
        """
        qty = item.get("current_quantity", 0)
        min_stock = item.get("minimum_stock", 0)

        if min_stock <= 0:
            # If no minimum is set, consider >20 units as overstock
            return qty > 20

        return qty > (min_stock * 2.5)

    def get_item_status(self, item: dict) -> Tuple[str, str]:
        """Get status and color for an item.
        
        Returns:
            (status_text, color_code)
        """
        qty = item.get("current_quantity", 0)
        min_stock = item.get("minimum_stock", 0)
        exp = item.get("expiration_date", "")

        # Check expiration
        if exp:
            try:
                exp_d = datetime.date.fromisoformat(exp)
                today = datetime.date.today()
                diff = (exp_d - today).days
                if diff < 0:
                    return ("EXPIRED", "#ff6b6b")
                elif diff <= 14:
                    return ("EXPIRING", "#fbbf24")
            except ValueError:
                pass

        # Check stock levels
        if qty == 0:
            return ("OUT OF STOCK", "#fca5a5")
        elif qty <= min_stock:
            return ("LOW STOCK", "#fcd34d")
        elif self.detect_overstock(item):
            return ("OVERSTOCK", "#a78bfa")
        else:
            return ("OK", "#86efac")

    def get_shelf_capacity(self, items: List[dict]) -> Tuple[int, int]:
        """Calculate shelf capacity usage.
        
        Returns:
            (current_units, overstock_count)
        """
        total_units = sum(item.get("current_quantity", 0) for item in items)
        overstock_count = sum(1 for item in items if self.detect_overstock(item))
        return (total_units, overstock_count)

    def get_pantry_stats(self) -> dict:
        """Get overall pantry statistics."""
        all_items = []
        for section in self.sections.values():
            all_items.extend(section.get_all_items())

        total_items = len(all_items)
        total_units = sum(item.get("current_quantity", 0) for item in all_items)
        overstock_items = sum(1 for item in all_items if self.detect_overstock(item))
        out_of_stock = sum(1 for item in all_items if item.get("current_quantity", 0) == 0)
        low_stock = sum(1 for item in all_items if 0 < item.get("current_quantity", 0) <= item.get("minimum_stock", 0))

        return {
            "total_items": total_items,
            "total_units": total_units,
            "overstock_items": overstock_items,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "sections": len(self.sections),
        }
