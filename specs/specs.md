# Rails for Restack v2: LLM + Tools + Prompts
## Product Specification & Implementation Plan

**Version:** 2.0.0  
**Date:** 2025-10-25  
**Status:** Ready for Implementation  
**Target:** Extend existing `restack-gen` CLI with agentic capabilities

---

## Executive Summary

Add **LLM routing**, **FastMCP tool integration**, and **prompt versioning** to the existing Rails-style Restack scaffolding toolchain. This transforms generated "agents" from simple event-driven workflows into true agentic systems with:

- **Multi-provider LLM routing** via Kong AI Gateway (with fallback)
- **FastMCP 2.0 tool servers** for extending agent capabilities
- **Versioned prompt registry** with semantic resolution
- **Built-in observability** for LLM calls, token usage, and tool invocations

**Key Design Principle:** Convention over configuration with escape hatches. Default to opinionated Kong + FastMCP setup, but allow swapping routers/tools via config.

---

## 1. Architecture Overview

```
repo/
  config/
    llm_router.yaml       # LLM provider config + Kong features
    tools.yaml            # FastMCP server definitions
    prompts.yaml          # Prompt registry with versions
  server/
    service.py            # Registers agents/workflows/functions + tool servers
  src/<app>/
    agents/               # Now use LLMs + tools
    common/
      llm_router.py       # Multi-provider routing client
      fastmcp_manager.py  # Tool server lifecycle
      prompt_loader.py    # Versioned prompt resolution
    tools/                # FastMCP tool server implementations
      __init__.py
      <server_name>_mcp.py
    prompts/              # Prompt templates (markdown)
      <name>/
        v1.0.0.md
        v1.1.0.md
```

---

## 2. New CLI Commands

| Command | Description |
|---------|-------------|
| `restack g llm-config` | Generate `config/llm_router.yaml` with Kong defaults |
| `restack g tool-server <Name>` | Generate FastMCP server with sample tools |
| `restack g prompt <Name> --version 1.0.0` | Create versioned prompt template |
| `restack g agent <Name> --with-llm --tools <server>` | Generate agent with LLM + tool wiring |
| `restack doctor --check-tools` | Validate FastMCP servers are reachable |

---

## 3. LLM Router (Kong AI Gateway)

### 3.1 Configuration Schema

```yaml
# config/llm_router.yaml
llm:
  router:
    backend: "kong"  # or "direct" for non-Kong usage
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
        provider: "azure"  # optional
        filters: ["violence", "hate", "sexual", "self-harm"]
  
  providers:
    - name: "openai-primary"
      type: "openai"
      model: "gpt-4o"
      base_url: "${OPENAI_BASE_URL:-https://api.openai.com/v1}"
      api_key: "${OPENAI_API_KEY}"
      priority: 1
      
    - name: "anthropic-fallback"
      type: "anthropic"
      model: "claude-3-5-sonnet-20241022"
      base_url: "${ANTHROPIC_BASE_URL:-https://api.anthropic.com}"
      api_key: "${ANTHROPIC_API_KEY}"
      priority: 2
      
    - name: "openai-budget"
      type: "openai"
      model: "gpt-4o-mini"
      base_url: "${OPENAI_BASE_URL:-https://api.openai.com/v1}"
      api_key: "${OPENAI_API_KEY}"
      priority: 3
      
  fallback:
    conditions:
      - timeout
      - 5xx
      - rate_limit
      - malformed_response
      - llm_error
    max_retries_per_provider: 2
    circuit_breaker:
      enabled: true
      failure_threshold: 5
      cooldown_seconds: 60
```

### 3.2 Router Implementation

```python
# src/<app>/common/llm_router.py
from typing import Literal, Any
import httpx
from pydantic import BaseModel

class LLMRequest(BaseModel):
    messages: list[dict[str, str]]
    model: str | None = None  # Override default
    temperature: float = 0.7
    max_tokens: int = 4096

class LLMResponse(BaseModel):
    content: str
    model: str
    usage: dict[str, int]
    provider: str

class LLMRouter:
    def __init__(self, config_path: str = "config/llm_router.yaml"):
        self.config = self._load_config(config_path)
        self.providers = sorted(
            self.config.providers, 
            key=lambda p: p.priority
        )
        self.circuit_breakers = {}  # provider_name -> state
        
    async def chat(self, request: LLMRequest) -> LLMResponse:
        """Route LLM request with fallback logic"""
        errors = []
        
        for provider in self.providers:
            if self._is_circuit_open(provider.name):
                continue
                
            try:
                response = await self._call_provider(provider, request)
                self._record_success(provider.name)
                return response
                
            except Exception as e:
                errors.append(f"{provider.name}: {e}")
                self._record_failure(provider.name)
                
                if not self._should_fallback(e):
                    raise
                    
        raise RuntimeError(f"All providers failed: {errors}")
    
    async def _call_provider(
        self, 
        provider: Provider, 
        request: LLMRequest
    ) -> LLMResponse:
        """Call provider via Kong or direct"""
        if self.config.router.backend == "kong":
            return await self._call_via_kong(provider, request)
        else:
            return await self._call_direct(provider, request)
    
    def _should_fallback(self, error: Exception) -> bool:
        """Check if error matches fallback conditions"""
        # Implement condition matching
        pass
```

### 3.3 Generated Agent Template (with LLM)

```python
# src/<app>/agents/research_agent.py
# @generated by restack-gen v2.0.0
from restack_ai import agent
from ..common.llm_router import LLMRouter, LLMRequest
from ..common.prompt_loader import PromptLoader
from ..common.fastmcp_manager import FastMCPClient

@agent.defn(name="ResearchAgent")
class ResearchAgent:
    def __init__(self):
        self.llm = LLMRouter()
        self.prompts = PromptLoader()
        self.tools = FastMCPClient("research_tools")
    
    @agent.run
    async def run(self, ctx, input: dict):
        # Load versioned prompt
        prompt_template = await self.prompts.load(
            "research_prompt", 
            version="1.0"
        )
        
        # Call tool if needed
        search_results = await self.tools.call_tool(
            "web_search",
            {"query": input["topic"]}
        )
        
        # Format prompt with context
        prompt = prompt_template.format(
            topic=input["topic"],
            context=search_results
        )
        
        # Route to LLM with fallback
        response = await self.llm.chat(LLMRequest(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        ))
        
        return {
            "analysis": response.content,
            "model_used": response.model,
            "provider": response.provider,
            "tokens": response.usage
        }
```

---

## 4. FastMCP Tool Integration

### 4.1 Tool Server Configuration

```yaml
# config/tools.yaml
fastmcp:
  servers:
    - name: "research_tools"
      module: "src.myapp.tools.research_mcp"
      class: "ResearchToolServer"
      transport: "stdio"  # or "sse" for HTTP
      autostart: true
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"
      health_check:
        enabled: true
        interval: 30
        
    - name: "docs_tools"
      module: "src.myapp.tools.docs_mcp"
      class: "DocsToolServer"
      transport: "sse"
      url: "http://localhost:8001"
      autostart: false  # Managed externally
      health_check:
        enabled: true
        endpoint: "/__health"
```

### 4.2 Tool Server Manager

```python
# src/<app>/common/fastmcp_manager.py
from fastmcp import FastMCP
import asyncio
from typing import Any

class FastMCPServerManager:
    """Manage lifecycle of FastMCP tool servers"""
    
    def __init__(self, config_path: str = "config/tools.yaml"):
        self.config = self._load_config(config_path)
        self.servers = {}
        
    async def start_all(self):
        """Start all autostart servers"""
        for server_config in self.config.servers:
            if server_config.autostart:
                await self.start_server(server_config.name)
    
    async def start_server(self, name: str):
        """Start a specific FastMCP server"""
        config = self._get_config(name)
        
        # Import and instantiate server class
        module = __import__(config.module, fromlist=[config.class_name])
        server_class = getattr(module, config.class_name)
        
        server = server_class()
        self.servers[name] = server
        
        # Run in background
        asyncio.create_task(
            server.run(transport=config.transport)
        )
    
    async def health_check(self, name: str) -> bool:
        """Check if server is healthy"""
        server = self.servers.get(name)
        if not server:
            return False
            
        try:
            # Ping server
            async with FastMCPClient(name) as client:
                tools = await client.list_tools()
                return len(tools) > 0
        except Exception:
            return False

class FastMCPClient:
    """Client for calling FastMCP tools from agents"""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        
    async def call_tool(
        self, 
        tool_name: str, 
        arguments: dict[str, Any]
    ) -> Any:
        """Call a tool on the server"""
        # Implementation using FastMCP client
        pass
        
    async def list_tools(self) -> list[dict]:
        """List available tools"""
        pass
```

### 4.3 Generated Tool Server Template

```python
# src/<app>/tools/research_mcp.py
# @generated by restack-gen v2.0.0
from fastmcp import FastMCP
import os

mcp = FastMCP("research_tools")

@mcp.tool()
async def web_search(query: str) -> dict:
    """
    Search the web using Brave Search API
    
    Args:
        query: Search query string
        
    Returns:
        Dict with search results
    """
    # TODO: Implement web search
    api_key = os.getenv("BRAVE_API_KEY")
    return {
        "results": [],
        "query": query
    }

@mcp.tool()
async def extract_urls(text: str) -> list[str]:
    """
    Extract URLs from text
    
    Args:
        text: Text to parse
        
    Returns:
        List of extracted URLs
    """
    # TODO: Implement URL extraction
    return []

class ResearchToolServer:
    """FastMCP server for research tools"""
    
    async def run(self, transport: str = "stdio"):
        await mcp.run(transport=transport)
```

---

## 5. Prompt Versioning

### 5.1 Prompt Registry Schema

```yaml
# config/prompts.yaml
prompts:
  research_prompt:
    description: "Analyze research topic with context"
    versions:
      "1.0.0": "prompts/research_prompt/v1.0.0.md"
      "1.1.0": "prompts/research_prompt/v1.1.0.md"
    latest: "1.1.0"
    resolution: "semver"  # or "exact"
    
  summarization_prompt:
    description: "Summarize long documents"
    versions:
      "1.0.0": "prompts/summarization/v1.0.0.md"
    latest: "1.0.0"
    resolution: "exact"
```

### 5.2 Prompt Template Format

```markdown
<!-- prompts/research_prompt/v1.0.0.md -->
---
version: 1.0.0
model: gpt-4o
temperature: 0.7
max_tokens: 4096
---

You are a research analyst. Analyze the following topic and provide insights.

## Topic
{topic}

## Context
{context}

## Instructions
1. Identify key themes
2. Highlight important findings
3. Suggest areas for deeper research

Provide your analysis in a structured format.
```

### 5.3 Prompt Loader Implementation

```python
# src/<app>/common/prompt_loader.py
from pathlib import Path
import yaml
from typing import Optional
from pydantic import BaseModel

class PromptTemplate(BaseModel):
    content: str
    metadata: dict
    version: str
    
    def format(self, **kwargs) -> str:
        """Format template with variables"""
        return self.content.format(**kwargs)

class PromptLoader:
    def __init__(self, config_path: str = "config/prompts.yaml"):
        self.config = self._load_config(config_path)
        self.cache = {}
    
    async def load(
        self, 
        name: str, 
        version: Optional[str] = None
    ) -> PromptTemplate:
        """Load prompt with version resolution"""
        
        if name not in self.config.prompts:
            raise ValueError(f"Prompt '{name}' not found")
        
        prompt_config = self.config.prompts[name]
        
        # Resolve version
        resolved_version = self._resolve_version(
            prompt_config, 
            version
        )
        
        # Load from cache or file
        cache_key = f"{name}:{resolved_version}"
        if cache_key not in self.cache:
            self.cache[cache_key] = self._load_file(
                prompt_config.versions[resolved_version]
            )
        
        return self.cache[cache_key]
    
    def _resolve_version(
        self, 
        config: PromptConfig, 
        requested: Optional[str]
    ) -> str:
        """Semantic version resolution"""
        if requested is None:
            return config.latest
            
        if config.resolution == "exact":
            if requested not in config.versions:
                raise ValueError(f"Version {requested} not found")
            return requested
        
        # Semver resolution
        available = sorted(
            config.versions.keys(), 
            key=lambda v: self._parse_version(v),
            reverse=True
        )
        
        requested_parts = self._parse_version(requested)
        
        for version in available:
            parts = self._parse_version(version)
            if self._matches_semver(requested_parts, parts):
                return version
        
        raise ValueError(f"No compatible version for {requested}")
    
    def _parse_version(self, version: str) -> tuple:
        """Parse semantic version string"""
        return tuple(map(int, version.split(".")))
    
    def _matches_semver(
        self, 
        requested: tuple, 
        available: tuple
    ) -> bool:
        """Check if versions match semantically"""
        # "1" matches "1.x.x"
        # "1.2" matches "1.2.x"
        # "1.2.3" matches exactly
        for i, req in enumerate(requested):
            if i >= len(available) or req != available[i]:
                return False
        return True
```

---

## 6. Service Registration Updates

```python
# server/service.py (updated)
from restack_ai.client import Restack
from src.myapp.agents import *
from src.myapp.workflows import *
from src.myapp.functions import *
from src.myapp.common.fastmcp_manager import FastMCPServerManager
import asyncio

async def main():
    # Start FastMCP tool servers
    tool_manager = FastMCPServerManager()
    await tool_manager.start_all()
    
    # Start Restack service
    client = Restack()
    await client.start_service(
        agents=[ResearchAgent],
        workflows=[...],
        functions=[...],
        task_queue="restack",
    )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 7. Doctor Enhancements

```bash
restack doctor --check-tools

Doctor Report
=============

✓ Python 3.11.8
✓ restack-ai 0.15.2 (compatible)
✓ fastmcp 2.0.1 (installed)
✓ pydantic 2.7.4

LLM Router
----------
✓ Kong Gateway reachable at http://localhost:8000
✓ Provider: openai-primary (healthy)
✓ Provider: anthropic-fallback (healthy)
! Provider: openai-budget (rate limited)

FastMCP Tool Servers
--------------------
✓ research_tools: healthy (3 tools available)
  - web_search
  - extract_urls
  - summarize_content
✗ docs_tools: unreachable (configured but not running)
  Fix: Start server or set autostart: false

Prompt Registry
---------------
✓ 5 prompts configured
✓ All prompt files exist
! research_prompt v1.2.0 missing (latest is 1.1.0)

Recommendations
---------------
• Update research_prompt to v1.2.0 or change latest in config/prompts.yaml
• Start docs_tools server: python -m src.myapp.tools.docs_mcp
• Consider adding fallback for openai-budget provider
```

---

## 8. Observability

### 8.1 Structured Logging

```python
# src/<app>/common/observability.py
import structlog
import time
from typing import Any

logger = structlog.get_logger()

class LLMCallObserver:
    """Track LLM calls for observability"""
    
    async def observe_call(
        self, 
        provider: str,
        model: str,
        func,
        *args, 
        **kwargs
    ) -> Any:
        start = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            logger.info(
                "llm_call_success",
                provider=provider,
                model=model,
                duration_ms=(time.time() - start) * 1000,
                tokens=result.usage,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "llm_call_failed",
                provider=provider,
                model=model,
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )
            raise

class ToolCallObserver:
    """Track FastMCP tool invocations"""
    
    async def observe_tool_call(
        self,
        server: str,
        tool: str,
        func,
        *args,
        **kwargs
    ) -> Any:
        start = time.time()
        
        try:
            result = await func(*args, **kwargs)
            
            logger.info(
                "tool_call_success",
                server=server,
                tool=tool,
                duration_ms=(time.time() - start) * 1000,
            )
            
            return result
            
        except Exception as e:
            logger.error(
                "tool_call_failed",
                server=server,
                tool=tool,
                duration_ms=(time.time() - start) * 1000,
                error=str(e),
            )
            raise
```

---

## 9. Implementation Plan — PR Sequence

### **PR #1: LLM Router Foundation**
**Files:** Core routing logic without Kong features  
**Scope:**
- [ ] `src/<app>/common/llm_router.py` (direct provider calls only)
- [ ] `config/llm_router.yaml` schema
- [ ] Basic fallback logic (timeout, 5xx)
- [ ] Unit tests for router
- [ ] `restack g llm-config` command

**Tests:**
- Mock provider responses
- Fallback on timeout
- Fallback on 5xx error
- All providers fail → raise error

**DoD:**
- Router can call OpenAI/Anthropic directly
- Fallback works for basic error conditions
- Config loads from YAML with env var substitution

---

### **PR #2: Kong AI Gateway Integration**
**Files:** Kong-specific routing features  
**Scope:**
- [ ] Kong backend in `llm_router.py`
- [ ] AI rate limiting config
- [ ] Token cost tracking
- [ ] Circuit breaker implementation
- [ ] Integration tests with mock Kong

**Tests:**
- Kong routes requests correctly
- Circuit breaker opens after threshold
- Rate limit detection triggers fallback
- Cost tracking exports metrics

**DoD:**
- Router works with Kong as backend
- All Kong features configurable via YAML
- Circuit breaker prevents repeated failures

---

### **PR #3: FastMCP Server Scaffolding**
**Files:** Tool server generation and management  
**Scope:**
- [ ] `restack g tool-server <Name>` command
- [ ] Tool server template (with 2 sample tools)
- [ ] `config/tools.yaml` schema
- [ ] `src/<app>/tools/__init__.py` structure
- [ ] Basic health check (no manager yet)

**Tests:**
- Generate tool server → imports successfully
- Sample tools are callable
- Health check returns true for running server

**DoD:**
- `restack g tool-server Research` creates runnable server
- Server exposes tools via FastMCP 2.0 API
- `pytest` passes for generated server

---

### **PR #4: FastMCP Server Manager**
**Files:** Lifecycle management for tool servers  
**Scope:**
- [ ] `src/<app>/common/fastmcp_manager.py`
- [ ] Server autostart in `server/service.py`
- [ ] FastMCPClient for calling tools from agents
- [ ] Health check integration
- [ ] `restack doctor --check-tools`

**Tests:**
- Manager starts all autostart servers
- Health checks detect running/stopped servers
- Client can call tools on running servers
- Doctor reports server status correctly

**DoD:**
- Tool servers auto-start with Restack service
- Agents can call tools via FastMCPClient
- Doctor validates tool server health

---

### **PR #5: Prompt Registry & Versioning**
**Files:** Prompt management system  
**Scope:**
- [ ] `config/prompts.yaml` schema
- [ ] `src/<app>/common/prompt_loader.py`
- [ ] Semantic version resolution
- [ ] `restack g prompt <Name> --version X.Y.Z` command
- [ ] Prompt template format (markdown with frontmatter)

**Tests:**
- Load prompt by exact version
- Resolve "1.2" to "1.2.3" (highest patch)
- Resolve "1" to "1.2.3" (highest minor.patch)
- Latest returns configured latest version
- Format template with variables

**DoD:**
- `restack g prompt Research --version 1.0.0` creates file
- Prompt loader resolves versions correctly
- Templates support variable substitution

---

### **PR #6: Agent Template with LLM + Tools**
**Files:** Enhanced agent generation  
**Scope:**
- [ ] Update agent template to include LLM router
- [ ] Add FastMCP client to agent template
- [ ] Add prompt loader to agent template
- [ ] `restack g agent <Name> --with-llm --tools <server>` flags
- [ ] Update existing agents to new pattern (migration guide)

**Tests:**
- Generate agent with `--with-llm` → includes router
- Generate agent with `--tools research` → includes client
- Agent can call LLM and tools in run method
- Integration test: agent → LLM → tool → response

**DoD:**
- New agents have LLM + tool capabilities
- `restack g agent Research --with-llm --tools research` works end-to-end
- Generated code follows conventions

---

### **PR #7: Observability & Logging**
**Files:** Structured logging for LLM/tool calls  
**Scope:**
- [ ] `src/<app>/common/observability.py`
- [ ] LLMCallObserver with timing/token tracking
- [ ] ToolCallObserver with timing
- [ ] Integration into router and FastMCP client
- [ ] Log correlation IDs (run_id, agent_id)

**Tests:**
- LLM calls emit structured logs
- Tool calls emit structured logs
- Logs include timing and outcome
- Logs include correlation IDs

**DoD:**
- All LLM calls are logged with tokens/duration
- All tool calls are logged with duration
- Logs are queryable by run_id

---

### **PR #8: Error Handling & Validation**
**Files:** Robust error handling  
**Scope:**
- [ ] Validate LLM response structure
- [ ] Detect malformed_response and llm_error conditions
- [ ] Handle 200-with-error-body cases
- [ ] Improved error messages
- [ ] Retry logic for transient failures

**Tests:**
- 200 with error body triggers fallback
- Malformed JSON triggers fallback
- Invalid finish_reason triggers fallback
- Error messages are actionable

**DoD:**
- Router handles all failure modes gracefully
- Users get clear error messages
- Transient failures retry automatically

---

### **PR #9: Doctor Enhancements**
**Files:** Comprehensive health checks  
**Scope:**
- [ ] `restack doctor --check-tools` (already in PR #4)
- [ ] Check Kong Gateway reachability
- [ ] Validate all configured providers
- [ ] Check prompt file existence
- [ ] Validate tool server health
- [ ] Actionable fix suggestions

**Tests:**
- Doctor detects unreachable Kong
- Doctor detects missing prompt files
- Doctor detects stopped tool servers
- Fix suggestions are accurate

**DoD:**
- `restack doctor` validates entire LLM + tool stack
- Reports are clear and actionable
- Suggested fixes work

---

### **PR #10: Documentation & Examples**
**Files:** Usage guides and examples  
**Scope:**
- [ ] README updates for v2 features
- [ ] Example: Research agent with LLM + tools
- [ ] Example: Multi-step pipeline with prompts
- [ ] Kong setup guide
- [ ] FastMCP tool development guide
- [ ] Prompt versioning best practices

**DoD:**
- New user can follow README to create agentic workflow
- Examples run successfully
- Documentation covers all new features

---

### **PR #11: Testing & CI Updates**
**Files:** Comprehensive test coverage  
**Scope:**
- [ ] Integration tests with mock Kong
- [ ] Integration tests with mock FastMCP servers
- [ ] Golden file tests for new templates
- [ ] CI pipeline updates
- [ ] Test fixtures for LLM/tool mocking

**DoD:**
- CI runs all new tests
- Coverage > 80% for new modules
- Integration tests catch regressions

---

### **PR #12: Performance & Polish**
**Files:** Optimizations and UX improvements  
**Scope:**
- [ ] Prompt caching in loader
- [ ] Connection pooling in router
- [ ] Tool response caching (optional)
- [ ] Better CLI progress indicators
- [ ] Dry-run mode for LLM calls (cost estimation)

**DoD:**
- Prompt loading is fast (cached)
- LLM calls use connection pooling
- `--dry-run` estimates token costs

---

## 10. Acceptance Criteria

### **End-to-End Flow**

```bash
# 1. Setup new project with LLM + tools
restack new research-agent
cd research-agent

# 2. Generate LLM config
restack g llm-config
# → creates config/llm_router.yaml

# 3. Generate tool server
restack g tool-server Research
# → creates src/research_agent/tools/research_mcp.py

# 4. Generate prompt
restack g prompt analyze-research --version 1.0.0
# → creates prompts/analyze_research/v1.0.0.md

# 5. Generate agent with everything
restack g agent ResearchAgent --with-llm --tools research
# → creates src/research_agent/agents/research_agent.py
# → wired with LLM router, FastMCP client, prompt loader

# 6. Validate setup
restack doctor --check-tools
# ✓ All systems operational

# 7. Run server
restack run:server
# → Starts tool servers + Restack service

# 8. Test agent (from client)
python client/run_agent.py ResearchAgent '{"topic": "AI safety"}'
# → Agent uses LLM + tools + prompts → returns analysis
```

### **Success Metrics**

- [ ] `restack g agent` with `--with-llm` generates functional agent
- [ ] Agent can call multiple LLM providers with automatic fallback
- [ ] Agent can invoke FastMCP tools
- [ ] Agent uses versioned prompts
- [ ] `restack doctor` validates entire stack
- [ ] All generated code passes linting/type checks
- [ ] Integration test runs full pipeline end-to-end

---

## 11. Configuration Reference

### Minimal Viable Config

```yaml
# config/llm_router.yaml (minimal)
llm:
  router:
    backend: "direct"
  providers:
    - name: "openai"
      type: "openai"
      model: "gpt-4o-mini"
      api_key: "${OPENAI_API_KEY}"
```

```yaml
# config/tools.yaml (minimal)
fastmcp:
  servers:
    - name: "basic_tools"
      module: "src.myapp.tools.basic_mcp"
      class: "BasicToolServer"
      transport: "stdio"
```

```yaml
# config/prompts.yaml (minimal)
prompts:
  default_prompt:
    versions:
      "1.0.0": "prompts/default/v1.0.0.md"
    latest: "1.0.0"
```

---

## 12. Migration Guide (v1 → v2)

### For Existing Projects

```bash
# 1. Add new config files
restack g llm-config
restack g tool-server Default

# 2. Update agents manually or regenerate
restack g agent ExistingAgent --with-llm --force

# 3. Update server/service.py
# Add tool manager startup (automatic if regenerated)

# 4. Add environment variables
# .env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
KONG_GATEWAY_URL=http://localhost:8000

# 5. Test migration
restack doctor --check-tools
pytest tests/
```

### Breaking Changes

**None for v1 projects** — v2 features are opt-in:
- Existing agents continue working without modification
- LLM/tool features require `--with-llm` flag
- No changes to core workflow/function templates

---

## 13. Dependencies & Versions

```toml
# pyproject.toml additions
[tool.poetry.dependencies]
fastmcp = "^2.0.0"           # FastMCP 2.0 framework
httpx = "^0.27.0"            # Async HTTP client
structlog = "^24.1.0"        # Structured logging
pyyaml = "^6.0.1"            # YAML config parsing
semver = "^3.0.2"            # Semantic versioning

[tool.poetry.group.dev.dependencies]
respx = "^0.21.0"            # HTTP mocking for tests
pytest-asyncio = "^0.23.0"   # Async test support
```

### Version Compatibility Matrix

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| Python | 3.11 | 3.12 | Async improvements |
| restack-ai | 0.15.0 | Latest | Core SDK |
| fastmcp | 2.0.0 | Latest | Not official MCP SDK |
| pydantic | 2.7.0 | Latest | v2 only |
| Kong Gateway | 3.9+ | 3.9+ | For AI features |

---

## 14. Security Considerations

### API Key Management

```python
# src/<app>/common/secrets.py
# @generated by restack-gen v2.0.0
import os
from functools import lru_cache

class SecretsManager:
    """Centralized secrets management"""
    
    @staticmethod
    @lru_cache(maxsize=None)
    def get_api_key(provider: str) -> str:
        """Get API key from environment"""
        key_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "brave": "BRAVE_API_KEY",
        }
        
        env_var = key_map.get(provider)
        if not env_var:
            raise ValueError(f"Unknown provider: {provider}")
        
        key = os.getenv(env_var)
        if not key:
            raise ValueError(f"{env_var} not set")
        
        return key
    
    @staticmethod
    def validate_all() -> dict[str, bool]:
        """Validate all required keys are present"""
        results = {}
        for provider in ["openai", "anthropic"]:
            try:
                SecretsManager.get_api_key(provider)
                results[provider] = True
            except ValueError:
                results[provider] = False
        return results
```

### Content Safety

```yaml
# config/llm_router.yaml
llm:
  router:
    features:
      content_safety:
        enabled: true
        provider: "azure"  # Azure Content Safety
        block_on: ["high"]  # Block high-severity content
        filters:
          - violence
          - hate
          - sexual
          - self-harm
        log_violations: true
```

### Rate Limiting (Kong)

```yaml
llm:
  router:
    features:
      ai_rate_limiting:
        enabled: true
        window: "minute"
        token_limit: 100000
        request_limit: 100
        strategy: "sliding"
        enforcement: "block"  # or "log"
```

---

## 15. Monitoring & Metrics

### Prometheus Metrics

```python
# src/<app>/common/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# LLM metrics
llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM requests',
    ['provider', 'model', 'status']
)

llm_request_duration = Histogram(
    'llm_request_duration_seconds',
    'LLM request duration',
    ['provider', 'model']
)

llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used',
    ['provider', 'model', 'type']  # type: prompt, completion
)

llm_cost_total = Counter(
    'llm_cost_total_usd',
    'Estimated LLM costs',
    ['provider', 'model']
)

# Tool metrics
tool_calls_total = Counter(
    'tool_calls_total',
    'Total tool invocations',
    ['server', 'tool', 'status']
)

tool_call_duration = Histogram(
    'tool_call_duration_seconds',
    'Tool call duration',
    ['server', 'tool']
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open)',
    ['provider']
)
```

### Kong AI Gateway Metrics Export

Kong automatically exports:
- Request/response counts per model
- Token usage per model
- Latency percentiles
- Error rates by provider
- Cost tracking (if configured)

**Integration:**
```yaml
# config/llm_router.yaml
llm:
  router:
    features:
      cost_tracking:
        enabled: true
        export_to:
          - prometheus
          - datadog
          - cloudwatch
```

---

## 16. Error Handling Patterns

### LLM Error Taxonomy

```python
# src/<app>/common/errors.py
from enum import Enum

class LLMErrorType(Enum):
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    INVALID_API_KEY = "invalid_api_key"
    MODEL_NOT_FOUND = "model_not_found"
    CONTENT_FILTER = "content_filter"
    MALFORMED_RESPONSE = "malformed_response"
    PROVIDER_ERROR = "provider_error"
    CIRCUIT_OPEN = "circuit_open"

class LLMError(Exception):
    def __init__(
        self, 
        error_type: LLMErrorType,
        provider: str,
        message: str,
        retryable: bool = True
    ):
        self.error_type = error_type
        self.provider = provider
        self.retryable = retryable
        super().__init__(message)

class ToolError(Exception):
    def __init__(
        self,
        server: str,
        tool: str,
        message: str,
        retryable: bool = True
    ):
        self.server = server
        self.tool = tool
        self.retryable = retryable
        super().__init__(message)
```

### Retry Strategy

```python
# src/<app>/common/retry.py
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

llm_retry = retry(
    retry=retry_if_exception_type(LLMError),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    stop=stop_after_attempt(3),
    before_sleep=lambda retry_state: logger.info(
        "Retrying LLM call",
        attempt=retry_state.attempt_number,
        error=str(retry_state.outcome.exception())
    )
)

tool_retry = retry(
    retry=retry_if_exception_type(ToolError),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    stop=stop_after_attempt(2),
)
```

---

## 17. Testing Strategy

### Unit Tests

```python
# tests/test_llm_router.py
import pytest
from unittest.mock import AsyncMock, patch
from src.myapp.common.llm_router import LLMRouter, LLMRequest

@pytest.fixture
def mock_providers():
    return {
        "openai": AsyncMock(return_value={
            "choices": [{"message": {"content": "test"}}],
            "usage": {"total_tokens": 100}
        }),
        "anthropic": AsyncMock(return_value={
            "content": [{"text": "test"}],
            "usage": {"input_tokens": 50, "output_tokens": 50}
        })
    }

@pytest.mark.asyncio
async def test_router_fallback_on_timeout(mock_providers):
    """Test fallback to secondary provider on timeout"""
    router = LLMRouter()
    
    # Primary times out
    mock_providers["openai"].side_effect = TimeoutError()
    
    with patch.object(router, '_call_provider', side_effect=[
        TimeoutError(),
        mock_providers["anthropic"]()
    ]):
        response = await router.chat(LLMRequest(
            messages=[{"role": "user", "content": "test"}]
        ))
        
        assert response.provider == "anthropic"
        assert response.content == "test"

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_threshold():
    """Test circuit breaker opens after repeated failures"""
    router = LLMRouter()
    
    # Simulate 5 consecutive failures
    for _ in range(5):
        with pytest.raises(LLMError):
            await router.chat(LLMRequest(
                messages=[{"role": "user", "content": "test"}]
            ))
    
    # Circuit should be open
    assert router._is_circuit_open("openai") is True
```

### Integration Tests

```python
# tests/integration/test_agent_with_llm.py
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_research_agent_end_to_end(
    mock_llm_router,
    mock_fastmcp_client
):
    """Test agent with LLM and tools"""
    from src.myapp.agents.research_agent import ResearchAgent
    
    # Mock tool response
    mock_fastmcp_client.call_tool.return_value = {
        "results": ["Article 1", "Article 2"]
    }
    
    # Mock LLM response
    mock_llm_router.chat.return_value = AsyncMock(
        content="Research analysis...",
        model="gpt-4o",
        provider="openai",
        usage={"total_tokens": 500}
    )
    
    agent = ResearchAgent()
    result = await agent.run(
        ctx=None,
        input={"topic": "AI safety"}
    )
    
    # Verify tool was called
    mock_fastmcp_client.call_tool.assert_called_once_with(
        "web_search",
        {"query": "AI safety"}
    )
    
    # Verify LLM was called
    mock_llm_router.chat.assert_called_once()
    
    # Verify result structure
    assert "analysis" in result
    assert result["model_used"] == "gpt-4o"
    assert result["provider"] == "openai"
```

### Golden File Tests

```python
# tests/test_templates/test_agent_template.py
from pathlib import Path
import pytest

def test_agent_template_with_llm_generates_correctly(tmp_path):
    """Test agent template includes LLM integration"""
    from restack_gen.cli import generate_agent
    
    # Generate agent
    generate_agent(
        name="TestAgent",
        output_dir=tmp_path,
        with_llm=True,
        tools=["research"]
    )
    
    agent_file = tmp_path / "src" / "myapp" / "agents" / "test_agent.py"
    content = agent_file.read_text()
    
    # Verify key components present
    assert "from ..common.llm_router import LLMRouter" in content
    assert "from ..common.fastmcp_manager import FastMCPClient" in content
    assert "self.llm = LLMRouter()" in content
    assert "self.tools = FastMCPClient" in content
    assert "await self.llm.chat" in content
```

---

## 18. Performance Optimization

### Connection Pooling

```python
# src/<app>/common/llm_router.py
import httpx

class LLMRouter:
    def __init__(self, config_path: str = "config/llm_router.yaml"):
        self.config = self._load_config(config_path)
        
        # Shared connection pool
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20
            )
        )
    
    async def close(self):
        """Close connection pool"""
        await self.client.aclose()
```

### Prompt Caching

```python
# src/<app>/common/prompt_loader.py
from functools import lru_cache

class PromptLoader:
    def __init__(self):
        self._cache = {}
    
    @lru_cache(maxsize=100)
    def _load_file(self, path: str) -> PromptTemplate:
        """Cache loaded prompts in memory"""
        content = Path(path).read_text()
        return self._parse_template(content)
```

### Batch Tool Calls

```python
# src/<app>/common/fastmcp_manager.py
class FastMCPClient:
    async def call_tools_batch(
        self,
        calls: list[dict]
    ) -> list[Any]:
        """Call multiple tools in parallel"""
        import asyncio
        
        tasks = [
            self.call_tool(call["tool"], call["args"])
            for call in calls
        ]
        
        return await asyncio.gather(*tasks, return_exceptions=True)
```

---

## 19. CLI Command Reference

### Complete Command List

```bash
# LLM configuration
restack g llm-config [--kong|--direct]
  # Generate config/llm_router.yaml with defaults

# Tool server generation
restack g tool-server <name> [--transport stdio|sse] [--autostart]
  # Generate FastMCP server with sample tools

# Prompt generation
restack g prompt <name> --version <semver> [--model <model>]
  # Create versioned prompt template

# Agent with LLM+Tools
restack g agent <name> --with-llm [--tools <server>] [--prompt <name>]
  # Generate agent with LLM router, tool client, prompt loader

# Validation
restack doctor --check-tools [--check-llm] [--check-prompts]
  # Comprehensive health check

# Testing
restack test:llm [--dry-run]
  # Test LLM configuration and connectivity

restack test:tools [--server <name>]
  # Test tool server health and tool availability
```

### Flag Reference

| Flag | Commands | Description |
|------|----------|-------------|
| `--with-llm` | `g agent` | Add LLM router to agent |
| `--tools <server>` | `g agent` | Add FastMCP client for server |
| `--prompt <name>` | `g agent` | Add prompt loader with default |
| `--kong` | `g llm-config` | Configure Kong backend (default) |
| `--direct` | `g llm-config` | Configure direct provider calls |
| `--transport stdio\|sse` | `g tool-server` | Set transport type |
| `--autostart` | `g tool-server` | Enable autostart in service |
| `--version <semver>` | `g prompt` | Set prompt version |
| `--model <model>` | `g prompt` | Set default model in frontmatter |
| `--check-tools` | `doctor` | Validate tool servers |
| `--check-llm` | `doctor` | Validate LLM configuration |
| `--check-prompts` | `doctor` | Validate prompt files |
| `--dry-run` | `test:llm` | Estimate costs without calling |

---

## 20. Troubleshooting Guide

### Common Issues

#### Issue: "Circuit breaker open for provider"

**Cause:** Too many consecutive failures to LLM provider  
**Fix:**
```bash
# Check provider health
restack doctor --check-llm

# Review logs
tail -f logs/llm_router.log | grep circuit_breaker

# Reset circuit breaker (restart service)
restack run:server
```

#### Issue: "Tool server unreachable"

**Cause:** FastMCP server not running  
**Fix:**
```bash
# Check tool server status
restack doctor --check-tools

# Start server manually (if autostart=false)
python -m src.myapp.tools.research_mcp

# Or enable autostart in config/tools.yaml
```

#### Issue: "Prompt version not found"

**Cause:** Requested version doesn't exist  
**Fix:**
```bash
# List available versions
ls prompts/research_prompt/

# Update config/prompts.yaml with correct version
# Or create new version:
restack g prompt research_prompt --version 1.2.0
```

#### Issue: "All LLM providers failed"

**Cause:** Network issues, invalid API keys, or all providers down  
**Fix:**
```bash
# Validate API keys
restack doctor --check-llm

# Test connectivity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Check fallback configuration
cat config/llm_router.yaml | grep fallback -A 5
```

---

## 21. Future Enhancements (Post-v2)

### v2.1 Planned Features

- [ ] **Streaming LLM responses** (SSE support)
- [ ] **Prompt A/B testing** (version comparison)
- [ ] **Tool response caching** (Redis integration)
- [ ] **Multi-agent orchestration** (agent-to-agent communication)
- [ ] **LLM cost budget enforcement** (per-agent limits)
- [ ] **Visual tool builder** (web UI for FastMCP tools)

### v3.0 Vision

- [ ] **Autonomous agent loops** (self-improving agents)
- [ ] **Knowledge graph integration** (for context management)
- [ ] **Fine-tuned model deployment** (LoRA adapters)
- [ ] **Multi-modal support** (vision, audio, video)
- [ ] **Federated learning** (distributed agent training)

---

## 22. Appendix: Example Outputs

### Example: Generated Agent with LLM+Tools

```python
# src/myapp/agents/research_agent.py
# @generated by restack-gen v2.0.0 (2025-10-25T14:30:00Z)
# command: restack g agent ResearchAgent --with-llm --tools research
# do not edit this header; use --force to overwrite

from restack_ai import agent
from pydantic import BaseModel
from ..common.llm_router import LLMRouter, LLMRequest
from ..common.fastmcp_manager import FastMCPClient
from ..common.prompt_loader import PromptLoader
from ..common.observability import LLMCallObserver, ToolCallObserver
import structlog

logger = structlog.get_logger()

class ResearchAgentInput(BaseModel):
    topic: str
    depth: str = "comprehensive"  # brief, standard, comprehensive
    max_sources: int = 5

class ResearchAgentOutput(BaseModel):
    analysis: str
    sources: list[str]
    model_used: str
    provider: str
    tokens: dict[str, int]
    tool_calls: int

@agent.defn(name="ResearchAgent")
class ResearchAgent:
    """
    Research agent that analyzes topics using web search and LLM analysis.
    
    Capabilities:
    - Web search via FastMCP tools
    - Multi-provider LLM analysis with fallback
    - Versioned prompt templates
    - Structured output with citations
    """
    
    def __init__(self):
        self.llm = LLMRouter()
        self.tools = FastMCPClient("research_tools")
        self.prompts = PromptLoader()
        self.llm_observer = LLMCallObserver()
        self.tool_observer = ToolCallObserver()
    
    @agent.run
    async def run(self, ctx, input: ResearchAgentInput) -> ResearchAgentOutput:
        logger.info(
            "research_agent_started",
            topic=input.topic,
            depth=input.depth
        )
        
        # Step 1: Search for sources
        search_result = await self.tool_observer.observe_tool_call(
            server="research_tools",
            tool="web_search",
            func=self.tools.call_tool,
            "web_search",
            {
                "query": input.topic,
                "max_results": input.max_sources
            }
        )
        
        sources = search_result.get("results", [])
        
        # Step 2: Load versioned prompt
        prompt_template = await self.prompts.load(
            "research_analysis",
            version="1.0"  # TODO: Make configurable
        )
        
        # Step 3: Format prompt with context
        prompt = prompt_template.format(
            topic=input.topic,
            depth=input.depth,
            sources="\n".join(sources)
        )
        
        # Step 4: Analyze with LLM (with fallback)
        llm_response = await self.llm_observer.observe_call(
            provider="primary",
            model="gpt-4o",
            func=self.llm.chat,
            LLMRequest(
                messages=[
                    {"role": "system", "content": "You are a research analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4096
            )
        )
        
        logger.info(
            "research_agent_completed",
            tokens=llm_response.usage,
            provider=llm_response.provider
        )
        
        return ResearchAgentOutput(
            analysis=llm_response.content,
            sources=sources,
            model_used=llm_response.model,
            provider=llm_response.provider,
            tokens=llm_response.usage,
            tool_calls=1
        )
```

### Example: Generated Tool Server

```python
# src/myapp/tools/research_mcp.py
# @generated by restack-gen v2.0.0 (2025-10-25T14:32:00Z)
# command: restack g tool-server Research --transport stdio --autostart
# do not edit this header; use --force to overwrite

from fastmcp import FastMCP
from pydantic import BaseModel, Field
import httpx
import os

mcp = FastMCP("research_tools")

class WebSearchArgs(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=10, description="Maximum results")

class WebSearchResult(BaseModel):
    results: list[str]
    query: str
    count: int

@mcp.tool()
async def web_search(args: WebSearchArgs) -> WebSearchResult:
    """
    Search the web using Brave Search API.
    
    Returns a list of relevant search results for the query.
    """
    api_key = os.getenv("BRAVE_API_KEY")
    if not api_key:
        raise ValueError("BRAVE_API_KEY not set")
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key},
            params={
                "q": args.query,
                "count": args.max_results
            }
        )
        response.raise_for_status()
        
        data = response.json()
        results = [
            result["title"] + " - " + result["url"]
            for result in data.get("web", {}).get("results", [])
        ]
        
        return WebSearchResult(
            results=results,
            query=args.query,
            count=len(results)
        )

@mcp.tool()
async def extract_content(url: str) -> str:
    """
    Extract main content from a web page.
    
    Args:
        url: URL to extract content from
        
    Returns:
        Extracted text content
    """
    # TODO: Implement content extraction
    # Consider using trafilatura or newspaper3k
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text[:1000]  # Stub implementation

class ResearchToolServer:
    """FastMCP server for research tools"""
    
    async def run(self, transport: str = "stdio"):
        """Start the FastMCP server"""
        await mcp.run(transport=transport)

if __name__ == "__main__":
    import asyncio
    server = ResearchToolServer()
    asyncio.run(server.run())
```

---

## 23. Definition of Done

### Per-PR Checklist

- [ ] Code passes `ruff check` and `ruff format`
- [ ] Type checking passes (`mypy src/`)
- [ ] Unit tests pass (`pytest tests/unit`)
- [ ] Integration tests pass (`pytest tests/integration`)
- [ ] Generated code imports without errors
- [ ] `restack doctor` validates new functionality
- [ ] Documentation updated (README, docstrings)
- [ ] CHANGELOG.md entry added
- [ ] PR reviewed and approved

### Release Checklist (v2.0.0)

- [ ] All PRs merged and tests passing
- [ ] End-to-end acceptance test passes
- [ ] Documentation complete and reviewed
- [ ] Migration guide tested with real v1 project
- [ ] Performance benchmarks acceptable
- [ ] Security audit completed
- [ ] Version bumped in `pyproject.toml`
- [ ] Git tag created: `v2.0.0`
- [ ] PyPI package published
- [ ] Release notes published
- [ ] Example projects updated

---

## 24. Success Metrics

### Developer Experience

- **Time to first agent**: < 5 minutes
- **Generated code quality**: No manual edits needed for 80% of use cases
- **Doctor diagnostic accuracy**: > 90% of issues detected correctly

### Production Reliability

- **LLM fallback success rate**: > 95%
- **Tool server uptime**: > 99%
- **Circuit breaker false positives**: < 5%

### Cost Efficiency

- **Token usage reduction**: 20% via prompt optimization
- **Failed request rate**: < 2%
- **Average latency**: < 3s for simple LLM calls

---

**END OF SPECIFICATION**

Ready to hand off to your development team. Each PR is self-contained with clear scope, tests, and DoD criteria.