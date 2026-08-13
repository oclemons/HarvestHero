"""
ai_prompts.py — System prompts and prompt library for Harvest AI.

Provides comprehensive system instructions for the AI assistant and
a library of suggested prompts organized by category.
"""

# ============================================================================
# SYSTEM PROMPT
# ============================================================================

HARVEST_AI_SYSTEM_PROMPT = """You are Harvest AI, a knowledgeable and friendly pantry operations assistant for the Harvest Hero inventory management system.

## IDENTITY
You are an AI assistant designed specifically to help food pantry staff and administrators understand and manage their pantry operations. You work for a community food pantry that serves clients in need.

## ROLE
Your primary role is to:
- Help staff and administrators understand current pantry conditions
- Answer questions about inventory status and locations
- Provide insights about distribution patterns and client needs
- Suggest operational priorities
- Explain inventory trends and anomalies
- Support decision-making with accurate data

## AVAILABLE DATA
You have access to live pantry data through backend tools:
- Current inventory status (quantities, stock levels, locations)
- Item details (names, barcodes, thresholds)
- Pantry sections and shelf organization
- Recent transactions and activity
- Client visit statistics
- Distribution summaries

## BUSINESS RULES
- Low Stock: Items below their configured low-stock threshold need restocking
- Overstock: Items above their overstock threshold may need redistribution
- Out of Stock: Items with zero quantity are unavailable
- Sections: Pantry is organized into sections (Dry Goods, Produce, etc.)
- Shelves: Each section contains numbered shelves for organization
- Clients: Pantry serves approved clients through scheduled visits

## SECURITY RULES
- NEVER reveal client personal information (names, addresses, phone numbers)
- NEVER reveal passwords, API keys, or system credentials
- NEVER modify data - you are READ-ONLY
- NEVER claim to have capabilities you don't have
- NEVER invent data - always use current database information
- Follow application authorization rules for all information access

## RESPONSE STYLE
- Be friendly and professional
- Use clear, concise language
- Provide actionable insights
- Prioritize accuracy over speculation
- When information is unavailable, clearly say so
- Use the pantry's harvest theme in your communication where appropriate
- Avoid jargon unless explaining technical concepts

## TOOL USAGE RULES
- Use available tools to get current data instead of guessing
- Call tools when you need specific information
- Combine multiple tool calls to build comprehensive answers
- Always verify data is current before providing it
- If a tool fails, explain what information you couldn't retrieve

## CONVERSATION CONTEXT
- Remember previous messages in the conversation
- Understand follow-up questions that reference earlier topics
- Build on context (e.g., if user asks about "rice", remember it in next question)
- Clarify ambiguous references when needed

## EXAMPLES

User: "What inventory needs attention?"
You: Call get_low_stock_items() and get_overstock_items(), then summarize findings.

User: "Where is tomato sauce?"
You: Call search_inventory("tomato sauce"), then get_item_location() for results.

User: "What changed today?"
You: Call get_recent_inventory_activity(days=1) and summarize changes.

User: "Give me a quick summary."
You: Call get_operational_summary() and present key metrics.

## PERSONALITY
- Warm and welcoming (reflecting the harvest theme)
- Calm and professional
- Helpful and supportive
- Knowledgeable about pantry operations
- Respectful of the community service mission

## IMPORTANT
- The application database is the source of truth
- Never contradict current database values
- Always prefer current data over historical information
- Help the pantry serve its community effectively
"""

# ============================================================================
# PROMPT LIBRARY
# ============================================================================

PROMPT_LIBRARY = {
    "TODAY": [
        {
            "label": "What needs attention today?",
            "prompt": "What inventory needs attention today? Please summarize the most urgent issues.",
            "icon": "⚠️",
        },
        {
            "label": "Give me today's summary",
            "prompt": "Give me today's pantry summary. What changed and what should I know?",
            "icon": "📊",
        },
        {
            "label": "What changed in inventory?",
            "prompt": "What changed in inventory today? Show me recent activity.",
            "icon": "📝",
        },
        {
            "label": "Are there urgent issues?",
            "prompt": "Are there any urgent stock problems I should address right now?",
            "icon": "🚨",
        },
    ],
    "INVENTORY": [
        {
            "label": "What items are low?",
            "prompt": "What items are currently below their low-stock threshold?",
            "icon": "📉",
        },
        {
            "label": "Show me overstock",
            "prompt": "Which items are currently overstocked? Show me everything above threshold.",
            "icon": "📦",
        },
        {
            "label": "Which section needs help?",
            "prompt": "Which pantry section needs the most attention right now?",
            "icon": "🏪",
        },
        {
            "label": "Which shelves have issues?",
            "prompt": "Which shelves have low-stock items? Give me a breakdown by section.",
            "icon": "📚",
        },
        {
            "label": "Healthiest sections?",
            "prompt": "Which sections are well-stocked and healthy right now?",
            "icon": "✅",
        },
        {
            "label": "Find an item",
            "prompt": "Where is [item name] located? How much do we have?",
            "icon": "🔍",
        },
    ],
    "OPERATIONS": [
        {
            "label": "Summarize operations",
            "prompt": "Give me an operational overview. What's the current state of the pantry?",
            "icon": "🎯",
        },
        {
            "label": "What should I prioritize?",
            "prompt": "What should staff prioritize right now? What's most important?",
            "icon": "⭐",
        },
        {
            "label": "Shift handoff summary",
            "prompt": "Give me a quick shift handoff summary. What should the next shift know?",
            "icon": "🔄",
        },
        {
            "label": "Explain operations",
            "prompt": "Explain the current state of pantry operations in simple terms.",
            "icon": "📋",
        },
    ],
    "DISTRIBUTION": [
        {
            "label": "Today's distributions",
            "prompt": "Summarize today's distributions. How many clients have we served?",
            "icon": "👥",
        },
        {
            "label": "Distribution impact",
            "prompt": "How has today's distribution affected our current stock levels?",
            "icon": "📊",
        },
        {
            "label": "Most distributed items",
            "prompt": "Which inventory categories were distributed the most today?",
            "icon": "🎁",
        },
    ],
    "ADMINISTRATION": [
        {
            "label": "Operational overview",
            "prompt": "Give me a comprehensive operational overview for management.",
            "icon": "📈",
        },
        {
            "label": "Major concerns",
            "prompt": "Summarize major inventory concerns that need management attention.",
            "icon": "⚡",
        },
        {
            "label": "Trends to review",
            "prompt": "What trends should I review? Are there patterns I should know about?",
            "icon": "📉",
        },
        {
            "label": "Unusual activity",
            "prompt": "Explain any unusual inventory activity from today.",
            "icon": "🔔",
        },
        {
            "label": "Management summary",
            "prompt": "Create a management summary of pantry operations and key metrics.",
            "icon": "📑",
        },
    ],
}

# ============================================================================
# CONTEXTUAL PROMPTS
# ============================================================================

CONTEXTUAL_PROMPTS = {
    "dashboard": [
        "What needs attention today?",
        "Give me today's summary.",
        "Are there urgent issues?",
    ],
    "inventory": [
        "What items are low?",
        "Show me overstock.",
        "Which section needs help?",
    ],
    "scan": [
        "What changed today?",
        "Summarize today's distributions.",
        "How has distribution affected stock?",
    ],
    "clients": [
        "How many clients today?",
        "What should we prioritize?",
        "Client visit statistics?",
    ],
    "reports": [
        "Operational overview?",
        "Major concerns?",
        "Trends to review?",
    ],
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_system_prompt() -> str:
    """Get the system prompt for Harvest AI.
    
    Returns:
        System prompt string
    """
    return HARVEST_AI_SYSTEM_PROMPT


def get_prompt_library() -> dict:
    """Get the complete prompt library.
    
    Returns:
        Dictionary of prompt categories and suggestions
    """
    return PROMPT_LIBRARY


def get_prompts_for_category(category: str) -> list:
    """Get prompts for a specific category.
    
    Args:
        category: Category name (TODAY, INVENTORY, OPERATIONS, etc.)
    
    Returns:
        List of prompts for that category
    """
    return PROMPT_LIBRARY.get(category.upper(), [])


def get_contextual_prompts(page: str) -> list:
    """Get suggested prompts for a specific page/context.
    
    Args:
        page: Current page (dashboard, inventory, scan, etc.)
    
    Returns:
        List of suggested prompts for that context
    """
    return CONTEXTUAL_PROMPTS.get(page.lower(), [])


def get_all_categories() -> list:
    """Get all available prompt categories.
    
    Returns:
        List of category names
    """
    return list(PROMPT_LIBRARY.keys())


def get_all_prompts() -> list:
    """Get all prompts across all categories.
    
    Returns:
        Flat list of all prompts
    """
    all_prompts = []
    for category_prompts in PROMPT_LIBRARY.values():
        all_prompts.extend(category_prompts)
    return all_prompts
