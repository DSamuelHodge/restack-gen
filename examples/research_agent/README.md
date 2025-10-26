# Research Agent Example (LLM + Tools)

This example demonstrates a research workflow that combines:
- FastMCP tools (web_search) to gather context
- LLM routing to summarize results

It works offline by default via stub fallbacks, and seamlessly switches to real FastMCP + LLM Router if you generate them.

## Project Structure

```
research_agent/
├── README.md
├── pyproject.toml
├── Makefile
├── settings.yaml
├── client/
│   └── run_workflow.py
└── src/
    └── research_agent/
        ├── __init__.py
        ├── service.py
        ├── common/
        │   └── fallbacks.py         # Fake LLM & tool client for offline mode
        └── workflows/
            └── research_workflow.py
```

## Run (offline, no external APIs)

```bash
pip install -e .
make dev  # starts service
# in another terminal
python client/run_workflow.py
```

## Optional: Use real LLM Router + FastMCP tools

In a separate, generated project you’d normally run:

```bash
restack g llm-config               # creates config/llm_router.yaml and common/llm_router.py
restack g tool-server Research     # creates common/fastmcp_manager.py and tools server
```

To adapt this example to use those real components, add (or copy-in) the generated files into `src/research_agent/common/`:
- `llm_router.py` (router implementation)
- `fastmcp_manager.py` (FastMCP client + server manager)

When present, the example auto-detects and uses them; otherwise it falls back to stubs.

## What it does

- Calls `web_search` tool to fetch a few results for your query
- Asks the LLM to summarize the results
- Prints the summary to stdout

See also:
- LLM Router: ../../docs/llm-router.md
- FastMCP Tools: ../../docs/fastmcp-tools.md
- Doctor checks: ../../docs/troubleshooting.md
