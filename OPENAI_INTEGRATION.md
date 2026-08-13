# OpenAI Integration Guide

This guide explains how to properly integrate OpenAI with Harvest Hero for inventory intelligence and analysis.

## Quick Start

### 1. Get Your API Key

1. Go to [OpenAI Platform](https://platform.openai.com/api/keys)
2. Sign in or create an account
3. Click "Create new secret key"
4. Copy the key (starts with `sk-`)

### 2. Add API Key to Application

**Option A: Environment File (Recommended)**

Create a file named `OpenAI.env` in the project root:

```
OPENAI_API_KEY=sk-your-actual-key-here
```

**Option B: Environment Variable**

Set the environment variable before running:

```bash
export OPENAI_API_KEY=sk-your-actual-key-here
python run.py
```

### 3. Use in Your Code

```python
from ai_client import _call_openai, _build_context

# Get inventory context
context = _build_context(db)

# Ask a question
messages = [
    {"role": "system", "content": "You are an inventory assistant for a food pantry."},
    {"role": "user", "content": f"Based on this inventory: {context}\n\nWhat should we reorder?"}
]

response = _call_openai(messages, model="gpt-4o-mini")
print(response)
```

## Correct API Usage

### ❌ WRONG - Don't Do This

```python
from openai import OpenAI

client = OpenAI()

# This endpoint doesn't exist
response = client.responses.create(
    model="gpt-5.6",  # This model doesn't exist
    instructions="...",  # Wrong parameter
    input=inventory_data
)
```

### ✅ CORRECT - Do This

```python
from ai_client import _call_openai

messages = [
    {"role": "system", "content": "You are an inventory assistant."},
    {"role": "user", "content": "Analyze this inventory data..."}
]

response = _call_openai(
    messages=messages,
    model="gpt-4o-mini",  # Valid model
    temperature=0.2,
    max_tokens=800
)
```

## Available Models

| Model | Cost | Speed | Quality | Best For |
|-------|------|-------|---------|----------|
| `gpt-4o-mini` | $0.15/1M input | Fast | Good | Dashboard insights, quick analysis |
| `gpt-4o` | $5/1M input | Medium | Excellent | Complex analysis, detailed insights |
| `gpt-3.5-turbo` | $0.50/1M input | Very Fast | Fair | Simple tasks, low cost |

**Current app uses:** `gpt-4o-mini` (best balance of cost and quality)

## How the App Uses OpenAI

### 1. Dashboard Insights

The AI Command tab uses OpenAI to analyze inventory patterns:

```python
# From ai_assistant.py
def _get_openai_insights(db):
    context = _build_context(db)
    messages = [
        {"role": "system", "content": "You are a pantry inventory expert..."},
        {"role": "user", "content": f"Analyze this inventory:\n{context}"}
    ]
    return _call_openai(messages, model="gpt-4o-mini")
```

### 2. Question Answering

Users can ask questions about inventory:

```python
# User asks: "What items are we running out of?"
# App builds context and sends to OpenAI
# OpenAI returns natural language answer
```

### 3. Recommendations

AI provides actionable recommendations:

- "Rice is running out in 3 days, order 50 units"
- "Corn has been over-ordered, reduce next order"
- "Expiring items: Milk expires tomorrow, distribute first"

## Building Context for OpenAI

The app automatically builds a structured summary of inventory data:

```python
from ai_client import _build_context

context = _build_context(db)
# Returns JSON with:
# - Total items and units
# - Low stock items
# - Out of stock items
# - Expiring items
# - Recent transactions
# - Top distributed items
```

Example context:

```json
{
  "total_items": 121,
  "total_units": 450,
  "low_stock_count": 5,
  "out_of_stock_count": 120,
  "today_in_count": 2,
  "today_in_qty": 15,
  "today_out_count": 3,
  "today_out_qty": 8,
  "low_stock_items": ["Rice", "Beans", "Pasta"],
  "out_of_stock_items": ["Milk", "Eggs"],
  "expiring_items": ["Yogurt", "Cheese"],
  "top_distributed_recent": [["Rice", 45], ["Beans", 32]]
}
```

## API Endpoints

### Chat Completions (Used by App)

```python
POST https://api.openai.com/v1/chat/completions

{
    "model": "gpt-4o-mini",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
    ],
    "temperature": 0.2,
    "max_tokens": 800
}
```

**Response:**

```json
{
    "choices": [
        {
            "message": {
                "content": "Here are my recommendations..."
            }
        }
    ]
}
```

## System Prompts

The app uses specific system prompts for different tasks:

### Dashboard Analysis

```
You are an inventory intelligence assistant for a food pantry.
Analyze the provided inventory data and provide:
1. Current status summary
2. Critical issues (out of stock, expiring)
3. Actionable recommendations
4. Consumption trends

Be concise and focus on what needs immediate attention.
```

### Question Answering

```
You are a helpful inventory assistant for a food pantry.
Answer questions about inventory status, trends, and recommendations.
Use the provided inventory context to give accurate answers.
Be specific with numbers and timeframes.
```

## Error Handling

The app gracefully handles API failures:

```python
response = _call_openai(messages, model="gpt-4o-mini")

if response is None:
    # API key missing or API call failed
    # Fall back to rule-based insights
    use_fallback_insights()
else:
    # Use OpenAI response
    display_insights(response)
```

## Cost Estimation

**gpt-4o-mini pricing:**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

**Typical usage:**
- Dashboard refresh: ~500 input tokens, ~200 output tokens
- Cost per refresh: ~$0.0001 (0.01 cents)
- 100 refreshes per day: ~$0.01 per day

**Monthly estimate:** ~$0.30 for typical pantry usage

## Troubleshooting

### "API key not found"

1. Check `OpenAI.env` exists in project root
2. Verify format: `OPENAI_API_KEY=sk-...`
3. Check environment variable is set
4. Restart application

### "API call failed"

1. Check internet connection
2. Verify API key is valid (not expired)
3. Check OpenAI account has credits
4. Check rate limits (120 requests/minute)

### "No response from OpenAI"

The app automatically falls back to rule-based insights if:
- API key is missing
- API call times out
- Network error occurs
- API returns an error

### "Response is incomplete"

Increase `max_tokens` parameter:

```python
response = _call_openai(
    messages=messages,
    model="gpt-4o-mini",
    max_tokens=1500  # Increased from 800
)
```

## Advanced Usage

### Custom Analysis

```python
from ai_client import _call_openai, _build_context

def analyze_consumption_trends(db):
    context = _build_context(db)
    messages = [
        {"role": "system", "content": "You are a data analyst for food distribution."},
        {"role": "user", "content": f"""
        Analyze consumption trends in this inventory:
        {context}
        
        Provide:
        1. Items with rising consumption
        2. Items with falling consumption
        3. Seasonal patterns
        4. Recommendations for ordering
        """}
    ]
    return _call_openai(messages, model="gpt-4o-mini")

# Usage
trends = analyze_consumption_trends(db)
print(trends)
```

### Batch Analysis

```python
def analyze_multiple_questions(db, questions):
    context = _build_context(db)
    results = {}
    
    for question in questions:
        messages = [
            {"role": "system", "content": "You are a pantry inventory expert."},
            {"role": "user", "content": f"{context}\n\n{question}"}
        ]
        results[question] = _call_openai(messages, model="gpt-4o-mini")
    
    return results

# Usage
questions = [
    "What should we order this week?",
    "Which items are expiring soon?",
    "What's our consumption trend?"
]
answers = analyze_multiple_questions(db, questions)
```

## Best Practices

### 1. Cache Context

```python
# Don't rebuild context for every call
context = _build_context(db)

# Reuse for multiple questions
for question in questions:
    messages = [
        {"role": "system", "content": "..."},
        {"role": "user", "content": f"{context}\n\n{question}"}
    ]
    response = _call_openai(messages)
```

### 2. Set Appropriate Temperature

```python
# For consistent, factual responses (analysis)
_call_openai(messages, temperature=0.2)

# For creative, varied responses (brainstorming)
_call_openai(messages, temperature=0.8)
```

### 3. Limit Max Tokens

```python
# Short responses
_call_openai(messages, max_tokens=200)

# Detailed responses
_call_openai(messages, max_tokens=1500)
```

### 4. Handle Timeouts

```python
try:
    response = _call_openai(messages, model="gpt-4o-mini")
except TimeoutError:
    # Use fallback
    response = fallback_insights(db)
```

## Security

### API Key Safety

✅ **DO:**
- Store in `OpenAI.env` (git-ignored)
- Use environment variables in production
- Rotate keys regularly
- Limit key permissions in OpenAI dashboard

❌ **DON'T:**
- Commit API key to git
- Share API key in messages/emails
- Use in client-side code
- Log API key in error messages

### Data Privacy

- Inventory data is sent to OpenAI for analysis
- OpenAI retains data for 30 days by default
- For sensitive data, use OpenAI's privacy controls
- Consider on-premise alternatives for highly sensitive data

## Files Involved

| File | Purpose |
|------|---------|
| `ai_client.py` | OpenAI API integration |
| `ai_assistant.py` | UI and pattern analysis |
| `OpenAI.env` | API key storage (git-ignored) |

## Summary

**Correct way to use OpenAI:**

```python
from ai_client import _call_openai, _build_context

# 1. Build inventory context
context = _build_context(db)

# 2. Create messages
messages = [
    {"role": "system", "content": "You are a pantry inventory expert."},
    {"role": "user", "content": f"Analyze: {context}"}
]

# 3. Call OpenAI
response = _call_openai(
    messages=messages,
    model="gpt-4o-mini",
    temperature=0.2,
    max_tokens=800
)

# 4. Use response
print(response)
```

That's it! The app handles the rest automatically.
