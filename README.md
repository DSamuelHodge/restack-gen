# 🚀 Restack Gen — Rails for Restack Agents

**Convention-over-configuration scaffolding CLI** for building Restack agents, workflows, and pipelines with **fault-tolerance baked in** and an **operator grammar** for chaining steps.

One command generates runnable, testable, observable code that registers itself with the Restack engine.

**NEW in v2.0:** Multi-provider LLM routing, FastMCP tool integration, and prompt versioning!

---

## ✨ Features

### Core Scaffolding (v1.0)
- **🏗️ Rails-style scaffolding**: `restack new`, `restack g agent`, `restack g workflow`, `restack g pipeline`
- **🔄 Omakase defaults**: Retries, timeouts, heartbeats, logging, typing, tests—all configured out of the box
- **📝 Operator grammar**: Chain workflows with `→` (sequence), `⇄` (loop), `→?` (conditional)
- **🎯 Type-safe**: Pydantic models for inputs/outputs, full type checking
- **🧪 Test-ready**: Unit and integration tests generated automatically
- **🔍 Observable**: Structured logging with correlation IDs
- **⚙️ Configurable**: CLI flags, environment variables, and YAML settings with clear precedence

### LLM + Tools + Prompts (v2.0)
- **🤖 Multi-provider LLM routing**: OpenAI, Anthropic with automatic fallback
- **🏢 Kong AI Gateway support**: AI rate limiting, cost tracking, content safety
- **🔌 FastMCP tool scaffolding**: Generate tool servers with `restack g tool-server`
- **🚀 Autostart tool servers**: Servers start automatically with Restack service
- **🛠️ Tool calling API**: Clean FastMCPClient interface for agents
- **🏥 Health monitoring**: `restack doctor --check-tools` validates server health
- **📝 Prompt versioning**: Git-tracked prompts with semantic versioning and loader (PR #5)
- **🛡️ Circuit breaker**: Automatic failure detection and recovery
- **🔄 Intelligent fallback**: Timeout, 5xx, rate limit handling
- **📊 Response metadata**: Latency, cost, and rate limit tracking

---

## 📦 Installation

```bash
# Recommended: Install with uv
uv pip install restack-gen

# Or with pip
pip install restack-gen

# Verify installation
restack --help
```

---

## 🚀 Quick Start

### 1. Create a new project

```bash
restack new myapp
cd myapp
```

This generates:
```
myapp/
  config/
    settings.yaml          # Configuration
  server/
    service.py             # Registers agents/workflows/functions
  client/
    run_workflow.py        # Example client usage
  src/myapp/
    agents/                # Long-lived, event-driven agents
    workflows/             # Orchestrators (typed, stepwise)
    functions/             # Stateless leaf operations
    common/
      retries.py           # Default retry policies
      settings.py          # Pydantic settings
      compat.py            # Pydantic v1/v2 compatibility
  tests/                   # Unit & integration tests
```

### 2. Generate resources

```bash
# Generate an agent
restack g agent Onboarding

# Generate a workflow
restack g workflow EmailCampaign

# Generate a function
restack g function SendEmail

# Generate a tool server (NEW in v2.0!)
restack g tool-server Research
```

### 3. Generate LLM configuration (NEW in v2.0!)

```bash
# Option 1: Direct provider calls (simple, no infrastructure)
restack g llm-config --backend direct

# Option 2: Kong AI Gateway (enterprise features)
restack g llm-config --backend kong

# Configure your API keys
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# For Kong backend, also set:
export KONG_GATEWAY_URL=http://localhost:8000
```

This generates:
- `config/llm_router.yaml` - Provider configuration
- `src/myapp/common/llm_router.py` - Router implementation

**Direct backend:** Simple HTTP calls to provider APIs  
**Kong backend:** AI rate limiting, cost tracking, content safety filters

**Testing Kong Gateway?** See [Kong Quick Test Guide](docs/kong-setup-test.md) for setup validation.

Use in your agents:

```python
from myapp.common.llm_router import LLMRouter, LLMRequest

router = LLMRouter()
response = await router.chat(LLMRequest(
    messages=[{"role": "user", "content": "Hello!"}]
))
print(response.content)
print(response.metadata)  # Kong: latency, cost, rate limit info
```

**See [LLM Router docs](docs/llm-router.md) for complete guide.**

### 4. Generate FastMCP tool servers (NEW in v2.0!)

```bash
# Generate a tool server
restack g tool-server Research
```

This generates:
- `src/myapp/tools/research_mcp.py` - FastMCP tool server with sample tools
- `src/myapp/common/fastmcp_manager.py` - Server lifecycle manager (first time only)
- `config/tools.yaml` - Tool server configuration (first time only)

The generated server includes three sample tools:
- `web_search` - Brave Search API integration (placeholder)
- `extract_urls` - Extract URLs from text
- `calculate` - Safe math expression evaluator

#### Autostart with Restack (Recommended)

Configure autostart in `config/tools.yaml`:

```yaml
fastmcp:
  servers:
    - name: "research_tools"
      autostart: true  # Start with Restack service
```

Then start normally:

```bash
restack up  # Tool servers start automatically!
```

#### Use Tools from Agents

```python
from myapp.common.fastmcp_manager import FastMCPClient

async def research_workflow(ctx):
    async with FastMCPClient("research_tools") as client:
        result = await client.call_tool(
            "web_search",
            {"query": "latest AI news", "max_results": 5}
        )
        return result
```

#### Monitor Server Health

```bash
# Check all health including tool servers
restack doctor --check-tools

# Verbose output with server details
restack doctor --check-tools --verbose
```

Replace sample tools with your domain-specific logic. **See [FastMCP Tools docs](docs/fastmcp-tools.md) for complete guide.**

### 5. Generate a pipeline with operator grammar

```bash
restack g pipeline BlogPipeline \
  --operators "IDEATE ⇄ RESEARCH → PLAN → OUTLINE → DRAFT ⇄ REVIEW → POLISH → PUBLISH → PROMOTE →? REPURPOSE" \
  --style subworkflows
```

**Operators:**
- `→` : Sequential execution (A then B)
- `⇄` : Refinement loop (iterate between A and B)
- `→?` : Conditional step (run B only if condition met)

### 6. Run the server

```bash
# Check everything is configured correctly
restack doctor

# Start the server (registers all resources with Restack engine)
restack run:server
```

### 7. Trigger workflows

```bash
# Use the generated client
python client/run_workflow.py
```

---

## 📖 Documentation

- **[⬇️ Installation](docs/installation.md)** - Install/upgrade/uninstall and requirements
- **[🚀 Quickstart](docs/quickstart.md)** - Create a project and run it locally
- **[🧰 CLI Reference](docs/cli-reference.md)** - Commands, options, and examples
- **[🧩 Templates](docs/templates.md)** - Generated code, headers, and customization
- **[� LLM Router](docs/llm-router.md)** - Multi-provider routing with Kong support (v2.0)
- **[🔌 FastMCP Tools](docs/fastmcp-tools.md)** - Tool server scaffolding guide (v2.0)
- **[�🩺 Troubleshooting](docs/troubleshooting.md)** - Common issues and fixes
- **[📦 Release Process](docs/RELEASE.md)** - Building, tagging, publishing
- **[📋 Decisions Log](docs/DECISIONS.md)** - Architecture decisions and rationales
- **[📝 Product Specs](specs/product_specs.md)** - Detailed feature specifications
- **[🗺️ Work Plan](specs/plan.md)** - Implementation roadmap

---

## 🧪 Examples

- Research agent (LLM + Tools): `examples/research_agent/`
  - Offline stubs by default; auto-switches to real router/tools if added
  - Shows tool invocation + LLM summarization end-to-end
- Prompted multi-step pipeline: `examples/prompted_pipeline/`
  - Minimal prompt loader reading `config/prompts.yaml`
  - Demonstrates prompt versioning + multi-step processing

---

## 🎨 Operator Grammar Examples

### Simple sequence
```
FETCH → PROCESS → STORE
```

### With refinement loop
```
DRAFT ⇄ REVIEW → PUBLISH
```

### With conditional
```
ANALYZE → CLASSIFY →? ESCALATE
```

### Complex pipeline
```
IDEATE ⇄ RESEARCH → PLAN → OUTLINE → DRAFT ⇄ REVIEW → POLISH → PUBLISH → PROMOTE →? REPURPOSE
```

---

## ⚙️ Configuration

Settings precedence (highest to lowest):
1. **CLI flags**: `--engine-url`, `--task-queue`, etc.
2. **Environment variables**: `RESTACK_ENGINE_URL`, `RETRY_MAX_ATTEMPTS`, etc.
3. **settings.yaml**: Project-level configuration
4. **Code defaults**: Built into generated templates

Example `config/settings.yaml`:
```yaml
engine_url: http://localhost:7700
task_queue_default: restack

retry:
  initial_seconds: 5.0
  backoff: 2.0
  max_interval_seconds: 120.0
  max_attempts: 6

pipeline:
  loops:
    ideate_research:
      max: 3
    draft_review:
      max: 5
```

---

## 🧪 Testing

```bash
# Run all tests
make test

# Run tests without slow ones
make test-fast

# Run with coverage
make test-cov

# Run integration tests only
make test-integration
```

Generated projects include:
- ✅ Unit tests for each resource
- ✅ Integration tests for pipelines
- ✅ Test fixtures in `conftest.py`
- ✅ Offline mode by default (no engine required)
- ✅ Optional online mode with `RESTACK_ENGINE_URL`

---

## 🛠️ Development

```bash
# Clone the repo
git clone https://github.com/restackio/restack-gen.git
cd restack-gen

# Install dependencies and pre-commit hooks
make setup

# Format code
make fmt

# Lint
make lint

# Type check
make typecheck

# Run tests
make test
```

---

## 🎯 CLI Commands

| Command | Description |
|---------|-------------|
| `restack new <app>` | Create new project with omakase layout |
| `restack g agent <Name>` | Generate agent with events & tests |
| `restack g workflow <Name>` | Generate workflow with typed I/O |
| `restack g function <Name>` | Generate function with test |
| `restack g pipeline <Name> --operators "..."` | Parse operator grammar & emit orchestrator |
| `restack run:server` | Start server (registers resources) |
| `restack doctor` | Check environment, config, permissions |

### Common Flags

- `--force` - Overwrite existing files
- `--dry-run[=minimal\|diff]` - Preview without writing
- `--task-queue <name>` - Set task queue
- `--omit-tests` - Skip test generation
- `--models external\|split` - Model placement strategy
- `--map TOKEN:CustomName` - Override token-to-class mapping

---

## 🔍 Doctor Checks

`restack doctor` validates:

✓ Python 3.11+  
✓ Package versions (restack-ai, pydantic>=2.7.0, etc.)  
✓ Engine connectivity  
✓ Import resolution  
✓ File permissions  
✓ Git status (warns on uncommitted changes)  

Example output:
```
Doctor
✓ Python 3.11.8
✓ restack-ai 1.2.3 (compatible)
! pydantic 2.6.4 (recommended >=2.7.0)
✓ Write access: src/, server/, client/, tests/
! Git: 3 unstaged files (commit or use --force)
✓ Engine reachable at http://localhost:7700
```

---

## 🎭 Generated Code Features

All generated files include:

- **📝 Header markers** with timestamp & command
- **🔄 Retry policies** (exponential backoff)
- **⏱️ Timeouts** (2min default)
- **💓 Heartbeats** (30s default)
- **📊 Structured logging** with correlation IDs
- **🎯 Type hints** (Pydantic models)
- **🧪 Tests** (unit + integration)

Example header:
```python
# @generated by restack-gen v1.0.0 (2025-10-24T14:05:12Z)
# command: restack g workflow BlogWorkflow --task-queue restack
# do not edit this header; use --force to overwrite
```

---

## 🗺️ Roadmap

**v1.0** (current)
- ✅ Sequential (`→`), loop (`⇄`), conditional (`→?`) operators
- ✅ Subworkflow and function styles
- ✅ AST-based service registration
- ✅ Comprehensive doctor checks

**v1.1** (planned)
- [ ] Parallel operator (`⊕`) codegen
- [ ] Visual DAG output
- [ ] `restack destroy` command
- [ ] `restack upgrade` migration tool

---

## 🤝 Contributing

We welcome contributions! Please see our [contribution guidelines](CONTRIBUTING.md) (coming soon).

---

## 📄 License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

Built with:
- [Typer](https://typer.tiangolo.com/) - CLI framework
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [Restack](https://www.restack.io/) - Agent orchestration engine

---

**Made with ❤️ by the Restack team**

Questions? Open an issue or reach out on [Discord](https://discord.gg/restack).
