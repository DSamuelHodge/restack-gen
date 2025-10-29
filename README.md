# Restack Gen — Scaffolding for Restack Agents

Restack Gen is a convention-over-configuration CLI that scaffolds Restack agents, workflows, functions, tool servers, and LLM integrations. It produces runnable, testable, and observable code with sensible defaults for retries, timeouts, and structured logging.

## Key features

- Rails-style scaffolding: `restack new`, `restack g agent`, `restack g workflow`, `restack g pipeline`
- Generated tests (unit and integration) and CI-friendly project layout
- Type-safe code using Pydantic models
- Operator grammar for composing pipelines (sequence, loop, conditional)
- LLM routing, prompt versioning, and FastMCP tool integration (v2.0)
- Health checks and doctor commands for sanity validation

## Installation

Install via pip (recommended using `uv` if available):

```powershell
uv pip install restack-gen
# or
pip install restack-gen
```

Verify installation:

```powershell
restack --help
```

## Quick start


Create a new project and scaffold a real-world, multi-agent research pipeline:

```powershell
# 1. Create your project
restack new research_hub
cd research_hub

# 2. Scaffold core agents, workflows, and functions
restack g agent Researcher --with-llm --tools ResearchTools
restack g agent Reviewer --with-llm
restack g function fetch_web_results
restack g function summarize_findings
restack g function score_relevance

# 3. Compose a pipeline using operator expressions
restack g pipeline LiteratureReview --operators "Researcher → fetch_web_results → summarize_findings → Reviewer → score_relevance"

# 4. Add a FastMCP tool server and LLM config
restack g tool-server ResearchTools
restack g llm-config --backend direct

# 5. Add a versioned prompt for the Researcher agent
restack g prompt LiteratureQuery --version 1.0.0

# 6. (Optional) Scaffold a full-featured agent with state/events
restack g scaffold LeadScientist

# 7. (Optional) Add a migration to evolve your prompt registry
restack g migration AddSummaryPrompt --target prompts
```

This example demonstrates how to:
- Build a multi-step pipeline with agents, functions, and operator grammar
- Integrate LLMs and tool servers
- Use versioned prompts and configuration migrations

Operator expressions like `A → B → C | D` let you compose complex, readable agent workflows. See the CLI Reference for more.

Run basic checks and start the server:

```powershell
restack doctor
restack run:server
# trigger a workflow with the generated client
python client/run_workflow.py
```

## v2.0 project layout

A project generated with v2.0 includes core scaffold plus optional LLM/tool/prompt add-ons:

```
myapp/
  config/
    settings.yaml           # Project settings
    llm_router.yaml         # LLM provider router configuration (added by g llm-config)
    tools.yaml              # FastMCP tool server configuration (added by g tool-server)
    prompts.yaml            # Prompt registry (added by g prompt)
  server/
    service.py              # Registers agents, workflows, functions; can autostart tools
  client/
    run_workflow.py         # Example client for workflows
    run_agent.py            # Example client to run agents (added by generators)
  src/myapp/
    agents/                 # Long-lived, event-driven agents
    workflows/              # Orchestrators (typed, stepwise)
    functions/              # Stateless leaf operations
    common/
      retries.py            # Default retry policies
      settings.py           # Pydantic settings
      compat.py             # Pydantic v1/v2 compatibility helpers
      llm_router.py         # LLM router implementation (added by g llm-config)
      fastmcp_manager.py    # FastMCP manager/client (added by g tool-server)
      prompt_loader.py      # Versioned prompt loader & cache (added by g prompt)
    tools/                  # FastMCP tool servers (added by g tool-server)
      <name>_mcp.py
  prompts/
    <prompt_name>/
      v1.0.0.md             # Versioned prompt templates
  tests/                    # Unit & integration tests
  Makefile
  pyproject.toml
  README.md
```

Notes:
- The LLM and tools files are additive: they appear when you run the corresponding generators.
- `config/llm_router.yaml` supports direct providers or Kong gateway backends.
- Tool servers created by `restack g tool-server` include optional autostart via `config/tools.yaml`.

## LLM router (brief usage)

Generated router API:

```python
from myapp.common.llm_router import LLMRouter, LLMRequest

router = LLMRouter()
response = await router.chat(
    LLMRequest(messages=[{"role": "user", "content": "Hello"}], dry_run=True)
)

# Restack Gen — Scaffolding for Restack Agents

Restack Gen is a convention-over-configuration CLI for scaffolding Restack agents, workflows, functions, tool servers, LLM integrations, and configuration migrations. It produces runnable, testable, and observable code with sensible defaults for retries, timeouts, and structured logging.

## Key Features

- Rails-style scaffolding: `restack new`, `restack g agent`, `restack g workflow`, `restack g function`, `restack g pipeline`
- Full-featured `scaffold` generator for agents with LLM and tools integration
- Configuration migration system: `restack g migration`, `restack migrate`
- Prompt versioning and registry management
- LLM router and FastMCP tool integration
- Generated tests (unit and integration) and CI-friendly project layout
- Type-safe code using Pydantic models
- Operator grammar for composing pipelines (sequence, loop, conditional)
- Health checks and doctor commands for environment validation

## Installation

Install via pip (recommended using `uv` if available):

```powershell
uv pip install restack-gen
# or
pip install restack-gen
```

Verify installation:

```powershell
restack --help
```

## Quick Start

Create a new project and generate resources:

```powershell
restack new myapp
cd myapp

# Generate resources
restack g agent Onboarding
restack g workflow EmailCampaign
restack g function SendEmail
restack g tool-server Research
restack g llm-config --backend direct
restack g prompt AnalyzeResearch --version 1.0.0
restack g scaffold FullAgent
restack g migration AddPromptField --target prompts
```

Run checks and start the server:

```powershell
restack doctor
restack run:server
python client/run_workflow.py
```

Apply or rollback configuration migrations:

```powershell
restack migrate --target prompts
restack migrate --direction down --count 1
restack migrate --status
```

## v2.0 Project Layout

A project generated with v2.0 includes core scaffold plus optional LLM/tool/prompt/migration add-ons:

```
myapp/
  config/
    settings.yaml           # Project settings
    llm_router.yaml         # LLM provider router configuration (added by g llm-config)
    tools.yaml              # FastMCP tool server configuration (added by g tool-server)
    prompts.yaml            # Prompt registry (added by g prompt)
  migrations/
    20251028_120000_add_prompt_field.py  # Example migration (timestamped)
    .migration_state.json   # Migration state tracking
  server/
    service.py              # Registers agents, workflows, functions; can autostart tools
  client/
    run_workflow.py         # Example client for workflows
    run_agent.py            # Example client to run agents (added by generators)
  src/myapp/
    agents/                 # Long-lived, event-driven agents
    workflows/              # Orchestrators (typed, stepwise)
    functions/              # Stateless leaf operations
    common/
      retries.py            # Default retry policies
      settings.py           # Pydantic settings
      compat.py             # Pydantic v1/v2 compatibility helpers
      llm_router.py         # LLM router implementation (added by g llm-config)
      fastmcp_manager.py    # FastMCP manager/client (added by g tool-server)
      prompt_loader.py      # Versioned prompt loader & cache (added by g prompt)
    tools/                  # FastMCP tool servers (added by g tool-server)
      <name>_mcp.py
  prompts/
    <prompt_name>/
      v1.0.0.md             # Versioned prompt templates
  tests/                    # Unit & integration tests
  Makefile
  pyproject.toml
  README.md
```

Notes:
- LLM, tools, prompts, and migrations are additive: they appear when you run the corresponding generators.
- `config/llm_router.yaml` supports direct providers or Kong gateway backends.
- Tool servers created by `restack g tool-server` include optional autostart via `config/tools.yaml`.
- Migrations are tracked in the `migrations/` folder and managed via CLI.

## CLI Reference

- `restack new <app>` — Create a new Restack project
- `restack g agent <Name> [--with-llm] [--tools <ToolServer>]` — Generate an agent
- `restack g workflow <Name>` — Generate a workflow
- `restack g function <Name>` — Generate a function
- `restack g pipeline <Name> --operators "<Expr>"` — Generate a pipeline with operator expressions
- `restack g tool-server <Name>` — Generate a FastMCP tool server
- `restack g llm-config [--backend direct|kong]` — Generate LLM router config
- `restack g prompt <Name> --version <SemVer>` — Generate a versioned prompt
- `restack g scaffold <Name>` — Generate a full-featured agent scaffold
- `restack g migration <Name> --target <prompts|llm-router|tools>` — Generate a config migration
- `restack migrate [--target <...>] [--direction up|down] [--count N] [--status]` — Apply or rollback migrations
- `restack doctor [--verbose] [--check-tools]` — Run environment and config checks
- `restack run:server [--config <file>]` — Start the Restack service
- `restack console [--config <file>]` — Launch an interactive console

## LLM Router (Usage Example)

```python
from myapp.common.llm_router import LLMRouter, LLMRequest

router = LLMRouter()
response = await router.chat(
    LLMRequest(messages=[{"role": "user", "content": "Hello"}], dry_run=True)
)
# response.content, response.usage, response.metadata (cost/latency) available
```

- Use `RESTACK_LLM_DRY_RUN=1` or `LLMRequest(dry_run=True)` to estimate token usage and cost without calling providers.
- Pricing can be configured in `config/llm_router.yaml`.

## FastMCP Tools (Usage Example)

```python
from myapp.common.fastmcp_manager import FastMCPClient

async with FastMCPClient("research_tools") as client:
    result = await client.call_tool("web_search", {"query": "latest AI news"})
```

## Configuration Migrations (Usage Example)

```powershell
restack g migration AddPromptField --target prompts
restack migrate --target prompts
restack migrate --direction down --count 1
restack migrate --status
```

Migration files are timestamped and reversible, supporting safe CI/CD and multi-environment upgrades.

## Documentation

See the `docs/` folder for full guides:
- docs/quickstart.md
- docs/installation.md
- docs/cli-reference.md
- docs/llm-router.md
- docs/fastmcp-tools.md
- docs/prompt-versioning.md
- docs/migrations.md
- docs/troubleshooting.md

## Testing

Run tests with:

```powershell
make test
# or
python -m pytest
```

## Contributing

Please follow the repository CONTRIBUTING guidelines. Typical workflow:

```powershell
git clone <repo>
make setup
make fmt
make lint
make test
```

## License

Apache License 2.0 — see LICENSE for details.

## Acknowledgments

Built with:
- Typer - CLI framework
- Jinja2 - Template engine
- Pydantic - Data validation
- Restack - Agent orchestration engine

Questions? Open an issue or reach out on Discord.
