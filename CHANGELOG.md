# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
