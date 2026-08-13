"""
intake_cart.py — Shopping cart system for intake transactions.

Allows staff to:
1. Select a client
2. Scan multiple items
3. Build a cart
4. Complete transaction
5. Track distribution history
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class CartItem:
    """Represents an item in the intake cart."""
    item_id: int
    barcode: str
    item_name: str
    quantity: int = 1
    category: str = ""
    storage_location: str = ""
    added_at: datetime = field(default_factory=datetime.now)


@dataclass
class IntakeTransaction:
    """Represents a complete intake transaction."""
    client_id: int
    client_name: str
    items: List[CartItem] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    notes: str = ""
    total_items: int = 0


class IntakeCart:
    """Shopping cart for intake transactions."""

    def __init__(self, db):
        """Initialize intake cart.
        
        Args:
            db: Database instance
        """
        self.db = db
        self.current_transaction: Optional[IntakeTransaction] = None
        self.cart_items: Dict[str, CartItem] = {}  # barcode -> CartItem

    def start_transaction(self, client_id: int, client_name: str) -> Tuple[bool, str]:
        """Start a new intake transaction.
        
        Args:
            client_id: Client ID
            client_name: Client name
            
        Returns:
            (success, message)
        """
        if self.current_transaction is not None:
            return (False, "Transaction already in progress. Complete or cancel first.")
        
        if not client_id or not client_name:
            return (False, "Client ID and name are required")
        
        self.current_transaction = IntakeTransaction(
            client_id=client_id,
            client_name=client_name
        )
        self.cart_items = {}
        
        return (True, f"Transaction started for {client_name}")

    def add_item(self, item_id: int, barcode: str, item_name: str, 
                 quantity: int = 1, category: str = "", 
                 storage_location: str = "") -> Tuple[bool, str]:
        """Add item to cart.
        
        Args:
            item_id: Item ID
            barcode: Item barcode
            item_name: Item name
            quantity: Quantity to add (default 1)
            category: Item category
            storage_location: Storage location
            
        Returns:
            (success, message)
        """
        if not self.current_transaction:
            return (False, "No transaction in progress. Start a transaction first.")
        
        if quantity <= 0:
            return (False, "Quantity must be greater than 0")
        
        # If item already in cart, increase quantity
        if barcode in self.cart_items:
            self.cart_items[barcode].quantity += quantity
            return (True, f"Updated {item_name} to {self.cart_items[barcode].quantity} units")
        
        # Add new item
        cart_item = CartItem(
            item_id=item_id,
            barcode=barcode,
            item_name=item_name,
            quantity=quantity,
            category=category,
            storage_location=storage_location
        )
        self.cart_items[barcode] = cart_item
        
        return (True, f"Added {item_name} ({quantity} units) to cart")

    def remove_item(self, barcode: str) -> Tuple[bool, str]:
        """Remove item from cart.
        
        Args:
            barcode: Item barcode
            
        Returns:
            (success, message)
        """
        if not self.current_transaction:
            return (False, "No transaction in progress")
        
        if barcode not in self.cart_items:
            return (False, "Item not in cart")
        
        item_name = self.cart_items[barcode].item_name
        del self.cart_items[barcode]
        
        return (True, f"Removed {item_name} from cart")

    def update_quantity(self, barcode: str, quantity: int) -> Tuple[bool, str]:
        """Update item quantity in cart.
        
        Args:
            barcode: Item barcode
            quantity: New quantity
            
        Returns:
            (success, message)
        """
        if not self.current_transaction:
            return (False, "No transaction in progress")
        
        if barcode not in self.cart_items:
            return (False, "Item not in cart")
        
        if quantity <= 0:
            return self.remove_item(barcode)
        
        item_name = self.cart_items[barcode].item_name
        self.cart_items[barcode].quantity = quantity
        
        return (True, f"Updated {item_name} to {quantity} units")

    def get_cart_items(self) -> List[CartItem]:
        """Get all items in cart.
        
        Returns:
            List of CartItem objects
        """
        return list(self.cart_items.values())

    def get_cart_summary(self) -> Dict:
        """Get cart summary.
        
        Returns:
            Dictionary with cart information
        """
        if not self.current_transaction:
            return {"error": "No transaction in progress"}
        
        items = self.get_cart_items()
        total_units = sum(item.quantity for item in items)
        
        return {
            "client_id": self.current_transaction.client_id,
            "client_name": self.current_transaction.client_name,
            "item_count": len(items),
            "total_units": total_units,
            "items": [
                {
                    "barcode": item.barcode,
                    "item_name": item.item_name,
                    "quantity": item.quantity,
                    "category": item.category,
                    "storage_location": item.storage_location
                }
                for item in items
            ],
            "created_at": self.current_transaction.created_at.isoformat()
        }

    def complete_transaction(self, notes: str = "") -> Tuple[bool, str, Optional[Dict]]:
        """Complete the intake transaction.
        
        Args:
            notes: Optional transaction notes
            
        Returns:
            (success, message, transaction_data)
        """
        if not self.current_transaction:
            return (False, "No transaction in progress", None)
        
        if not self.cart_items:
            return (False, "Cart is empty. Add items before completing.", None)
        
        try:
            # Update inventory for each item
            for barcode, cart_item in self.cart_items.items():
                try:
                    # Add to inventory (increase quantity)
                    self.db.adjust_stock(barcode, cart_item.quantity)
                except Exception as e:
                    print(f"Error updating {cart_item.item_name}: {e}")
            
            # Record transaction
            transaction_data = {
                "client_id": self.current_transaction.client_id,
                "client_name": self.current_transaction.client_name,
                "items": [
                    {
                        "item_id": item.item_id,
                        "barcode": item.barcode,
                        "item_name": item.item_name,
                        "quantity": item.quantity
                    }
                    for item in self.cart_items.values()
                ],
                "total_items": len(self.cart_items),
                "total_units": sum(item.quantity for item in self.cart_items.values()),
                "notes": notes,
                "completed_at": datetime.now().isoformat()
            }
            
            # Clear transaction
            self.current_transaction = None
            self.cart_items = {}
            
            return (True, "Transaction completed successfully", transaction_data)
        except Exception as e:
            return (False, f"Error completing transaction: {str(e)}", None)

    def cancel_transaction(self) -> Tuple[bool, str]:
        """Cancel the current transaction.
        
        Returns:
            (success, message)
        """
        if not self.current_transaction:
            return (False, "No transaction in progress")
        
        client_name = self.current_transaction.client_name
        self.current_transaction = None
        self.cart_items = {}
        
        return (True, f"Transaction cancelled for {client_name}")

    def is_transaction_active(self) -> bool:
        """Check if transaction is active.
        
        Returns:
            True if transaction is active
        """
        return self.current_transaction is not None

    def get_current_client(self) -> Optional[Tuple[int, str]]:
        """Get current client info.
        
        Returns:
            (client_id, client_name) or None
        """
        if not self.current_transaction:
            return None
        
        return (self.current_transaction.client_id, self.current_transaction.client_name)

    def clear_cart(self) -> Tuple[bool, str]:
        """Clear all items from cart but keep transaction active.
        
        Returns:
            (success, message)
        """
        if not self.current_transaction:
            return (False, "No transaction in progress")
        
        self.cart_items = {}
        return (True, "Cart cleared")

    def get_item_in_cart(self, barcode: str) -> Optional[CartItem]:
        """Get item from cart by barcode.
        
        Args:
            barcode: Item barcode
            
        Returns:
            CartItem or None
        """
        return self.cart_items.get(barcode)

    def is_item_in_cart(self, barcode: str) -> bool:
        """Check if item is in cart.
        
        Args:
            barcode: Item barcode
            
        Returns:
            True if item is in cart
        """
        return barcode in self.cart_items
