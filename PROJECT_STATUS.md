# 📋 Project Status

This document tracks the implementation status of **restack-gen v2.0.0**, the Rails-style scaffolding CLI for Restack agents with LLM, Tools, and Prompt capabilities.

---

## 🎯 Current Version: 2.0.0

### Recently Completed: PR #4 - FastMCP Server Manager

**Status:** ✅ Complete  
**Date:** January 2025

#### Implemented Features
- ✅ FastMCPServerManager class for lifecycle management
- ✅ Autostart support - servers start with Restack service
- ✅ FastMCPClient for tool calling from agents
- ✅ Health monitoring via `restack doctor --check-tools`
- ✅ Server registry for tracking running servers
- ✅ Graceful shutdown on service termination
- ✅ Robust error handling for startup failures
- ✅ Full test coverage (18 tests, all passing)

#### Files Modified
- `restack_gen/templates/fastmcp_manager.py.j2` - Manager and client template (460 lines)
- `restack_gen/templates/service.py.j2` - Integrated tool server autostart (30 lines added)
- `restack_gen/doctor.py` - Added check_tools() function (145 lines)
- `restack_gen/cli.py` - Added --check-tools flag (8 lines modified)
- `restack_gen/generator.py` - Automatic manager generation (25 lines added)
- `tests/test_fastmcp_manager.py` - Complete test suite (323 lines, 18 tests)
- `docs/fastmcp-tools.md` - Added manager documentation (350+ lines)

#### Test Results
- All 18 FastMCP manager tests passing
- Test classes:
  - TestFastMCPManagerGeneration: 3 tests (file generation, no regeneration, method validation)
  - TestFastMCPManagerFunctionality: 8 tests (config loading, health checks, server management, singleton)
  - TestDoctorToolsCheck: 4 tests (with/without config, invalid YAML, verbose mode)
  - TestServiceIntegration: 3 tests (imports, startup, shutdown)
- Coverage: Manager lifecycle, autostart, tool calling, health monitoring, doctor integration

#### Generated Components
- **Manager File**: `src/<project>/common/fastmcp_manager.py`
  - FastMCPServerManager class: Configuration loading, server registry, start/stop methods
  - FastMCPClient class: Async context manager for tool calling
  - Global helpers: start_tool_servers(), stop_tool_servers(), get_manager()
  - ServerConfig dataclass for typed configuration
- **Updated Service**: `src/<project>/service.py`
  - Conditional import of fastmcp_manager
  - Autostart tool servers before starting Restack service
  - Graceful shutdown in finally block
- **Doctor Integration**: Health checks for tool servers
  - Validates tools.yaml syntax and FastMCP installation
  - Verifies module imports for all configured servers
  - Performs async health checks on running servers
  - Detailed verbose output with server information

#### CLI Usage
```bash
# Generate first tool server (creates manager automatically)
restack g tool-server Research

# Check tool server health
restack doctor --check-tools

# Check with verbose output
restack doctor --check-tools --verbose

# Start Restack service (autostart tool servers)
restack up
```

#### API Usage
```python
# Use FastMCPClient in agents
from myproject.common.fastmcp_manager import FastMCPClient

async def my_workflow(ctx):
    async with FastMCPClient("research_tools") as client:
        result = await client.call_tool("web_search", {"query": "AI"})
        return result

# Programmatic health checks
from myproject.common.fastmcp_manager import FastMCPServerManager

async def check_health():
    manager = FastMCPServerManager()
    status = await manager.health_check("research_tools")
    return status  # {"status": "healthy", "details": {...}}
```

---

### Recently Completed: PR #3 - FastMCP Tool Server Scaffolding

**Status:** ✅ Complete  
**Date:** January 2025

#### Implemented Features
- ✅ Tool server generation via `restack g tool-server <Name>`
- ✅ FastMCP 2.0 server template with 3 sample tools
- ✅ YAML configuration (tools.yaml) with server settings
- ✅ Health check and server lifecycle methods
- ✅ Support for stdio and sse transport protocols
- ✅ Multiple tool servers per project
- ✅ Name format conversion (PascalCase/snake_case)
- ✅ Full test coverage (14 tests, all passing)

#### Files Modified
- `restack_gen/generator.py` - Added `generate_tool_server()` function (95 lines)
- `restack_gen/cli.py` - Added tool-server command to generate (11 lines modified)
- `restack_gen/templates/tool_server.py.j2` - FastMCP server template (177 lines)
- `restack_gen/templates/tools.yaml.j2` - Configuration template (45 lines)
- `tests/test_tool_server.py` - Complete test suite (170 lines, 14 tests)
- `docs/fastmcp-tools.md` - Comprehensive documentation (600+ lines)

#### Test Results
- All 14 tool server tests passing
- Coverage: File creation, content validation, name conversion, errors, force flag
- Validation: Python syntax, health checks, run methods, multiple servers

#### Generated Components
- **Tool Server File**: `src/<project>/tools/<name>_mcp.py`
  - FastMCP initialization
  - 3 sample tools: web_search, extract_urls, calculate
  - Server class with run() and health_check() methods
  - Direct execution support via __main__
- **Configuration File**: `config/tools.yaml`
  - Server list with name, module, class, transport
  - Global settings for timeout, retry, logging
  - Environment variable placeholders
  - Health check configuration

#### CLI Usage
```bash
# Generate tool server
restack g tool-server Research

# Supports both naming conventions
restack g tool-server data_analysis  # Creates DataAnalysisToolServer
restack g tool-server DataAnalysis   # Creates DataAnalysisToolServer

# Force overwrite
restack g tool-server Research --force
```

---

### Recently Completed: PR #2 - Kong AI Gateway Integration

**Status:** ✅ Complete  
**Date:** January 2025

#### Implemented Features
- ✅ Kong backend support in LLMRouter
- ✅ AI rate limiting detection and fallback
- ✅ Cost tracking with metadata extraction
- ✅ Content safety filter integration
- ✅ Kong-specific error handling (429, 400, 5xx)
- ✅ Response metadata (latency, cost, rate limit remaining)
- ✅ Automatic feature enablement for Kong backend
- ✅ Full test coverage (8 new Kong tests)

#### Files Modified
- `restack_gen/templates/llm_router.py.j2` - Added `_call_kong()` method (170+ lines)
- `restack_gen/templates/llm_router.py.j2` - Updated LLMResponse with metadata field
- `restack_gen/templates/llm_router.yaml.j2` - Dynamic feature enablement based on backend
- `tests/test_llm_router.py` - Added TestKongBackend class with 8 tests
- `docs/llm-router.md` - Added Kong setup guide, features, and examples

#### Test Results
- All 17 tests passing (9 PR #1 + 8 PR #2)
- Kong backend: 100% test coverage
- CLI generation: Verified with both backends

#### Kong Features Enabled
- **AI Rate Limiting**: Token-based with configurable window (default: 100k tokens/minute)
- **Cost Tracking**: Prometheus export, captures token usage and USD cost
- **Content Safety**: Optional Azure filters for violence, hate, sexual, self-harm
- **Metadata Tracking**: Latency, cost, rate limit remaining in every response

---

### Recently Completed: PR #1 - LLM Router Foundation

**Status:** ✅ Complete  
**Date:** January 2025

#### Implemented Features
- ✅ Multi-provider LLM routing (OpenAI, Anthropic)
- ✅ Direct provider calls with httpx
- ✅ Circuit breaker pattern (5 failure threshold, 60s cooldown)
- ✅ Automatic fallback logic (timeout, 5xx, rate_limit)
- ✅ YAML configuration with environment variable substitution
- ✅ CLI command: `restack g llm-config --backend direct`
- ✅ Structured logging with structlog
- ✅ Full test coverage (9 tests)

#### Files Added/Modified
- `pyproject.toml` - Updated to v2.0.0, added httpx and structlog dependencies
- `restack_gen/templates/llm_router.yaml.j2` - Configuration template
- `restack_gen/templates/llm_router.py.j2` - Router implementation template
- `restack_gen/generator.py` - Added generate_llm_config() function
- `restack_gen/cli.py` - Added llm-config resource type support
- `tests/test_llm_router.py` - Complete test suite

#### Test Results
- All 245 tests passing (236 existing + 9 new)
- Test coverage: 80.29% overall
- LLM router tests: 100% passing

---

## 🚀 v1.0.0 - Core Scaffolding (Completed)

### ✅ Completed Tasks

### 1. Specification Refinement
- ✅ Updated `specs/product_specs.md` with all architectural decisions
- ✅ Updated `specs/plan.md` with implementation details
- ✅ Moved `specs/decisions.md` to `docs/DECISIONS.md`
- ✅ Added v2.0.0 specification in `specs/specs.md`

### 2. Repository Structure
```
restack-agent-generator/
├── .github/
│   └── workflows/
│       └── ci.yml                 # GitHub Actions CI
├── docs/
│   └── DECISIONS.md               # Architecture decisions log
├── examples/                      # Example projects (to be populated)
├── restack_gen/                   # Main package
│   ├── __init__.py
│   ├── cli.py                     # Typer CLI commands
│   ├── compat.py                  # Pydantic v1/v2 compatibility
│   └── templates/                 # Jinja2 templates (to be populated)
├── specs/
│   ├── clarity.md                 # Q&A clarifications
│   ├── plan.md                    # Work plan
│   └── product_specs.md           # Product specifications
├── tests/
│   ├── conftest.py                # Pytest fixtures
│   └── test_cli.py                # CLI tests
├── .gitignore
├── .pre-commit-config.yaml        # Pre-commit hooks
├── LICENSE                        # MIT License
├── Makefile                       # Development tasks
├── pyproject.toml                 # Package configuration
└── README.md                      # Project documentation
```

### 3. Core Files Created

#### Configuration Files
- ✅ `pyproject.toml` - Package metadata, dependencies, tool configs
- ✅ `.pre-commit-config.yaml` - Code quality hooks (ruff, black, mypy)
- ✅ `.github/workflows/ci.yml` - CI pipeline (lint, typecheck, test)
- ✅ `Makefile` - Common development tasks
- ✅ `.gitignore` - Ignore patterns

#### Python Package
- ✅ `restack_gen/__init__.py` - Package initialization
- ✅ `restack_gen/cli.py` - CLI commands (placeholders)
- ✅ `restack_gen/compat.py` - Pydantic v1/v2 compatibility shim

#### Tests
- ✅ `tests/conftest.py` - Pytest fixtures
- ✅ `tests/test_cli.py` - CLI smoke tests

#### Documentation
- ✅ `README.md` - Comprehensive user documentation
- ✅ `LICENSE` - MIT License
- ✅ `docs/DECISIONS.md` - Architecture decisions

---

## 🎯 Current Status

### ✅ Passing Tests
All 6 initial CLI smoke tests pass:
- `test_version` - Version flag works
- `test_help` - Help output displays
- `test_new_command` - New command stub works
- `test_generate_command` - Generate command stub works
- `test_doctor_command` - Doctor command stub works
- `test_run_server_command` - Run server command stub works

### ✅ Development Environment
- Python 3.11+ required (tested with 3.14)
- All dependencies installed successfully
- Package installable via `pip install -e ".[dev]"`
- CLI accessible via `python -m restack_gen.cli`

---

## 🚀 Next Steps (Following PR Plan)

### PR 1: Repo Bootstrap & Tooling ✅ COMPLETE
- [x] Skeleton repo structure
- [x] `pyproject.toml`, `Makefile`, CI, pre-commit
- [x] Empty `restack_gen/` package
- [x] CI green, `make fmt/lint/test` works

### PR 2: Templates v1 (Static) 🔜 NEXT
Create Jinja2 templates for:
- [ ] Agent template (with event enum)
- [ ] Workflow template (with I/O models)
- [ ] Function template
- [ ] Pipeline orchestrator template
- [ ] Service template
- [ ] Client samples
- [ ] Common modules (retries, settings, compat)
- [ ] Tests templates
- [ ] Project boilerplate files

### PR 3: CLI Core: `new` 🔜
- [ ] Implement `restack new <app>` command
- [ ] Render templates to disk
- [ ] Create directory structure
- [ ] Generate initial project files

### PR 4-7: Generator Commands 🔜
- [ ] `restack g agent`
- [ ] `restack g workflow`
- [ ] `restack g function`
- [ ] `restack g pipeline` (with operator parsing)
- [ ] AST-based service.py registration

### PR 8-12: Advanced Features 🔜
- [ ] Continue-as-new support
- [ ] Doctor checks (PR 9)
- [ ] Observability/logging
- [ ] Docs and examples
- [ ] Polish and safeguards

---

## 📊 Development Commands

```bash
# Setup (first time)
make setup

# Format code
make fmt

# Lint
make lint

# Type check
make typecheck

# Run tests
make test

# Run tests with coverage
make test-cov

# Clean artifacts
make clean
```

---

## 🔧 Key Technologies

| Tool | Purpose | Version |
|------|---------|---------|
| Python | Runtime | ≥3.11 |
| Typer | CLI framework | ≥0.12.0 |
| Jinja2 | Template engine | ≥3.1.0 |
| Pydantic | Data validation | ≥2.7.0 |
| Pytest | Testing framework | ≥8.0.0 |
| Ruff | Linting | ≥0.4.0 |
| Black | Formatting | ≥24.0.0 |
| Mypy | Type checking | ≥1.9.0 |

---

## 📝 Important Decisions

See `docs/DECISIONS.md` for full details. Key decisions:

- **Python 3.11+** for modern async features
- **Pydantic v2** with compatibility shim for v1
- **Standalone CLI** distribution via `uv pip install restack-gen`
- **AST manipulation** for safe service registration
- **Operator grammar** for pipeline chaining (`→`, `⇄`, `→?`)
- **Settings precedence**: CLI > ENV > YAML > defaults
- **Generated file headers** with timestamp + command
- **Comprehensive doctor checks** (permissions, versions, git status)

---

## 🎨 CLI Preview

```bash
# Create new project
restack new myapp

# Generate resources
restack g agent Onboarding
restack g workflow EmailCampaign
restack g function SendEmail

# Generate pipeline with operators
restack g pipeline BlogPipeline \
  --operators "IDEATE ⇄ RESEARCH → PLAN → OUTLINE → DRAFT ⇄ REVIEW → POLISH → PUBLISH"

# Run server
restack run:server

# Health check
restack doctor
```

---

## ✨ Generated Project Structure

```
myapp/
├── config/
│   └── settings.yaml
├── server/
│   └── service.py              # Auto-registers resources
├── client/
│   └── run_workflow.py
├── src/myapp/
│   ├── agents/
│   ├── workflows/
│   ├── functions/
│   └── common/
│       ├── retries.py          # Default policies
│       ├── settings.py         # Pydantic settings
│       └── compat.py           # Pydantic shim
└── tests/
    ├── test_agents/
    ├── test_workflows/
    └── test_pipeline/
```

---

## 📚 Documentation Links

- [Product Specs](specs/product_specs.md) - Detailed feature specifications
- [Work Plan](specs/plan.md) - Implementation roadmap with PR sequence
- [Decisions Log](docs/DECISIONS.md) - Architecture decisions and rationales
- [README](README.md) - User-facing documentation

---

## 🎯 Acceptance Criteria (v1.0)

Based on product spec, v1.0 is complete when:

1. ✅ `restack new demo` produces a repo that runs with no edits
2. ⏳ `restack g agent/workflow/function` creates files with auto-registration
3. ⏳ `restack g pipeline` with operators generates orchestrator + tokens
4. ⏳ All child calls include DEFAULT_RETRY, TIMEOUT, HEARTBEAT
5. ⏳ Integration test runs end-to-end with stubs
6. ⏳ `restack doctor` detects and prints actionable errors

**Current Progress**: 1/6 (16%)

---

## 🤝 Contributing

The project follows the PR plan in `specs/plan.md`. Each PR should:
1. Focus on one module/feature
2. Include tests (golden snapshots for templates)
3. Pass CI (lint, typecheck, tests)
4. Update docs if needed

---

## 📞 Support

- Open an issue on GitHub
- Check documentation in `docs/` and `specs/`
- Review `DECISIONS.md` for design rationales

---

**Status**: ✅ **PR 1 Complete - Ready for PR 2 (Templates)**

Last updated: 2025-10-24
