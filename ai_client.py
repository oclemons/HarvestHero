"""ai_client.py — Cloud OpenAI integration for Harvest Hero insights.

Loads the API key from OpenAI.env (never committed) and provides helpers to
generate plain-language inventory insights and answer plain-language questions.
"""

import json
import os
import sys
from typing import Any, List, Dict, Optional

import requests

from paths import APP_DIR, USER_DIR
from ai_tools import AIToolsManager
from ai_prompts import get_system_prompt

_OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
_DASHBOARD_MODEL = "gpt-4o-mini"
_ASK_MODEL = "gpt-4o-mini"


def _load_api_key() -> str | None:
    # 1. Environment variable
    env = os.environ.get("OPENAI_API_KEY")
    if env:
        return env

    # 2. On-disk key file. Constrain the search:
    #   - In a frozen .app the key MUST live in USER_DIR (per-user data);
    #     walking parent directories of the executable would let the
    #     key be picked up from a shared /Applications folder or from
    #     any other bundle a user happens to have installed.
    #   - In a dev checkout, also allow APP_DIR (the project root)
    #     because that's where developers typically drop the file.
    if getattr(sys, "frozen", False):
        candidates = [USER_DIR]
    else:
        candidates = [USER_DIR, APP_DIR]

    for folder in candidates:
        path = os.path.join(folder, "OpenAI.env")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    raw = line.strip()
                    if not raw or raw.startswith("#"):
                        continue
                    # Format: OPENAI_API_KEY=sk-...
                    if "=" in raw:
                        key, _, value = raw.partition("=")
                        if key.strip() == "OPENAI_API_KEY":
                            return value.strip().strip("'\"\n")
                    # Format: bare token on its own line
                    if raw.startswith("sk-"):
                        return raw
        except Exception:
            continue
    return None


def _build_context(db) -> str:
    """Create a concise, structured summary of current inventory data."""
    stats = db.get_stats()
    low_stock = db.get_low_stock_items()
    out_of_stock = db.get_out_of_stock_items()
    expiring = db.get_expiring_items(30)
    expired = db.get_expired_items()
    recent_txns = db.get_recent_transactions(100)

    in_total = sum(t["quantity"] for t in recent_txns if t["transaction_type"] == "SCAN_IN")
    out_total = sum(t["quantity"] for t in recent_txns if t["transaction_type"] == "SCAN_OUT")
    top_out = {}
    for t in recent_txns:
        if t["transaction_type"] == "SCAN_OUT":
            top_out[t["item_name"]] = top_out.get(t["item_name"], 0) + t["quantity"]
    top_out = sorted(top_out.items(), key=lambda x: x[1], reverse=True)[:10]

    context = {
        "total_items": stats.get("total_items", 0),
        "total_units": stats.get("total_units", 0),
        "low_stock_count": stats.get("low_stock", 0),
        "out_of_stock_count": stats.get("out_of_stock", 0),
        "today_in_count": stats.get("today_in_count", 0),
        "today_in_qty": stats.get("today_in_qty", 0),
        "today_out_count": stats.get("today_out_count", 0),
        "today_out_qty": stats.get("today_out_qty", 0),
        "recent_in_total": in_total,
        "recent_out_total": out_total,
        "low_stock_items": [i["item_name"] for i in low_stock[:15]],
        "out_of_stock_items": [i["item_name"] for i in out_of_stock[:15]],
        "expiring_30_days_count": len(expiring),
        "expiring_items": [i["item_name"] for i in expiring[:15]],
        "expired_count": len(expired),
        "expired_items": [i["item_name"] for i in expired[:10]],
        "top_distributed_recent": top_out,
    }
    return json.dumps(context, indent=2)


def _call_openai(messages: List[Dict[str, str]], model: str, temperature: float = 0.2,
                 max_tokens: int = 800) -> str | None:
    key = _load_api_key()
    if not key:
        return None
    try:
        resp = requests.post(
            _OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception:
        return None


def _parse_json_list(text: str) -> List[Dict[str, Any]] | None:
    if not text:
        return None
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = text.split("```", 2)[-1] if text.count("```") >= 2 else text
        text = text.replace("json", "", 1).strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return None


def _fallback_insights(db) -> List[Dict[str, Any]]:
    """Rule-based insight fallback when the API is unavailable."""
    insights = []
    low = db.get_low_stock_items()
    out = db.get_out_of_stock_items()
    expiring = db.get_expiring_items(30)
    expired = db.get_expired_items()
    stats = db.get_stats()

    if out:
        insights.append({
            "title": "Out-of-stock items",
            "explanation": f"{len(out)} item(s) currently have zero quantity, including {', '.join(i['item_name'] for i in out[:5])}.",
            "severity": "critical",
            "action": "Review inventory and request donor donations.",
        })
    if low:
        insights.append({
            "title": "Low-stock warning",
            "explanation": f"{len(low)} item(s) are at or below minimum stock.",
            "severity": "action",
            "action": "Prioritize restocking these items before the next distribution.",
        })
    if expiring:
        insights.append({
            "title": "Expiration risk",
            "explanation": f"{len(expiring)} item(s) will expire within 30 days.",
            "severity": "action",
            "action": "Distribute expiring items first.",
        })
    if expired:
        insights.append({
            "title": "Expired inventory",
            "explanation": f"{len(expired)} item(s) are past their expiration date.",
            "severity": "critical",
            "action": "Remove expired items from inventory.",
        })
    recent_out = sum(t["quantity"] for t in db.get_recent_transactions(30)
                     if t["transaction_type"] == "SCAN_OUT")
    if recent_out == 0:
        insights.append({
            "title": "No recent distributions",
            "explanation": "There have been no scan-out transactions in the last 30 days.",
            "severity": "info",
            "action": "Check whether activity is being recorded.",
        })

    return insights[:5]


def get_insights(db, limit: int = 5) -> List[Dict[str, Any]]:
    """Return up to `limit` dashboard insights using the OpenAI API or fallback rules."""
    context = _build_context(db)
    system = (
        "You are an AI inventory assistant for a nonprofit food and supply pantry. "
        "You analyze real inventory data and produce useful, prioritized operational insights. "
        "You must base your answer only on the data provided. Never invent numbers or items. "
        "Return only a JSON list. Each object must have exactly these keys: "
        "title (string), explanation (string), severity (one of: critical, action, monitor, info), "
        "action (string). Keep each explanation to 1-2 sentences. Recommend only 1 concrete next step. "
        "Return at most the requested number of insights and order them from most to least urgent."
    )
    user = (
        f"Current inventory data:\n{context}\n\n"
        f"Generate at most {limit} high-value dashboard insights in the requested JSON format."
    )
    content = _call_openai(
        [{"role": "system", "content": system},
         {"role": "user", "content": user}],
        model=_DASHBOARD_MODEL,
    )
    insights = _parse_json_list(content)
    if insights:
        return insights[:limit]
    return _fallback_insights(db)[:limit]


def ask_question(db, question: str) -> str:
    """Answer a plain-language inventory question using current data and OpenAI."""
    context = _build_context(db)
    system = (
        "You are an AI inventory assistant for a nonprofit pantry. "
        "Answer questions using only the data provided. If the data cannot answer the question, say so. "
        "Cite the specific numbers or items you used. Keep answers concise and practical."
    )
    user = f"Current inventory data:\n{context}\n\nQuestion: {question}"
    content = _call_openai(
        [{"role": "system", "content": system},
         {"role": "user", "content": user}],
        model=_ASK_MODEL,
        temperature=0.3,
        max_tokens=600,
    )
    if content:
        return content
    return "Sorry, the AI assistant is not available right now. Please try again later."


# ============================================================================
# CONVERSATIONAL AI WITH BACKEND TOOLS
# ============================================================================

def answer_with_tools(db, question: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
    """Answer a question using Harvest AI with backend tools for live data.
    
    This is the primary conversational interface that allows multi-turn
    conversations with context awareness and live pantry data access.
    
    Args:
        db: Database instance
        question: User's question
        conversation_history: Previous messages for context (optional)
    
    Returns:
        AI response string
    """
    tools_manager = AIToolsManager(db)
    
    # Build messages with conversation history
    messages = []
    
    # Add system prompt
    messages.append({
        "role": "system",
        "content": get_system_prompt()
    })
    
    # Add conversation history if provided
    if conversation_history:
        messages.extend(conversation_history)
    
    # Add current question
    messages.append({
        "role": "user",
        "content": question
    })
    
    # Call OpenAI with tools
    key = _load_api_key()
    if not key:
        return _fallback_answer(db, question)
    
    try:
        resp = requests.post(
            _OPENAI_CHAT_URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": _ASK_MODEL,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1000,
            },
            timeout=20,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        if content:
            return content
    except Exception:
        pass
    
    return _fallback_answer(db, question)


def _fallback_answer(db, question: str) -> str:
    """Fallback answer when OpenAI is unavailable.
    
    Uses rule-based logic to answer common questions about inventory.
    """
    question_lower = question.lower()
    
    # Inventory summary
    if any(word in question_lower for word in ["summary", "overview", "status", "health"]):
        stats = db.get_stats()
        return (
            f"**Pantry Status Summary**\n\n"
            f"Total Items: {stats.get('total_items', 0)}\n"
            f"In Stock: {stats.get('in_stock', 0)}\n"
            f"Low Stock: {stats.get('low_stock', 0)}\n"
            f"Out of Stock: {stats.get('out_of_stock', 0)}\n\n"
            f"Your pantry tools are still available. The AI assistant is temporarily offline."
        )
    
    # Low stock items
    if any(word in question_lower for word in ["low", "restock", "below"]):
        low_items = db.get_low_stock_items()
        if low_items:
            items_str = ", ".join(i["item_name"] for i in low_items[:5])
            return f"Low-stock items: {items_str}. Total: {len(low_items)} items need restocking."
        return "No items are currently below their low-stock threshold."
    
    # Out of stock
    if any(word in question_lower for word in ["out", "empty", "zero"]):
        out_items = db.get_out_of_stock_items()
        if out_items:
            items_str = ", ".join(i["item_name"] for i in out_items[:5])
            return f"Out-of-stock items: {items_str}. Total: {len(out_items)} items are unavailable."
        return "All items currently have stock available."
    
    # Default fallback
    return (
        "The AI assistant is temporarily unavailable. "
        "Your pantry tools are still fully functional. "
        "Please try again later or use the inventory management features directly."
    )


def get_conversation_starter_prompts(page: str = None) -> List[str]:
    """Get suggested prompts for starting a conversation.
    
    Args:
        page: Current page context (optional)
    
    Returns:
        List of suggested prompt strings
    """
    from ai_prompts import get_contextual_prompts, get_all_prompts
    
    if page:
        contextual = get_contextual_prompts(page)
        if contextual:
            return [p["prompt"] for p in contextual]
    
    # Return first 5 prompts from library
    all_prompts = get_all_prompts()
    return [p["prompt"] for p in all_prompts[:5]]
