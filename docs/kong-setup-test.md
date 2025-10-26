# Kong Gateway Quick Test Guide

This guide will help you verify that Kong Gateway is running and configure it for LLM routing.

## Prerequisites

- Kong Gateway 3.9+ installed
- decK CLI installed
- OpenAI API key set in environment variable `OPENAI_KEY`

## Step 1: Verify Kong Gateway is Running

Check that Kong Gateway is accessible via decK:

```bash
deck gateway ping
```

**Expected response:**
```
Successfully Konnected to the Kong organization!
```

If you get an error, ensure:
- Kong Gateway is running (check `docker ps` or service status)
- Your Konnect access token is configured
- Network connectivity is available

## Step 2: Create a Gateway Service

Create a Service to contain the Route for the LLM provider:

```bash
echo '
_format_version: "3.0"
services:
  - name: llm-service
    url: http://localhost:32000
' | deck gateway apply -
```

**Note:** The URL can point to any empty host, as it won't be used by the AI Proxy plugin.

## Step 3: Create a Route

Create a Route for the LLM provider. We'll use `/chat` as the path:

```bash
echo '
_format_version: "3.0"
routes:
  - name: openai-chat
    service:
      name: llm-service
    paths:
    - "/chat"
' | deck gateway apply -
```

## Step 4: Enable the AI Proxy Plugin

Enable the AI Proxy plugin to create a chat route:

```bash
echo '
_format_version: "3.0"
plugins:
  - name: ai-proxy
    config:
      route_type: llm/v1/chat
      model:
        provider: openai
' | deck gateway apply -
```

### Plugin Configuration Notes

This minimal configuration means:
- ✅ Client can use **any model** in the OpenAI provider
- ✅ Client **must provide** the model name in request body
- ✅ Client **must provide** an `Authorization` header with OpenAI API key

### Optional: Restrict Model Access

To restrict specific models, add `config.model.name`:

```bash
echo '
_format_version: "3.0"
plugins:
  - name: ai-proxy
    config:
      route_type: llm/v1/chat
      model:
        provider: openai
        name: gpt-4o  # Only allow gpt-4o
' | deck gateway apply -
```

### Optional: Embed API Key in Configuration

To avoid clients sending API keys, configure them in the plugin:

```bash
echo '
_format_version: "3.0"
plugins:
  - name: ai-proxy
    config:
      route_type: llm/v1/chat
      model:
        provider: openai
      auth:
        header_name: Authorization
        header_value: Bearer sk-YOUR_OPENAI_KEY_HERE
' | deck gateway apply -
```

## Step 5: Validate the Setup

Send a test request to verify the configuration:

```bash
curl -X POST "$KONNECT_PROXY_URL/chat" \
     -H "Accept: application/json" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer $OPENAI_KEY" \
     --json '{
       "model": "gpt-4",
       "messages": [
         {
           "role": "user",
           "content": "Say this is a test!"
         }
       ]
     }'
```

**Expected response:**
- Status: `200 OK`
- Body should contain: `"This is a test"`

### Example Response

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "created": 1729872000,
  "model": "gpt-4",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "This is a test!"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 13,
    "completion_tokens": 5,
    "total_tokens": 18
  }
}
```

## Kong Gateway Configuration for Restack-Gen

Once Kong is verified, update your `restack-gen` LLM router configuration:

### 1. Set Environment Variables

```bash
# PowerShell
$env:KONG_GATEWAY_URL = "http://localhost:8000"  # Your Kong proxy URL
$env:OPENAI_API_KEY = "sk-your-key-here"
```

```bash
# Linux/Mac
export KONG_GATEWAY_URL="http://localhost:8000"
export OPENAI_API_KEY="sk-your-key-here"
```

### 2. Generate Kong-Enabled Configuration

```bash
restack g llm-config --backend kong --force
```

### 3. Verify Generated Config

Check `config/llm_router.yaml`:

```yaml
backend: "kong"

kong:
  gateway_url: "${KONG_GATEWAY_URL}"
  routes:
    openai: "/ai/openai"
    anthropic: "/ai/anthropic"

ai_rate_limiting:
  enabled: true
  tokens_per_minute: 100000
  window: 60

cost_tracking:
  enabled: true
  export_to: ["prometheus"]
```

## Troubleshooting

### Issue: "Connection refused"

**Solution:**
- Check Kong Gateway is running: `docker ps | grep kong`
- Verify proxy URL: `echo $KONNECT_PROXY_URL`
- Test connectivity: `curl $KONNECT_PROXY_URL/status`

### Issue: "401 Unauthorized"

**Solution:**
- Verify OpenAI API key is set: `echo $OPENAI_KEY`
- Check key format: Should start with `sk-`
- Test key directly with OpenAI: `curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_KEY"`

### Issue: "404 Not Found"

**Solution:**
- Verify route was created: `deck gateway dump`
- Check route path matches request: `/chat`
- Confirm service and route are linked

### Issue: "429 Rate Limited"

**Solution:**
- Kong AI rate limiting is active
- Check remaining tokens: Response header `X-RateLimit-Remaining`
- Adjust limits in plugin config: `tokens_per_minute`

## Developer Access Token

For this tutorial, use the provided Konnect access token:

```bash
# PowerShell
$env:KONNECT_TOKEN = "kpat_dV2YeT1gbRfYhuI5fUSF1lsaU8mWH2T4Zvk3XPBZP2XwxX5Kt"

# Linux/Mac
export KONNECT_TOKEN="kpat_dV2YeT1gbRfYhuI5fUSF1lsaU8mWH2T4Zvk3XPBZP2XwxX5Kt"
```

**Note:** This token should be kept secure and rotated regularly in production.

## Next Steps

1. ✅ Verify Kong Gateway is running (`deck gateway ping`)
2. ✅ Create service, route, and plugin configuration
3. ✅ Test with curl to validate setup
4. ✅ Generate `restack-gen` config with `--backend kong`
5. 🚀 Start using LLM router with Kong features:
   - AI rate limiting (100k tokens/minute)
   - Cost tracking (Prometheus export)
   - Content safety filters (optional)
   - Response metadata (latency, cost, rate limits)

## Related Documentation

- [LLM Router Guide](./llm-router.md)
- [Kong AI Gateway Documentation](https://docs.konghq.com/gateway/latest/ai-gateway/)
- [decK CLI Reference](https://docs.konghq.com/deck/)
- [Restack-Gen CLI Reference](./cli-reference.md)
