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

Create a new project and generate resources:

```powershell
restack new myapp
cd myapp

# generate resources
restack g agent Onboarding
restack g workflow EmailCampaign
restack g function SendEmail
restack g tool-server Research
restack g llm-config --backend direct
restack g prompt AnalyzeResearch --version 1.0.0
```

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
# response.content, response.usage, response.metadata (cost/latency) available
```

- Use `RESTACK_LLM_DRY_RUN=1` or `LLMRequest(dry_run=True)` to estimate token usage and cost without calling providers.
- Pricing can be configured in `config/llm_router.yaml`.

## FastMCP tools (brief usage)

Start tool servers via the Restack service (autostart) or run standalone. Example client usage:

```python
from myapp.common.fastmcp_manager import FastMCPClient

async with FastMCPClient("research_tools") as client:
    result = await client.call_tool("web_search", {"query": "latest AI news"})
```

FastMCP client supports optional response caching and lifecycle management.

## Documentation

See the `docs/` folder for full guides:
- docs/quickstart.md
- docs/installation.md
- docs/cli-reference.md
- docs/llm-router.md
- docs/fastmcp-tools.md
- docs/prompt-versioning.md
- docs/troubleshooting.md
- docs/RELEASE.md
- docs/DECISIONS.md

## Testing

Run tests with:

```powershell
make test
# or
python -m pytest
```

Integration tests exercise the dynamic import patterns used by generated projects; ensure dependencies are installed for provider integrations.

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
