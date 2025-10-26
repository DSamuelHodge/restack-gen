# Agent LLM & Tools Migration Guide

This guide explains how to enhance existing agents with LLM routing and FastMCP tool integration capabilities.

## Overview

As of restack-gen v2.0.0, agents can be generated with enhanced capabilities:

- **LLM Router**: Multi-provider LLM support with automatic fallback
- **Prompt Loader**: Versioned prompt management
- **FastMCP Tools**: Integration with tool servers for external capabilities

## New Agent Generation

### Generate Agent with LLM Support

```bash
restack g agent Researcher --with-llm
```

This generates an agent with:
- LLMRouter for calling LLMs
- PromptLoader for loading versioned prompts
- Sample code showing LLM usage patterns

### Generate Agent with Tool Support

```bash
restack g agent DataProcessor --tools Research
```

This generates an agent with:
- FastMCPClient connected to the "Research" tool server
- Sample code showing tool calling patterns

### Generate Agent with Both

```bash
restack g agent SmartAnalyzer --with-llm --tools DataTools
```

This generates an agent with:
- All LLM capabilities
- Tool integration
- Sample code showing combined usage (tools → LLM workflow)

## Migrating Existing Agents

### Step 1: Set Up Prerequisites

Before migrating, ensure you have the necessary infrastructure:

#### For LLM Support

```bash
# Generate LLM router configuration
restack g llm-config

# Set environment variables
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Create prompts
restack g prompt AgentPrompt --version 1.0.0
```

#### For Tool Support

```bash
# Generate tool server
restack g tool-server Research

# Set tool-specific environment variables
export BRAVE_API_KEY=...
```

### Step 2: Update Agent Imports

Add conditional imports to your existing agent:

```python
# Add to imports section
from typing import Any
from myproject.common.llm_router import LLMRouter, LLMRequest
from myproject.common.prompt_loader import PromptLoader
from myproject.common.fastmcp_manager import FastMCPClient
```

### Step 3: Add Initialization

Add an `__init__` method to your agent class:

```python
@workflow.defn(name="MyAgent")
class MyAgent:
    """My agent description."""
    
    def __init__(self) -> None:
        """Initialize agent with enhanced capabilities."""
        # For LLM support
        self.llm = LLMRouter()
        self.prompts = PromptLoader()
        
        # For tool support
        self.tools = FastMCPClient("Research")
    
    @workflow.run
    async def run(self, initial_state: MyAgentState) -> None:
        # ... existing code
```

### Step 4: Integrate LLM Calls

Replace hardcoded logic with LLM-driven decisions:

#### Before (Hardcoded Logic)

```python
async def run(self, initial_state: MyAgentState) -> None:
    state = initial_state
    
    # Hardcoded decision logic
    if state.priority == "high":
        action = "process_immediately"
    else:
        action = "queue"
```

#### After (LLM-Driven)

```python
async def run(self, initial_state: MyAgentState) -> None:
    state = initial_state
    
    # Load versioned prompt
    prompt_template = await self.prompts.load("myagent_decision", version="1.0")
    
    # Format with context
    prompt = prompt_template.format(
        priority=state.priority,
        task_description=state.description,
        current_load=state.system_load
    )
    
    # Get LLM decision
    response = await self.llm.chat(LLMRequest(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,  # Lower temp for consistent decisions
    ))
    
    action = response.content  # Parse action from response
```

### Step 5: Integrate Tool Calls

Add external data fetching with tools:

```python
async def run(self, initial_state: MyAgentState) -> None:
    state = initial_state
    
    # Call tool to gather context
    search_results = await self.tools.call_tool(
        "web_search",
        {"query": state.search_query, "max_results": 5}
    )
    
    # Load prompt template
    prompt_template = await self.prompts.load("myagent_analysis", version="1.0")
    
    # Format prompt with tool results
    prompt = prompt_template.format(
        query=state.search_query,
        search_results=search_results,
        context=state.additional_context
    )
    
    # Call LLM with enriched context
    response = await self.llm.chat(LLMRequest(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    ))
    
    log.info("Analysis complete", extra={"response": response.content})
```

## Complete Example: Before & After

### Before (Simple Agent)

```python
from datetime import timedelta
from enum import Enum

from restack_ai.workflow import workflow, log
from myproject.common.compat import BaseModel
from myproject.common.settings import settings


class ResearcherAgentEvent(str, Enum):
    """Events for Researcher agent."""
    START_RESEARCH = "start_research"


class ResearcherAgentState(BaseModel):
    """State model for Researcher agent."""
    topic: str
    status: str = "idle"


@workflow.defn(name="ResearcherAgent")
class ResearcherAgent:
    """
    Research agent for gathering information.
    """

    @workflow.run
    async def run(self, initial_state: ResearcherAgentState) -> None:
        """Run Researcher agent event loop."""
        state = initial_state
        log.info("ResearcherAgent started", extra={"initial_state": state})

        while True:
            event = await workflow.wait_condition(
                lambda: workflow.all_handlers_finished(),
                timeout=timedelta(seconds=settings.agent_event_timeout),
            )

            if event is None:
                log.info("ResearcherAgent timeout")
                continue

    @workflow.signal
    async def handle_event(self, event: ResearcherAgentEvent, payload: dict | None = None) -> None:
        """Handle incoming events."""
        log.info("Received event", extra={"event": event})
        # TODO: Process event
```

### After (Enhanced with LLM + Tools)

```python
from datetime import timedelta
from enum import Enum
from typing import Any

from restack_ai.workflow import workflow, log
from myproject.common.compat import BaseModel
from myproject.common.settings import settings
from myproject.common.llm_router import LLMRouter, LLMRequest
from myproject.common.prompt_loader import PromptLoader
from myproject.common.fastmcp_manager import FastMCPClient


class ResearcherAgentEvent(str, Enum):
    """Events for Researcher agent."""
    START_RESEARCH = "start_research"


class ResearcherAgentState(BaseModel):
    """State model for Researcher agent."""
    topic: str
    status: str = "idle"
    findings: list[dict] = []


@workflow.defn(name="ResearcherAgent")
class ResearcherAgent:
    """
    Research agent with LLM-powered analysis and web search capabilities.
    
    Enhanced capabilities:
    - LLM routing with multi-provider fallback
    - Versioned prompt management
    - FastMCP tool integration (Research)
    """

    def __init__(self) -> None:
        """Initialize agent with enhanced capabilities."""
        self.llm = LLMRouter()
        self.prompts = PromptLoader()
        self.tools = FastMCPClient("Research")

    @workflow.run
    async def run(self, initial_state: ResearcherAgentState) -> None:
        """Run Researcher agent event loop."""
        state = initial_state
        log.info("ResearcherAgent started", extra={"initial_state": state})

        # Initial research using LLM + tools
        # 1. Search web for topic
        search_results = await self.tools.call_tool(
            "web_search",
            {"query": state.topic, "max_results": 10}
        )
        
        # 2. Load analysis prompt
        prompt_template = await self.prompts.load("researcher_analyze", version="1.0")
        
        # 3. Format prompt with search results
        prompt = prompt_template.format(
            topic=state.topic,
            search_results=search_results,
        )
        
        # 4. Get LLM analysis
        response = await self.llm.chat(LLMRequest(
            messages=[
                {"role": "system", "content": "You are a research analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
        ))
        
        log.info("Initial research complete", extra={
            "topic": state.topic,
            "findings": response.content
        })

        while True:
            event = await workflow.wait_condition(
                lambda: workflow.all_handlers_finished(),
                timeout=timedelta(seconds=settings.agent_event_timeout),
            )

            if event is None:
                log.info("ResearcherAgent timeout")
                continue

    @workflow.signal
    async def handle_event(self, event: ResearcherAgentEvent, payload: dict | None = None) -> None:
        """Handle incoming events."""
        log.info("Received event", extra={"event": event})
        
        match event:
            case ResearcherAgentEvent.START_RESEARCH:
                await self._handle_start_research(payload)
    
    async def _handle_start_research(self, payload: dict | None) -> None:
        """Handle research start event."""
        if not payload or "topic" not in payload:
            log.warning("Missing topic in payload")
            return
        
        # Trigger research workflow
        # ... additional research logic
```

## Prompt Management

### Creating Versioned Prompts

```bash
# Create initial prompt
restack g prompt ResearcherAnalyze --version 1.0.0

# Update prompt with new version
restack g prompt ResearcherAnalyze --version 1.1.0
```

### Prompt File Structure

```
prompts/
├── researcher_analyze/
│   ├── 1.0.0.md
│   ├── 1.1.0.md
│   └── latest.md -> 1.1.0.md
└── registry.yaml
```

### Using Prompts in Agents

```python
# Load specific version
prompt = await self.prompts.load("researcher_analyze", version="1.0.0")

# Load latest version
prompt = await self.prompts.load("researcher_analyze", version="latest")

# Format with variables
formatted = prompt.format(
    topic="AI Safety",
    context="Research for blog post"
)
```

## Testing Enhanced Agents

### Update Test Files

```python
# tests/test_researcher_agent.py
import pytest
from unittest.mock import AsyncMock, Mock

from myproject.agents.researcher import ResearcherAgent, ResearcherAgentState


@pytest.mark.asyncio
async def test_researcher_with_llm_and_tools():
    """Test enhanced researcher agent."""
    # Arrange
    agent = ResearcherAgent()
    
    # Mock LLM response
    agent.llm.chat = AsyncMock(return_value=Mock(
        content="Analysis: AI Safety is an important field..."
    ))
    
    # Mock tool response
    agent.tools.call_tool = AsyncMock(return_value=[
        {"title": "AI Safety Overview", "url": "https://..."},
        {"title": "Latest Research", "url": "https://..."}
    ])
    
    # Mock prompt loader
    agent.prompts.load = AsyncMock(return_value=Mock(
        format=lambda **kwargs: f"Analyze: {kwargs['topic']}"
    ))
    
    # Act
    state = ResearcherAgentState(topic="AI Safety")
    # Test specific workflow methods
    
    # Assert
    agent.llm.chat.assert_called_once()
    agent.tools.call_tool.assert_called_once()
```

## Configuration

### LLM Router Configuration

Edit `config/llm_router.yaml`:

```yaml
providers:
  - name: openai
    model: gpt-4o-mini
    priority: 1
    timeout: 30.0
  
  - name: anthropic
    model: claude-3-5-sonnet-20241022
    priority: 2
    timeout: 30.0

default_provider: openai
fallback_enabled: true
```

### Tool Server Configuration

Edit `config/fastmcp_tools.yaml`:

```yaml
servers:
  Research:
    command: python
    args:
      - src/myproject/tools/research.py
    env:
      BRAVE_API_KEY: ${BRAVE_API_KEY}
```

## Best Practices

### 1. Prompt Versioning

- Use semantic versioning (1.0.0, 1.1.0, etc.)
- Test new prompt versions before updating `latest`
- Keep old versions for rollback capability

### 2. Error Handling

```python
try:
    response = await self.llm.chat(LLMRequest(
        messages=[{"role": "user", "content": prompt}]
    ))
except LLMError as e:
    log.error("LLM call failed", extra={"error": str(e)})
    # Fallback logic
```

### 3. Tool Call Timeouts

```python
tool_result = await self.tools.call_tool(
    "slow_operation",
    {"query": "complex query"},
    timeout=60.0  # Specify timeout for long-running tools
)
```

### 4. Prompt Engineering

- Be specific in prompts
- Provide clear context
- Use examples when appropriate
- Request structured output (JSON) for parsing

### 5. Cost Management

- Use cheaper models for simple tasks
- Cache prompt results when possible
- Set appropriate temperature (lower = more deterministic, cheaper)

## Troubleshooting

### LLM Router Not Found

**Error**: `ImportError: cannot import name 'LLMRouter'`

**Solution**:
```bash
# Generate LLM config if not already done
restack g llm-config
```

### Tool Server Connection Failed

**Error**: `FastMCPError: Failed to connect to tool server 'Research'`

**Solution**:
1. Verify tool server exists: `ls src/myproject/tools/`
2. Check environment variables
3. Test tool server independently

### Prompt Not Found

**Error**: `PromptNotFoundError: Prompt 'myagent_prompt' version '1.0' not found`

**Solution**:
```bash
# Create the prompt
restack g prompt MyAgentPrompt --version 1.0.0
```

## Next Steps

- Review [LLM Router documentation](./llm-router.md)
- Review [FastMCP Tools documentation](./fastmcp-tools.md)
- Review [Prompt Versioning documentation](./prompt-versioning.md)
- Check [CLI Reference](./cli-reference.md) for all generation options
