# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-10-25

### Added

#### LLM Router Foundation (PR #1)
- Prompt versioning system (PR #5):
  - prompts.yaml registry with versions/latest and resolution modes
  - PromptLoader with semver resolution and frontmatter parsing
  - CLI: `restack g prompt <Name> --version X.Y.Z`
- **CLI command**: `restack g llm-config --backend direct` generates router configuration
- **Automatic fallback**: Routes to next provider on timeout, 5xx, or rate limit
- **Circuit breaker**: Prevents cascading failures with 5-failure threshold and 60s cooldown
- **Environment variable substitution**: Config supports `${VAR}` and `${VAR:-default}` syntax
- **Structured logging**: Uses structlog for comprehensive request/response logging
- **Complete test coverage**: 9 new tests for config generation and router functionality

#### New Dependencies
- `httpx>=0.27.0` - Async HTTP client for provider calls
- `structlog>=24.1.0` - Structured logging support
- `respx>=0.21.0` - HTTP mocking for tests (dev dependency)

#### New Files
- `restack_gen/templates/llm_router.yaml.j2` - Configuration template
- `restack_gen/templates/llm_router.py.j2` - Router implementation template
- `tests/test_llm_router.py` - Comprehensive test suite
- `docs/llm-router.md` - Complete documentation and usage guide

### Changed
- Version bumped to 2.0.0
- Updated README with v2.0 features
- Enhanced PROJECT_STATUS.md with PR tracking

### Coming Soon (v2.0 Roadmap)
- **PR #3**: FastMCP tool server scaffolding
- **PR #4**: Auto-registration of tools in agents
- **PR #5**: Prompt versioning system
- **PR #6-12**: Advanced features (caching, streaming, batch processing, etc.)

#### Kong AI Gateway Integration (PR #2)
- **Kong backend support**: Route LLM requests through Kong AI Gateway
- **AI rate limiting**: Token-based rate limiting with configurable thresholds
- **Cost tracking**: Automatic token usage and cost metrics in response metadata
- **Content safety**: Optional Azure content filters integration
- **Gateway-level features**: Latency tracking, rate limit monitoring
- **Enhanced metadata**: Response includes `latency_ms`, `cost_usd`, `rate_limit_remaining`
- **Kong-specific tests**: 8 new tests for Kong routing, rate limiting, and cost tracking

#### FastMCP Tool Server Scaffolding (PR #3)
- **Tool server generation**: `restack g tool-server Research` creates FastMCP tool server
- **Sample tools included**: web_search, extract_urls, calculate tools in generated servers
- **YAML configuration**: Automatic `config/tools.yaml` generation with server settings
- **Health checks**: Built-in health check methods for monitoring server status
- **Transport support**: stdio (local) and sse (HTTP) transport protocols
- **Multiple servers**: Support for multiple tool servers in single project
- **Complete test suite**: 14 tests covering generation, content, name conversion, errors

#### New Files (PR #3)
- `restack_gen/templates/tool_server.py.j2` - FastMCP tool server template
- `restack_gen/templates/tools.yaml.j2` - Tool server configuration template
- `tests/test_tool_server.py` - Test suite for tool server generation
- `docs/fastmcp-tools.md` - Comprehensive FastMCP tool server guide

#### FastMCP Server Manager (PR #4)
- **Lifecycle management**: FastMCPServerManager class manages all tool servers
- **Autostart support**: Tool servers start automatically with Restack service when `autostart: true`
- **Tool calling API**: FastMCPClient provides clean interface for agents to call tools
- **Health monitoring**: `restack doctor --check-tools` validates server health and configuration
- **Server registry**: Track running servers, start/stop individual or all servers
- **Graceful shutdown**: Automatic cleanup when Restack service stops
- **Error handling**: Robust error handling for startup failures and unhealthy servers
- **Complete test suite**: 18 tests covering manager, autostart, health checks, doctor integration

#### New Files (PR #4)
- `restack_gen/templates/fastmcp_manager.py.j2` - Server manager and client (460 lines)
- `tests/test_fastmcp_manager.py` - Comprehensive test suite (18 tests)

#### Updated Files (PR #4)
- `restack_gen/templates/service.py.j2` - Integrated tool server autostart
- `restack_gen/doctor.py` - Added check_tools() function (145 lines)
- `restack_gen/cli.py` - Added --check-tools flag to doctor command
- `restack_gen/generator.py` - Automatic manager generation on first tool server
- `docs/fastmcp-tools.md` - Added 350+ lines covering manager usage, autostart, tool calling, health monitoring

#### New Features
- `restack g llm-config --backend kong` generates Kong-ready configuration
- Automatic feature enablement when Kong backend selected
- Support for Kong routes: `/ai/openai` and `/ai/anthropic`
- Content safety filter detection and error handling

## [1.0.0] - 2025-10-24

### Added

#### Core Features
- **Project scaffolding**: `restack new <name>` command creates complete project structure with:
  - Server setup with service registration
  - Client examples for workflow execution
  - Configuration management (YAML + environment variables)
  - Common utilities (retries, settings, compatibility layer)
  - Test structure with pytest configuration
  
- **Resource generation**: Rails-style generators for:
  - **Agents** (`restack g agent <Name>`): Long-lived, event-driven components
  - **Workflows** (`restack g workflow <Name>`): Orchestrators with typed steps
  - **Functions** (`restack g function <Name>`): Stateless leaf operations
  - Each generator creates implementation, tests, and updates service.py automatically
  
- **Pipeline generation**: `restack g pipeline <Name> --operators "<expression>"` creates workflow orchestrators from operator expressions:
  - Sequential operator (`→`): Chain steps in order
  - Parallel operator (`⇄`): Execute steps concurrently
  - Conditional operator (`→?`): Branch based on conditions
  - Automatic import generation and service registration
  
- **Developer tools**:
  - `restack doctor` command: Validates project health, dependencies, Python version, git status
  - `restack run:server` command: Starts Restack service with environment loading and graceful shutdown
  
#### Code Quality Features
- **AST-based code modification**: Safe, idempotent updates to service.py
- **@generated markers**: Prevent duplicate registrations, support force regeneration with `--force`
- **Type safety**: Full type annotations, Pydantic validation
- **Pydantic v1/v2 compatibility**: Automatic detection and compatibility layer

#### Validation & Analysis
- Pipeline validation with cycle detection
- Unreachable node detection
- Dependency graph analysis
- Execution order computation
- Complexity metrics (depth, width, parallel sections)

#### Templates
- 15+ Jinja2 templates for all resource types
- Configurable retry policies with exponential backoff
- Structured logging with correlation IDs
- Test templates with mocking and async support

### Infrastructure
- **Build system**: Hatchling-based package configuration
- **CI/CD**: GitHub Actions workflow for testing and linting
- **Code quality**: Ruff, Black, MyPy, pre-commit hooks
- **Testing**: pytest with coverage reporting (80%+ coverage)
- **Documentation**: Comprehensive guides for pipelines, CLI usage, and troubleshooting

### Dependencies
- Python 3.11+ required
- Core: typer, jinja2, pydantic, pyyaml, rich
- Development: pytest, pytest-asyncio, pytest-cov, ruff, black, mypy

### Examples
- Data pipeline example: Sequential data fetching, processing, and storage
- Email pipeline example: Parallel fetching with conditional processing

### Statistics
- **236 tests** passing with **80.92% coverage**
- **~3,700 lines** of production code
- **~3,400 lines** of test code
- **~1,500 lines** of template code

## [Unreleased]

### Planned
- Hot-reload support for development mode
- Additional pipeline operators
- Enhanced observability integrations
- Performance optimizations

---

## Release History

### Version Naming Convention
- **Major (X.0.0)**: Breaking changes, major feature additions
- **Minor (1.X.0)**: New features, backwards compatible
- **Patch (1.0.X)**: Bug fixes, documentation updates

### Support
For issues, feature requests, or questions:
- GitHub Issues: https://github.com/restackio/restack-gen/issues
- Documentation: https://github.com/restackio/restack-gen/tree/main/docs
