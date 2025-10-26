# FastMCP Tool Server Scaffolding

This guide covers how to generate and work with FastMCP tool servers in restack-gen.

## Overview

FastMCP is a Python library for building Model Context Protocol (MCP) tool servers. The restack-gen generator creates fully-functional tool server scaffolding with sample tools, configuration, and best practices.

## Quick Start

### 1. Generate a Tool Server

```bash
restack g tool-server Research
```

This creates:
- `src/<project>/tools/research_mcp.py` - Tool server implementation
- `config/tools.yaml` - FastMCP configuration (first time only)
- `src/<project>/tools/__init__.py` - Package initialization

### 2. Review Generated Code

The generated server includes three sample tools:

```python
@mcp.tool()
async def web_search(query: str, max_results: int = 10) -> dict:
    """Search the web using Brave Search API."""
    # Implementation placeholder
    pass

@mcp.tool()
async def extract_urls(text: str) -> list[str]:
    """Extract all URLs from text."""
    # Working implementation
    pass

@mcp.tool()
async def calculate(expression: str) -> float:
    """Safely evaluate a mathematical expression."""
    # Working implementation
    pass
```

### 3. Set Environment Variables

Add your API keys to `.env`:

```bash
BRAVE_API_KEY=your_api_key_here
```

### 4. Implement Custom Tools

Replace sample tools with your domain-specific logic:

```python
@mcp.tool()
async def analyze_sentiment(text: str) -> dict:
    """Analyze sentiment of text using GPT-4."""
    # Your implementation
    pass
```

### 5. Configure Autostart (Recommended)

Set `autostart: true` in `config/tools.yaml` to start servers with Restack:

```yaml
fastmcp:
  servers:
    - name: "research_tools"
      autostart: true  # Start automatically with Restack service
```

Then start your Restack service normally:

```bash
restack up
```

Your tool servers will start automatically! See [Autostart with Restack Service](#autostart-with-restack-service) for details.

### 6. Use Tools from Agents

Call tools from your workflows using `FastMCPClient`:

```python
from myproject.common.fastmcp_manager import FastMCPClient

async def my_workflow(ctx):
    async with FastMCPClient("research_tools") as client:
        result = await client.call_tool("web_search", {"query": "AI news"})
        return result
```

See [Calling Tools from Agents](#calling-tools-from-agents) for complete examples.

## Tool Development

### Tool Decorator

The `@mcp.tool()` decorator registers functions as MCP tools:

```python
@mcp.tool()
async def my_tool(param1: str, param2: int = 10) -> dict:
    """Tool description shown to LLMs."""
    # Must be async function
    # Type hints are required
    # Docstring becomes tool description
    return {"result": "value"}
```

### Tool Best Practices

1. **Always use async functions** - FastMCP requires async/await
2. **Provide type hints** - Used for parameter validation
3. **Write clear docstrings** - LLMs use these to understand tool purpose
4. **Return structured data** - Use dicts or dataclasses for complex results
5. **Handle errors gracefully** - Catch exceptions and return error information

### Example: API Integration Tool

```python
import httpx
from typing import Optional

@mcp.tool()
async def fetch_weather(
    city: str,
    units: str = "metric"
) -> dict:
    """Get current weather for a city.
    
    Args:
        city: City name (e.g., "London", "New York")
        units: Temperature units ("metric" or "imperial")
    
    Returns:
        Dict with temperature, conditions, humidity, etc.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://api.openweathermap.org/data/2.5/weather",
            params={
                "q": city,
                "units": units,
                "appid": os.getenv("OPENWEATHER_API_KEY")
            }
        )
        response.raise_for_status()
        data = response.json()
        
        return {
            "temperature": data["main"]["temp"],
            "conditions": data["weather"][0]["description"],
            "humidity": data["main"]["humidity"],
            "wind_speed": data["wind"]["speed"]
        }
```

## Server Configuration

### tools.yaml Structure

The `config/tools.yaml` file configures all tool servers:

```yaml
fastmcp:
  servers:
    - name: "research_tools"
      module: "src.myproject.tools.research_mcp"
      class: "ResearchToolServer"
      transport: "stdio"
      autostart: true
      env:
        BRAVE_API_KEY: "${BRAVE_API_KEY}"
      health_check:
        enabled: true
        interval: 30
  
  settings:
    timeout: 30
    retry:
      max_attempts: 3
      backoff_multiplier: 2
      max_backoff: 10
    logging:
      level: "INFO"
      format: "json"
```

### Configuration Options

#### Server Options

- `name` - Unique identifier for the server
- `module` - Python import path to the server file
- `class` - Server class name (must inherit from base or implement protocol)
- `transport` - Communication protocol:
  - `"stdio"` - Standard input/output (for local process communication)
  - `"sse"` - Server-Sent Events over HTTP (for remote access)
- `autostart` - Whether to start server automatically with Restack service
- `env` - Environment variables available to the server
- `health_check` - Health monitoring configuration

#### Global Settings

- `timeout` - Maximum seconds for tool execution
- `retry.max_attempts` - Number of retry attempts for failed tools
- `retry.backoff_multiplier` - Exponential backoff multiplier
- `retry.max_backoff` - Maximum backoff delay in seconds
- `logging.level` - Log verbosity (DEBUG, INFO, WARNING, ERROR)
- `logging.format` - Log format ("json" or "text")

### Multiple Tool Servers

You can generate multiple tool servers for different domains:

```bash
restack g tool-server Research
restack g tool-server DataAnalysis
restack g tool-server EmailAutomation
```

Each server is added to `config/tools.yaml` automatically.

## FastMCP Server Manager

The FastMCP Server Manager provides lifecycle management for all tool servers in your project. It's automatically generated when you create your first tool server and handles:

- **Automatic server startup** with the Restack service
- **Configuration loading** from `tools.yaml`
- **Health monitoring** of running servers
- **Graceful shutdown** on service termination
- **Server registry** for tracking active instances

### Manager API

The manager is located at `src/<project>/common/fastmcp_manager.py` and provides:

#### FastMCPServerManager

```python
from myproject.common.fastmcp_manager import FastMCPServerManager

# Get singleton manager instance
manager = FastMCPServerManager()

# Start all servers with autostart=true
await manager.start_all()

# Start specific server
await manager.start_server("research_tools")

# Stop specific server
await manager.stop_server("research_tools")

# Stop all servers
await manager.stop_all()

# Check health of specific server
status = await manager.health_check("research_tools")
# Returns: {"status": "healthy", "details": {...}}

# Check health of all servers
statuses = await manager.health_check_all()
# Returns: {"research_tools": {...}, "data_tools": {...}}

# List all configured servers
servers = manager.list_servers()
# Returns: [{"name": "research_tools", "status": "running", ...}]

# Get running server instance
server = manager.get_server("research_tools")
```

#### Global Helpers

```python
from myproject.common.fastmcp_manager import start_tool_servers, stop_tool_servers

# Start all autostart servers (used by service.py)
await start_tool_servers()

# Stop all running servers (used by service.py)
await stop_tool_servers()
```

### Configuration Loading

The manager automatically loads configuration from `config/tools.yaml`:

```python
# Manager reads this configuration on initialization
manager = FastMCPServerManager()  # Loads config/tools.yaml

# Access server configurations
servers = manager.list_servers()
for server in servers:
    print(f"{server['name']}: {server['status']}")
```

### Server Registry

The manager maintains a registry of running servers:

```python
# Check if server is running
server = manager.get_server("research_tools")
if server:
    print(f"Server is running: {server}")
else:
    print("Server not running")

# List all servers with status
servers = manager.list_servers()
for server in servers:
    print(f"{server['name']}: {server['status']}")
```

### Error Handling

The manager handles common errors gracefully:

```python
try:
    await manager.start_server("research_tools")
except Exception as e:
    logger.error(f"Failed to start server: {e}")
    # Server startup errors are logged but don't crash the service

# Health checks return error status instead of raising
status = await manager.health_check("research_tools")
if status["status"] == "unhealthy":
    logger.warning(f"Server unhealthy: {status['details']}")
```

## Autostart with Restack Service

When you set `autostart: true` in `config/tools.yaml`, tool servers automatically start with the Restack service.

### How Autostart Works

1. **Service startup**: When `service.py` initializes, it checks for `config/tools.yaml`
2. **Manager import**: If found, imports `FastMCPServerManager`
3. **Server startup**: Calls `start_tool_servers()` to start all autostart servers
4. **Background execution**: Servers run as asyncio background tasks
5. **Graceful shutdown**: On service termination, calls `stop_tool_servers()`

### Service Integration

The generated `service.py` includes tool server integration:

```python
# At top of service.py
try:
    from myproject.common.fastmcp_manager import start_tool_servers, stop_tool_servers
    FASTMCP_AVAILABLE = Path("config/tools.yaml").exists()
except ImportError:
    FASTMCP_AVAILABLE = False

async def main():
    # ... Restack client setup ...
    
    try:
        # Start tool servers if configured
        if FASTMCP_AVAILABLE:
            logger.info("Starting FastMCP tool servers...")
            await start_tool_servers()
        
        # Start Restack service
        await client.start_service(services=[service])
    finally:
        # Graceful shutdown
        if FASTMCP_AVAILABLE:
            logger.info("Stopping FastMCP tool servers...")
            await stop_tool_servers()
```

### Startup Logging

Tool server startup is logged for visibility:

```
INFO - Starting FastMCP tool servers...
INFO - Starting tool server: research_tools
INFO - Tool server research_tools started successfully
INFO - Starting tool server: data_tools
INFO - Tool server data_tools started successfully
```

### Startup Errors

If a server fails to start, the error is logged but doesn't crash the service:

```python
# In FastMCPServerManager.start_server()
try:
    # ... server startup logic ...
    logger.info(f"Tool server {name} started successfully")
except Exception as e:
    logger.error(f"Failed to start tool server {name}: {e}")
    # Service continues running even if tool server fails
```

### Disabling Autostart

To disable autostart for a specific server:

```yaml
# config/tools.yaml
fastmcp:
  servers:
    - name: "research_tools"
      autostart: false  # Don't start automatically
```

## Calling Tools from Agents

Use `FastMCPClient` to call tools from your Restack agents.

### Basic Usage

```python
from myproject.common.fastmcp_manager import FastMCPClient

async def research_workflow(ctx: WorkflowContext):
    # Use client as async context manager
    async with FastMCPClient("research_tools") as client:
        # Call tool and get result
        result = await client.call_tool(
            "web_search",
            {"query": "latest AI news", "max_results": 5}
        )
        print(result)  # {"results": [...]}
```

### Listing Available Tools

```python
async with FastMCPClient("research_tools") as client:
    # Get all available tools
    tools = await client.list_tools()
    for tool in tools:
        print(f"{tool['name']}: {tool['description']}")
```

### Error Handling

```python
from myproject.common.fastmcp_manager import FastMCPClient

async def safe_tool_call():
    try:
        async with FastMCPClient("research_tools") as client:
            result = await client.call_tool("web_search", {"query": "test"})
            return result
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        return {"error": str(e)}
```

### Multiple Tool Servers

You can use multiple tool servers in the same workflow:

```python
async def multi_tool_workflow(ctx: WorkflowContext):
    # Use research tools
    async with FastMCPClient("research_tools") as research:
        urls = await research.call_tool("web_search", {"query": "AI"})
    
    # Use data analysis tools
    async with FastMCPClient("data_tools") as data:
        analysis = await data.call_tool("analyze_data", {"data": urls})
    
    return analysis
```

### Agent Integration Example

```python
from restack_ai import function
from myproject.common.fastmcp_manager import FastMCPClient

@function(name="research_agent")
async def research_agent(ctx, query: str) -> dict:
    """Agent that uses tool servers for research."""
    
    # Call research tool
    async with FastMCPClient("research_tools") as client:
        # Search for information
        search_results = await client.call_tool(
            "web_search",
            {"query": query, "max_results": 10}
        )
        
        # Extract URLs from results
        urls = await client.call_tool(
            "extract_urls",
            {"text": str(search_results)}
        )
    
    return {"search_results": search_results, "urls": urls}
```

### Tool Call Parameters

```python
# Tool call signature
result = await client.call_tool(
    tool_name: str,      # Name of the tool to call
    arguments: dict      # Tool parameters as dictionary
) -> dict                # Tool returns result as dictionary
```

## Health Monitoring

Monitor tool server health using the `restack doctor` command.

### Basic Health Check

```bash
# Check all project health including tool servers
restack doctor --check-tools
```

Output:

```
🏥 Running Restack Project Health Checks
========================================

Environment Checks:
  ✓ Python version: 3.12.0
  ✓ pip version: 23.3.1

Dependency Checks:
  ✓ restack-ai: 0.2.0
  ✓ python-dotenv: 1.0.0

Project Structure:
  ✓ src/myproject: Present
  ✓ config/settings.yaml: Present

Tool Server Checks:
  ✓ config/tools.yaml: Valid
  ✓ FastMCP: Installed (0.5.0)
  ✓ research_tools: Module importable
  ✓ data_tools: Module importable

Health Status:
  ✓ research_tools: Healthy
  ✓ data_tools: Healthy

All checks passed! ✓
```

### Verbose Health Check

For detailed server information:

```bash
restack doctor --check-tools --verbose
```

Output includes:

```
Tool Server Checks:
  ✓ config/tools.yaml: Valid (2 servers configured)
  ✓ FastMCP: Installed (0.5.0)
  
  Server: research_tools
    Module: src.myproject.tools.research_mcp
    Class: ResearchToolServer
    Transport: stdio
    Autostart: true
    Status: ✓ Healthy
    
  Server: data_tools
    Module: src.myproject.tools.data_mcp
    Class: DataToolServer
    Transport: stdio
    Autostart: true
    Status: ✓ Healthy
```

### Health Check Failures

If a server is unhealthy:

```
Health Status:
  ✗ research_tools: Unhealthy
    Error: Server not responding
    Suggestion: Check if server process is running
  
  ✓ data_tools: Healthy
```

### Programmatic Health Checks

Check health from Python code:

```python
from myproject.common.fastmcp_manager import FastMCPServerManager

async def check_server_health():
    manager = FastMCPServerManager()
    
    # Check specific server
    status = await manager.health_check("research_tools")
    if status["status"] == "healthy":
        print("Server is healthy!")
    else:
        print(f"Server unhealthy: {status['details']}")
    
    # Check all servers
    statuses = await manager.health_check_all()
    for name, status in statuses.items():
        print(f"{name}: {status['status']}")
```

### Health Check Configuration

Configure health checks in `config/tools.yaml`:

```yaml
fastmcp:
  servers:
    - name: "research_tools"
      health_check:
        enabled: true       # Enable health checks
        interval: 30        # Check every 30 seconds
        timeout: 5          # Timeout after 5 seconds
```

### Troubleshooting Unhealthy Servers

1. **Check server logs**: Look for startup errors
2. **Verify configuration**: Ensure `tools.yaml` is correct
3. **Test manually**: Run server standalone to isolate issues
4. **Check dependencies**: Ensure all required packages installed
5. **Review environment**: Verify API keys and env vars are set

## Server Class Implementation

### Required Methods

Every tool server must implement:

```python
class ResearchToolServer:
    def __init__(self):
        self.mcp = mcp  # Reference to FastMCP instance
    
    async def run(self, transport: str = "stdio"):
        """Start the server with specified transport."""
        await self.mcp.run(transport=transport)
    
    async def health_check(self) -> bool:
        """Check if server is healthy and has tools."""
        tools = self.mcp.list_tools()
        return len(tools) > 0
```

### Custom Initialization

Add server-specific setup in `__init__`:

```python
class ResearchToolServer:
    def __init__(self):
        self.mcp = mcp
        self.api_key = os.getenv("BRAVE_API_KEY")
        if not self.api_key:
            raise ValueError("BRAVE_API_KEY environment variable required")
        
        # Initialize shared resources
        self.http_client = httpx.AsyncClient()
        self.cache = {}
```

### Cleanup Resources

Use async context manager for cleanup:

```python
class ResearchToolServer:
    async def __aenter__(self):
        self.http_client = httpx.AsyncClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
```

## Testing

### Manual Testing

Run the server directly:

```bash
python src/myproject/tools/research_mcp.py
```

Test health check:

```python
import asyncio
from src.myproject.tools.research_mcp import ResearchToolServer

async def test():
    server = ResearchToolServer()
    is_healthy = await server.health_check()
    print(f"Server healthy: {is_healthy}")

asyncio.run(test())
```

### Unit Testing

Test individual tools:

```python
import pytest
from src.myproject.tools.research_mcp import web_search

@pytest.mark.asyncio
async def test_web_search():
    result = await web_search("Python testing", max_results=5)
    assert "results" in result
    assert len(result["results"]) <= 5
```

### Integration Testing

Test server lifecycle:

```python
@pytest.mark.asyncio
async def test_server_lifecycle():
    server = ResearchToolServer()
    
    # Health check
    assert await server.health_check()
    
    # Tool listing
    tools = server.mcp.list_tools()
    assert len(tools) >= 3
    
    # Tool execution would require MCP client
```

## Transport Protocols

### stdio (Local)

Default mode for local process communication:

```python
# Server
await server.run(transport="stdio")

# Client (conceptual)
# Communicates via stdin/stdout pipes
```

Use for:
- Development and testing
- Integration with local LLM applications
- Command-line tools

### sse (HTTP)

Server-Sent Events over HTTP for remote access:

```python
# Server
await server.run(transport="sse")

# Exposes HTTP endpoint
# Clients connect via EventSource API
```

Use for:
- Production deployments
- Remote LLM access
- Web-based applications
- Multi-client scenarios

## Deployment

### Development

**Recommended: Use Autostart**

The easiest way to run tool servers in development:

```bash
# Set autostart: true in config/tools.yaml
# Then start Restack service
restack up
```

Tool servers start automatically with the Restack service and stop gracefully on shutdown.

**Alternative: Manual Execution**

```bash
# Run single server standalone
python src/myproject/tools/research_mcp.py
```

### Production

#### Option 1: Systemd Service

Create `/etc/systemd/system/research-tools.service`:

```ini
[Unit]
Description=Research Tool Server
After=network.target

[Service]
Type=simple
User=restack
WorkingDirectory=/app
Environment="BRAVE_API_KEY=your_key"
ExecStart=/usr/bin/python src/myproject/tools/research_mcp.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

#### Option 2: Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV BRAVE_API_KEY=""
CMD ["python", "src/myproject/tools/research_mcp.py"]
```

#### Option 3: Supervisor

Add to `supervisord.conf`:

```ini
[program:research-tools]
command=python src/myproject/tools/research_mcp.py
directory=/app
environment=BRAVE_API_KEY="your_key"
autostart=true
autorestart=true
```

## Advanced Topics

### Tool Categories

Organize tools by domain:

```python
# Research tools
@mcp.tool()
async def web_search(...): pass

@mcp.tool()
async def academic_search(...): pass

# Data tools
@mcp.tool()
async def analyze_csv(...): pass

@mcp.tool()
async def generate_chart(...): pass
```

### Error Handling

Return structured error information:

```python
@mcp.tool()
async def risky_operation(param: str) -> dict:
    try:
        result = await perform_operation(param)
        return {"success": True, "data": result}
    except ValueError as e:
        return {"success": False, "error": "validation", "message": str(e)}
    except Exception as e:
        return {"success": False, "error": "internal", "message": str(e)}
```

### Rate Limiting

Implement tool-level rate limits:

```python
from asyncio import Semaphore

rate_limiter = Semaphore(5)  # 5 concurrent calls

@mcp.tool()
async def rate_limited_api(param: str) -> dict:
    async with rate_limiter:
        return await call_external_api(param)
```

### Caching

Add result caching for expensive operations:

```python
from functools import lru_cache
import hashlib

cache = {}

@mcp.tool()
async def cached_search(query: str) -> dict:
    cache_key = hashlib.md5(query.encode()).hexdigest()
    
    if cache_key in cache:
        return cache[cache_key]
    
    result = await expensive_search(query)
    cache[cache_key] = result
    return result
```

### Authentication

Validate API keys before tool execution:

```python
@mcp.tool()
async def authenticated_tool(api_key: str, data: str) -> dict:
    if not validate_api_key(api_key):
        return {"error": "Invalid API key"}
    
    return await process_data(data)
```

## Troubleshooting

### Server Won't Start

**Problem**: `ModuleNotFoundError` or import errors

**Solution**: Check Python path and module structure:
```bash
export PYTHONPATH="${PYTHONPATH}:."
python -c "from src.myproject.tools.research_mcp import ResearchToolServer"
```

### Health Check Fails

**Problem**: `health_check()` returns `False`

**Solution**: Verify tools are registered:
```python
tools = mcp.list_tools()
print(f"Registered tools: {[t['name'] for t in tools]}")
```

### Environment Variables Not Loading

**Problem**: Tools can't access API keys

**Solution**: Load `.env` file explicitly:
```python
from dotenv import load_dotenv
load_dotenv()
```

### Tool Execution Timeout

**Problem**: Tools exceed configured timeout

**Solution**: Increase timeout in `tools.yaml`:
```yaml
settings:
  timeout: 60  # Increase to 60 seconds
```

## API Reference

### FastMCP Core

- `FastMCP(name: str)` - Create FastMCP instance
- `@mcp.tool()` - Decorator to register tool functions
- `mcp.list_tools()` - Get list of registered tools
- `await mcp.run(transport)` - Start server with transport protocol

### Generated Server Class

- `__init__()` - Initialize server instance
- `async run(transport)` - Start server (stdio or sse)
- `async health_check()` - Verify server health

## Examples

### Example 1: Web Research Tools

```bash
restack g tool-server Research
```

Implement web search, article extraction, and summarization tools.

### Example 2: Data Analysis Tools

```bash
restack g tool-server Analytics
```

Implement CSV analysis, data visualization, and statistical tools.

### Example 3: Email Automation Tools

```bash
restack g tool-server Email
```

Implement email sending, template rendering, and attachment handling.

## Next Steps

1. **Explore FastMCP Documentation**: Learn advanced features at FastMCP docs
2. **Build Custom Tools**: Replace sample tools with domain-specific logic
3. **Set Up Monitoring**: Add logging and metrics to track tool usage
4. **Deploy to Production**: Use Docker, systemd, or supervisor for reliable deployment
5. **Integrate with LLMs**: Connect your tool server to Claude, GPT-4, or other LLMs

## Related Documentation

- [Installation Guide](installation.md)
- [CLI Reference](cli-reference.md)
- [Templates Guide](templates.md)
- [Troubleshooting](troubleshooting.md)

## Support

For issues or questions:
- GitHub Issues: [restack-agent-generator/issues](https://github.com/your-org/restack-agent-generator/issues)
- Documentation: [Full docs](../README.md)
