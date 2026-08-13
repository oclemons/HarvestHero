# OpenAI Integration Troubleshooting

## Current Status

**API Key:** ✓ Loaded successfully  
**API Connection:** ✗ Failed (401 Unauthorized)  
**Issue:** API key is invalid or expired

## Common Issues & Solutions

### 1. Invalid or Expired API Key

**Error:** `401 Unauthorized - Incorrect API key provided`

**Causes:**
- API key has expired
- API key was revoked
- API key is incorrect/malformed
- Wrong API key format

**Solutions:**

1. **Check your API key on OpenAI website:**
   - Go to https://platform.openai.com/account/api-keys
   - Sign in to your OpenAI account
   - Check if your key is still active
   - If expired, delete it and create a new one

2. **Update OpenAI.env with new key:**
   ```
   OPENAI_API_KEY=sk-proj-your-new-key-here
   ```

3. **Verify key format:**
   - Should start with `sk-proj-` (for project keys) or `sk-` (for legacy keys)
   - Should be a long string (100+ characters)
   - No spaces or special characters

4. **Restart the application:**
   - Close Harvest Hero completely
   - Open it again
   - The new key will be loaded

### 2. No Credits on OpenAI Account

**Error:** `429 Rate Limit Exceeded` or `Quota exceeded`

**Solutions:**

1. **Check your OpenAI account balance:**
   - Go to https://platform.openai.com/account/billing/overview
   - Check "Credits" section
   - Add payment method if needed

2. **Add billing information:**
   - Go to https://platform.openai.com/account/billing/overview
   - Click "Set up paid account"
   - Add credit card
   - Set usage limits if desired

3. **Check usage:**
   - Go to https://platform.openai.com/account/billing/usage
   - See how much you've used
   - Adjust limits if needed

### 3. Network Connection Issues

**Error:** `Connection timeout` or `Network unreachable`

**Solutions:**

1. **Check internet connection:**
   ```bash
   ping google.com
   ```

2. **Check if OpenAI API is accessible:**
   ```bash
   curl https://api.openai.com/v1/models -H "Authorization: Bearer YOUR_KEY"
   ```

3. **Check firewall/proxy:**
   - Ensure OpenAI API is not blocked
   - Check corporate firewall settings
   - Disable VPN if using one

### 4. API Key Not Found

**Error:** `API Key NOT found`

**Solutions:**

1. **Verify OpenAI.env exists:**
   ```bash
   ls -la OpenAI.env
   ```

2. **Check file format:**
   ```bash
   cat OpenAI.env
   ```
   Should show:
   ```
   OPENAI_API_KEY=sk-proj-...
   ```

3. **Create OpenAI.env if missing:**
   ```bash
   echo "OPENAI_API_KEY=sk-proj-your-key-here" > OpenAI.env
   ```

4. **Check file permissions:**
   ```bash
   chmod 600 OpenAI.env
   ```

### 5. Wrong Model Name

**Error:** `Model not found` or `Invalid model`

**Valid models:**
- `gpt-4o` (latest, most capable)
- `gpt-4o-mini` (fast, affordable) ← **Currently used**
- `gpt-3.5-turbo` (legacy, cheap)

**Solution:**
The app uses `gpt-4o-mini` which is correct. If you want to change it, edit `ai_client.py`:
```python
_ASK_MODEL = "gpt-4o-mini"  # Change this if needed
```

## Testing the Integration

### Quick Test

Run this command to test if OpenAI is working:

```bash
cd /Users/octayviaclemons/CascadeProjects/inventory_tracker
python << 'EOF'
import sys
sys.path.insert(0, '.')
from ai_client import _load_api_key, _call_openai

key = _load_api_key()
print(f"API Key loaded: {bool(key)}")

if key:
    response = _call_openai(
        [{"role": "user", "content": "Say hello"}],
        model="gpt-4o-mini"
    )
    print(f"Response: {response}")
EOF
```

### Full Integration Test

```bash
python << 'EOF'
import sys
sys.path.insert(0, '.')

print("Testing OpenAI Integration...")

# 1. Check API key
from ai_client import _load_api_key
key = _load_api_key()
print(f"1. API Key: {'✓' if key else '✗'}")

# 2. Test API call
if key:
    from ai_client import _call_openai
    response = _call_openai(
        [{"role": "user", "content": "Say 'Hello'"}],
        model="gpt-4o-mini",
        max_tokens=20
    )
    print(f"2. API Call: {'✓' if response else '✗'}")
    if response:
        print(f"   Response: {response}")

# 3. Test with inventory
try:
    from database import Database
    from ai_client import _build_context
    db = Database()
    context = _build_context(db)
    print(f"3. Inventory Context: ✓ ({len(context)} chars)")
except Exception as e:
    print(f"3. Inventory Context: ✗ ({e})")

EOF
```

## Step-by-Step Fix

### If OpenAI is not working:

**Step 1: Get a new API key**
1. Go to https://platform.openai.com/account/api-keys
2. Sign in
3. Click "Create new secret key"
4. Copy the key

**Step 2: Update OpenAI.env**
1. Open `OpenAI.env` in the project root
2. Replace the old key with the new one:
   ```
   OPENAI_API_KEY=sk-proj-your-new-key-here
   ```
3. Save the file

**Step 3: Verify it works**
1. Run the test command above
2. Should see "✓" for API Key and API Call

**Step 4: Restart the app**
1. Close Harvest Hero completely
2. Open it again
3. Go to AI Command tab
4. Ask Ava a question
5. Should get OpenAI response

## What to Check

| Item | Status | How to Check |
|------|--------|-------------|
| API Key exists | ? | `cat OpenAI.env` |
| API Key format | ? | Should start with `sk-proj-` |
| API Key valid | ✗ | Run test command |
| OpenAI account active | ? | https://platform.openai.com |
| Account has credits | ? | https://platform.openai.com/account/billing |
| Internet connection | ? | `ping google.com` |
| Firewall blocking | ? | Try without VPN |

## Fallback Behavior

If OpenAI is not working:
- Ask Ava will still work using rule-based answers
- Responses won't be as natural/intelligent
- But the app will still be functional
- No errors or crashes

## Cost Concerns

**gpt-4o-mini pricing:**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

**Typical usage:**
- Per question: ~$0.0001 (0.01 cents)
- 100 questions/day: ~$0.01/day
- Monthly: ~$0.30

**Very affordable!**

## Advanced Debugging

### Check API key validity directly:

```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer sk-proj-your-key-here" \
  -H "Content-Type: application/json"
```

Should return a list of models if key is valid.

### Check specific error:

```python
import requests

key = "sk-proj-your-key-here"
resp = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    json={
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 10
    },
    timeout=20
)

print(f"Status: {resp.status_code}")
print(f"Response: {resp.json()}")
```

## Support

If you're still having issues:

1. **Check OpenAI status page:**
   https://status.openai.com

2. **Review OpenAI documentation:**
   https://platform.openai.com/docs

3. **Check your account:**
   https://platform.openai.com/account

4. **Contact OpenAI support:**
   https://help.openai.com

## Summary

**Current Issue:** API key is invalid or expired (401 error)

**Solution:** Get a new API key from https://platform.openai.com/account/api-keys and update OpenAI.env

**Next Steps:**
1. Get new API key
2. Update OpenAI.env
3. Restart app
4. Test in Ask Ava tab

Once fixed, Ask Ava will provide intelligent OpenAI-powered responses!
