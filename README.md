# 🚀 Restack Gen — Rails for Restack Agents

**Convention-over-configuration scaffolding CLI** for building Restack agents, workflows, and pipelines with **fault-tolerance baked in** and an **operator grammar** for chaining steps.

One command generates runnable, testable, observable code that registers itself with the Restack engine.

---

## ✨ Features

- **🏗️ Rails-style scaffolding**: `restack new`, `restack g agent`, `restack g workflow`, `restack g pipeline`
- **🔄 Omakase defaults**: Retries, timeouts, heartbeats, logging, typing, tests—all configured out of the box
- **📝 Operator grammar**: Chain workflows with `→` (sequence), `⇄` (loop), `→?` (conditional)
- **🎯 Type-safe**: Pydantic models for inputs/outputs, full type checking
- **🧪 Test-ready**: Unit and integration tests generated automatically
- **🔍 Observable**: Structured logging with correlation IDs
- **⚙️ Configurable**: CLI flags, environment variables, and YAML settings with clear precedence

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
```

### 3. Generate a pipeline with operator grammar

```bash
restack g pipeline BlogPipeline \
  --operators "IDEATE ⇄ RESEARCH → PLAN → OUTLINE → DRAFT ⇄ REVIEW → POLISH → PUBLISH → PROMOTE →? REPURPOSE" \
  --style subworkflows
```

**Operators:**
- `→` : Sequential execution (A then B)
- `⇄` : Refinement loop (iterate between A and B)
- `→?` : Conditional step (run B only if condition met)

### 4. Run the server

```bash
# Check everything is configured correctly
restack doctor

# Start the server (registers all resources with Restack engine)
restack run:server
```

### 5. Trigger workflows

```bash
# Use the generated client
python client/run_workflow.py
```

---

## 📖 Documentation

- **[📋 Decisions Log](docs/DECISIONS.md)** - Architecture decisions and rationales
- **[📝 Product Specs](specs/product_specs.md)** - Detailed feature specifications
- **[🗺️ Work Plan](specs/plan.md)** - Implementation roadmap

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

MIT License - see [LICENSE](LICENSE) for details.

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
