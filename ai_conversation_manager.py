"""
ai_conversation_manager.py — Multi-turn conversational AI with context management.

Provides:
- Multi-turn conversation support
- Conversation context tracking
- Conversation history
- Suggested follow-up prompts
- Backend tools for AI
- Conversation state management
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import json


@dataclass
class ConversationMessage:
    """Single message in conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Dict = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }


class ConversationContext:
    """Manages conversation context and state."""

    def __init__(self, db):
        self.db = db
        self.messages: List[ConversationMessage] = []
        self.conversation_id = None
        self.created_at = datetime.now()
        self.last_updated = datetime.now()

    def add_message(self, role: str, content: str, metadata: Dict = None):
        """Add message to conversation."""
        msg = ConversationMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.messages.append(msg)
        self.last_updated = datetime.now()

    def get_context_summary(self) -> str:
        """Get summary of conversation context."""
        if not self.messages:
            return "No conversation history."

        summary = f"Conversation started at {self.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        summary += f"Messages: {len(self.messages)}\n"
        summary += "Recent messages:\n"

        for msg in self.messages[-3:]:
            role = "User" if msg.role == "user" else "Assistant"
            summary += f"- {role}: {msg.content[:100]}...\n"

        return summary

    def get_system_prompt(self) -> str:
        """Get system prompt with context."""
        base_prompt = """You are Harvest AI, a helpful assistant for managing food pantries.
You have access to pantry data and can help with inventory management, client tracking, and operations.
Be concise, helpful, and professional. Always prioritize accuracy over speculation.
If you don't know something, say so clearly."""

        context = self.get_context_summary()
        return f"{base_prompt}\n\nCurrent context:\n{context}"

    def get_messages_for_api(self) -> List[Dict]:
        """Get messages formatted for OpenAI API."""
        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in self.messages
        ]

    def clear(self):
        """Clear conversation."""
        self.messages.clear()
        self.created_at = datetime.now()
        self.last_updated = datetime.now()


class AIToolsManager:
    """Manages backend tools available to AI."""

    def __init__(self, db):
        self.db = db
        self.tools = self._initialize_tools()

    def _initialize_tools(self) -> List[Dict]:
        """Initialize available tools."""
        return [
            {
                "name": "get_inventory_summary",
                "description": "Get summary of current inventory status",
                "parameters": {}
            },
            {
                "name": "get_low_stock_items",
                "description": "Get items that are low in stock",
                "parameters": {}
            },
            {
                "name": "get_overstock_items",
                "description": "Get items that are overstocked",
                "parameters": {}
            },
            {
                "name": "search_items",
                "description": "Search for items by name",
                "parameters": {"query": "string"}
            },
            {
                "name": "get_client_stats",
                "description": "Get statistics about clients and visits",
                "parameters": {}
            },
            {
                "name": "get_recent_activity",
                "description": "Get recent activity log",
                "parameters": {"limit": "integer"}
            },
            {
                "name": "get_distribution_summary",
                "description": "Get summary of recent distributions",
                "parameters": {}
            },
        ]

    def execute_tool(self, tool_name: str, parameters: Dict = None) -> str:
        """Execute a tool and return result."""
        try:
            if tool_name == "get_inventory_summary":
                return self._get_inventory_summary()
            elif tool_name == "get_low_stock_items":
                return self._get_low_stock_items()
            elif tool_name == "get_overstock_items":
                return self._get_overstock_items()
            elif tool_name == "search_items":
                query = (parameters or {}).get("query", "")
                return self._search_items(query)
            elif tool_name == "get_client_stats":
                return self._get_client_stats()
            elif tool_name == "get_recent_activity":
                limit = (parameters or {}).get("limit", 10)
                return self._get_recent_activity(limit)
            elif tool_name == "get_distribution_summary":
                return self._get_distribution_summary()
            else:
                return f"Unknown tool: {tool_name}"
        except Exception as e:
            return f"Error executing tool: {str(e)}"

    def _get_inventory_summary(self) -> str:
        """Get inventory summary."""
        try:
            stats = self.db.get_stats()
            return f"""Inventory Summary:
- Total Items: {stats.get('total_items', 0)}
- Total Quantity: {stats.get('total_quantity', 0)}
- Low Stock Items: {stats.get('low_stock_count', 0)}
- Out of Stock: {stats.get('out_of_stock_count', 0)}"""
        except Exception as e:
            return f"Unable to get inventory summary: {str(e)}"

    def _get_low_stock_items(self) -> str:
        """Get low stock items."""
        try:
            items = self.db.get_low_stock_items()
            if not items:
                return "No items are currently low in stock."
            result = "Low Stock Items:\n"
            for item in items[:10]:
                result += f"- {item['item_name']}: {item['current_quantity']} (min: {item['minimum_stock']})\n"
            return result
        except Exception as e:
            return f"Unable to get low stock items: {str(e)}"

    def _get_overstock_items(self) -> str:
        """Get overstock items."""
        try:
            items = self.db.get_overstock_items()
            if not items:
                return "No items are currently overstocked."
            result = "Overstock Items:\n"
            for item in items[:10]:
                result += f"- {item['item_name']}: {item['current_quantity']} (max: {item['overstock_threshold']})\n"
            return result
        except Exception as e:
            return f"Unable to get overstock items: {str(e)}"

    def _search_items(self, query: str) -> str:
        """Search for items."""
        try:
            items = self.db.search_items(query)
            if not items:
                return f"No items found matching '{query}'."
            result = f"Items matching '{query}':\n"
            for item in items[:10]:
                result += f"- {item['item_name']}: {item['current_quantity']} units\n"
            return result
        except Exception as e:
            return f"Unable to search items: {str(e)}"

    def _get_client_stats(self) -> str:
        """Get client statistics."""
        try:
            clients = self.db.get_all_clients()
            visits = self.db.get_all_visits()
            return f"""Client Statistics:
- Total Clients: {len(clients) if clients else 0}
- Total Visits: {len(visits) if visits else 0}
- Active Clients: {sum(1 for c in (clients or []) if c.get('is_active'))}"""
        except Exception as e:
            return f"Unable to get client stats: {str(e)}"

    def _get_recent_activity(self, limit: int = 10) -> str:
        """Get recent activity."""
        try:
            activity = self.db.get_activity_log(limit=limit)
            if not activity:
                return "No recent activity."
            result = "Recent Activity:\n"
            for entry in activity[:limit]:
                result += f"- {entry['action']} by {entry['username']} at {entry['timestamp']}\n"
            return result
        except Exception as e:
            return f"Unable to get recent activity: {str(e)}"

    def _get_distribution_summary(self) -> str:
        """Get distribution summary."""
        try:
            txns = self.db.get_recent_transactions(100)
            out_txns = [t for t in txns if t['transaction_type'] == 'SCAN_OUT']
            total_distributed = sum(t['quantity'] for t in out_txns)
            return f"""Distribution Summary:
- Items Distributed (recent): {total_distributed} units
- Distribution Events: {len(out_txns)}
- Top Item Distributed: {max((t['item_name'] for t in out_txns), default='N/A')}"""
        except Exception as e:
            return f"Unable to get distribution summary: {str(e)}"


class ConversationManager:
    """Manages multi-turn conversations with context."""

    def __init__(self, db):
        self.db = db
        self.context = ConversationContext(db)
        self.tools_manager = AIToolsManager(db)
        self.conversations: Dict[str, ConversationContext] = {}

    def start_conversation(self) -> str:
        """Start a new conversation."""
        self.context = ConversationContext(self.db)
        return "Conversation started. How can I help you with your pantry today?"

    def add_user_message(self, message: str):
        """Add user message to conversation."""
        self.context.add_message("user", message)

    def add_assistant_message(self, message: str, metadata: Dict = None):
        """Add assistant message to conversation."""
        self.context.add_message("assistant", message, metadata)

    def get_conversation_history(self) -> List[Dict]:
        """Get full conversation history."""
        return [msg.to_dict() for msg in self.context.messages]

    def get_suggested_follow_ups(self, last_response: str) -> List[str]:
        """Get suggested follow-up prompts based on last response."""
        suggestions = []

        if "low stock" in last_response.lower():
            suggestions.append("What should we order to restock?")
            suggestions.append("Which items are most critical?")

        if "client" in last_response.lower():
            suggestions.append("How many clients visited this week?")
            suggestions.append("What's the most popular item?")

        if "inventory" in last_response.lower():
            suggestions.append("Show me overstock items")
            suggestions.append("What's our total inventory value?")

        if not suggestions:
            suggestions = [
                "What items are low in stock?",
                "Show me recent activity",
                "How many clients visited today?",
            ]

        return suggestions[:3]

    def clear_conversation(self):
        """Clear current conversation."""
        self.context.clear()

    def get_system_prompt(self) -> str:
        """Get system prompt with context."""
        return self.context.get_system_prompt()

    def get_messages_for_api(self) -> List[Dict]:
        """Get messages for OpenAI API."""
        return self.context.get_messages_for_api()
