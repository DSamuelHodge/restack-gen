# LLM Router

Multi-provider LLM routing with automatic fallback and circuit breaker patterns.

## Quick Start

Generate LLM configuration for your project:

```bash
restack g llm-config --backend direct
```

This creates:
- `config/llm_router.yaml` - Configuration file with provider settings
- `src/<project>/common/llm_router.py` - Router implementation

**Testing Kong Gateway?** See [Kong Gateway Quick Test Guide](./kong-setup-test.md) for step-by-step setup and validation.

## Configuration

### Environment Variables

Set your API keys:

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
```

### Provider Configuration

Edit `config/llm_router.yaml`:

```yaml
llm:
  router:
    backend: "direct"  # Direct provider calls
    timeout: 30
    
  providers:
    - name: "openai-primary"
      type: "openai"
      model: "gpt-4o-mini"
      base_url: "${OPENAI_BASE_URL:-https://api.openai.com/v1}"
      api_key: "${OPENAI_API_KEY}"
      priority: 1
      
    - name: "anthropic-fallback"
      type: "anthropic"
      model: "claude-3-5-sonnet-20241022"
      base_url: "${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
      api_key: "${ANTHROPIC_API_KEY}"
      priority: 2
  
  fallback:
    conditions:
      - "timeout"
      - "5xx"
      - "rate_limit"
    max_retries_per_provider: 2
    
    circuit_breaker:
      enabled: true
      failure_threshold: 5
      cooldown_seconds: 60
```

## Usage in Code

### Basic Usage

```python
from testapp.common.llm_router import LLMRouter, LLMRequest

# Initialize router (loads config/llm_router.yaml)
router = LLMRouter()

# Make a request
request = LLMRequest(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is 2+2?"}
    ],
    temperature=0.7,
    max_tokens=1000
)

response = await router.chat(request)
print(response.content)  # "4"
print(response.provider)  # "openai-primary"
print(response.usage)     # {"prompt_tokens": 15, "completion_tokens": 1, ...}
```

### In Restack Agents

```python
from restack_ai.agent import Agent, event
from testapp.common.llm_router import LLMRouter, LLMRequest

class MyAgent(Agent):
    def __init__(self):
        super().__init__()
        self.llm = LLMRouter()
    
    @event()
    async def process_query(self, query: str) -> str:
        request = LLMRequest(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": query}
            ]
        )
        
        response = await self.llm.chat(request)
        return response.content
```

## Features

### 1. Multi-Provider Fallback

Automatically falls back to the next provider if:
- Request times out
- Provider returns 5xx error
- Rate limit exceeded

Providers are tried in priority order (lowest number first).

### 2. Circuit Breaker

Prevents cascading failures by:
- Opening circuit after 5 consecutive failures
- Keeping circuit open for 60 seconds (cooldown)
- Automatically attempting recovery (half-open state)

### 3. Environment Variable Substitution

Config values support:
- `${VAR}` - Required variable (fails if not set)
- `${VAR:-default}` - Optional with default value

Example:
```yaml
api_key: "${OPENAI_API_KEY}"  # Required
base_url: "${OPENAI_BASE_URL:-https://api.openai.com/v1}"  # Optional with default
```

## Provider Support

### OpenAI

Supports all OpenAI chat models:
- `gpt-4o`
- `gpt-4o-mini`
- `gpt-4-turbo`
- Custom models via base_url

### Anthropic

Supports Claude models:
- `claude-3-5-sonnet-20241022`
- `claude-3-5-haiku-20241022`
- Other Claude 3.x models

## Backend Options

### Direct

Direct HTTP calls to provider APIs using httpx.

**Pros:**
- Simple, no additional infrastructure
- Fast local development
- Direct control over requests
- No gateway setup required

**Cons:**
- No rate limiting across instances
- No cost tracking
- No centralized caching
- Manual monitoring required

**Usage:**
```bash
restack g llm-config --backend direct
```

### Kong AI Gateway

Route through Kong AI Gateway for enterprise features.

**Additional Features:**
- **AI Rate Limiting:** Token-based rate limiting per consumer
- **Cost Tracking:** Automatic token usage and cost metrics
- **Content Safety:** Optional Azure content filters
- **Response Metadata:** Latency, cost, and rate limit info in responses
- **Circuit Breaking:** Gateway-level failure detection

**Setup:**

1. Install Kong Gateway (3.9+):
   ```bash
   # Docker example
   docker run -d --name kong-gateway \
     -e KONG_DATABASE=off \
     -e KONG_PROXY_ACCESS_LOG=/dev/stdout \
     -e KONG_ADMIN_ACCESS_LOG=/dev/stdout \
     -e KONG_PROXY_ERROR_LOG=/dev/stderr \
     -e KONG_ADMIN_ERROR_LOG=/dev/stderr \
     -p 8000:8000 \
     -p 8001:8001 \
     kong:3.9-alpine
   ```

2. Configure AI routes in Kong (see Kong AI Gateway docs)

3. Generate config with Kong backend:
   ```bash
   export KONG_GATEWAY_URL=http://localhost:8000
   restack g llm-config --backend kong
   ```

4. Configure features in `config/llm_router.yaml`:
   ```yaml
   llm:
     router:
       backend: "kong"
       url: "${KONG_GATEWAY_URL:-http://localhost:8000}"
       timeout: 30
       
       features:
         ai_rate_limiting:
           enabled: true
           window: "minute"
           token_limit: 100000  # Per consumer
           
         cost_tracking:
           enabled: true
           export_to: ["prometheus"]
           
         content_safety:
           enabled: false
           provider: "azure"
           filters: ["violence", "hate", "sexual", "self-harm"]
   ```

**Kong Routes:**
- OpenAI: `POST {KONG_URL}/ai/openai`
- Anthropic: `POST {KONG_URL}/ai/anthropic`

**Response Metadata:**
```python
response = await router.chat(request)
print(response.metadata)
# {
#   "latency_ms": "123",
#   "cost_usd": "0.0015",
#   "rate_limit_remaining": "95000"
# }
```

## Testing

Run tests:
```bash
pytest tests/test_llm_router.py -v
```

Test coverage:
- Config generation (4 tests)
- Router functionality (5 tests)
- Circuit breaker behavior
- Fallback logic
- Provider calls

## Troubleshooting

### "Config file not found"

Ensure `config/llm_router.yaml` exists in your project root.

### "API key not set"

Set environment variables:
```bash
export OPENAI_API_KEY=sk-...
```

### "All providers failed"

Check:
1. API keys are valid
2. Network connectivity
3. Provider status pages
4. Circuit breaker state (may need cooldown)

### Circuit breaker stuck open

Wait for cooldown period (default 60s) or restart application.

## Next Steps

See the v2.0 specification (`specs/specs.md`) for upcoming features:
- **PR #1:** ✅ LLM Router Foundation (Direct backend)
- **PR #2:** ✅ Kong AI Gateway integration
- **PR #3:** FastMCP tool server scaffolding
- **PR #4:** Tool auto-registration
- **PR #5:** Prompt versioning system
- **PR #6-12:** Advanced features (caching, streaming, etc.)

## Resources

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic API Documentation](https://docs.anthropic.com)
- [Kong AI Gateway Documentation](https://docs.konghq.com/gateway/latest/ai-gateway/)
- [httpx Documentation](https://www.python-httpx.org)
- [Restack Documentation](https://docs.restack.io)
