# Rails for Restack Agents — Product Spec (v1)

## 0) Executive summary

Build a **Rails-style scaffolding toolchain** for Restack that makes it trivial to create **agents, workflows, and functions** with a clean **client/server** split, opinionated defaults, retries/fault-tolerance baked in, and an **operator grammar** for chaining pipelines. One command should generate runnable, testable, observable code that registers itself with the Restack engine.

---

## 1) Goals & Non-Goals

**Goals**

* **Convention over configuration** scaffolding for Restack: consistent repo layout, code templates, and wiring.
* **Omakase defaults**: retries, timeouts, heartbeats, logging, typing, tests.
* **Operator grammar → codegen** for workflow chaining.
* **Majestic monolith** first: single service process registers everything; easy later extraction.
* **DX speed**: `restack new`, `restack g <resource>`, `restack run:server`, `restack doctor`.

**Non-Goals (v1)**

* No GUI pipeline builder (CLI only).
* No multi-repo orchestration.
* No vendor-specific integrations beyond stubs (email, LLM, etc. as examples).
* No background monitoring service; rely on Restack engine/UI and logs.

---

## 2) Personas

* **App/ML engineer:** builds agentic automations & pipelines.
* **Infra/Platform engineer:** cares about reliability, observability, CI.
* **New team member:** must grok the project in minutes.

---

## 3) Architecture overview

```
repo/
  server/                 # registers with Restack engine (service process)
  client/                 # SDK scripts to schedule/trigger things
  src/<app>/
    agents/               # long-lived, event-driven
    workflows/            # orchestrators (typed, stepwise)
    functions/            # stateless leaf operations
    common/               # retry policies, utils
  config/                 # env/config (YAML)
  tests/                  # unit & integration
  restack_gen/            # the generator (CLI + templates) [optional mono-repo layout]
```

* **Server**: runs `service.py` that registers agents/workflows/functions (one task queue by default).
* **Client**: provides runnable examples for starting workflows, scheduling agents, sending events.
* **App**: all business logic under `src/<app>/…`.

---

## 4) CLI & Developer Experience

### 4.1 Commands

| Command                                                               | Description                                                            |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `restack new <app>`                                                   | Create new app with omakase layout & config                            |
| `restack g agent <Name>`                                              | Generate agent (`@agent.defn`, events, tests) + auto-register          |
| `restack g workflow <Name>`                                           | Generate workflow (`@workflow.defn`, typed I/O, tests) + auto-register |
| `restack g function <Name>`                                           | Generate function + test + auto-register                               |
| `restack g pipeline <Name> --operators "<expr>" [--style subworkflows\|functions]` | Parse operator grammar and emit orchestrator + tokens |
| `restack run:server`                                                  | Start server/service.py (assumes engine is up)                         |
| `restack doctor`                                                      | Env checks (engine, imports, config, permissions, git status)          |

### 4.2 Flags (common)

* `--retry.max_attempts`, `--retry.initial`, `--retry.backoff`, `--timeout`, `--heartbeat`
* `--task-queue` (default: `restack`)
* `--omit-tests` (default: false)
* `--force` (overwrite existing files)
* `--dry-run[=minimal|diff]` (preview without writing)
* `--models external|split` (model placement strategy)
* `--map TOKEN:CustomName` (override token-to-class mappings)
* `--cond STEP:condition_fn` (custom conditional logic)

---

## 5) Operator grammar & codegen

### 5.1 Grammar (v1)

* **Tokens**: `WORD` (step names, uppercase or CamelCase).
* **Operators**:

  * `A → B` : strict sequence
  * `A ⇄ B` : two-node refinement loop
  * `A →? B` : conditional sequence
  * *(optional v1.1)* `A ⊕ {B, C, D}` : parallel fan-out
* **Example**:
  `IDEATE ⇄ RESEARCH → PLAN → OUTLINE → DRAFT ⇄ REVIEW → POLISH → PUBLISH → PROMOTE →? REPURPOSE`

### 5.2 IR (Intermediate Representation)

* `nodes: Set[Step]`
* `edges: List[{from, to, type: seq|loop|cond|fanout}]`
* Validation rules: no orphan nodes, loops are 2-node cycles, at least one sink.

### 5.3 Codegen styles

* **subworkflows**: each token → `@workflow.defn` with `In/Out` models; orchestrator uses `child_execute(...)`.
* **functions**: each token → plain function with typed input; orchestrator uses `workflow.step(...)`.

*(Both styles attach the same default retry/timeout policies.)*

---

## 6) Reliability profile (fault-tolerance baked in)

### 6.1 Defaults (generated in `src/<app>/common/retries.py`)

* `DEFAULT_RETRY`: exponential backoff (e.g., start 5s, backoff 2.0, max interval 2m, attempts 6).
* `DEFAULT_STEP_TIMEOUT`: 2m.
* `DEFAULT_HEARTBEAT`: 30s.

### 6.2 Application

* Every **child_execute / step** call sets:

  * `retry_policy=DEFAULT_RETRY`
  * `start_to_close_timeout=DEFAULT_STEP_TIMEOUT`
  * `heartbeat_timeout=DEFAULT_HEARTBEAT`
* Per-step overrides via CLI flags or inline in templates.

### 6.3 Long-run durability

* **continue-as-new** insertion points for very long pipelines (post-publish or after N steps).
* Agents: use `should_continue_as_new()` in template loops.

---

## 7) Templates (Jinja) — generated files

### 7.1 Agent template

* `@agent.defn`, `@agent.run`, sample `@agent.event("end")` + `condition()` usage.
* Includes example `agent.step(...)` to a function with policies applied.
* Docstring with role and TODO markers.

### 7.2 Workflow template

* `@workflow.defn` with `@workflow.run(self, input: InModel) -> OutModel`.
* `In/Out` Pydantic models with comments for fields.
* Policies imported from `common.retries`.

### 7.3 Function template

* Small typed function (dataclass or Pydantic input).
* Pure side-effect stub and return.

### 7.4 Pipeline (operator) orchestrator

* Emits sequential awaits (`→`), refinement loops (`⇄`), conditional branches (`→?`).
* Imports all generated subworkflows/functions.
* Returns typed output model aggregating downstream results.

### 7.5 Service & Client

* `server/service.py`: registers lists of agents/workflows/functions on a task queue.
* `client/schedule_agent.py`, `client/run_workflow.py`: runnable samples.

### 7.6 Config & Tooling

* `config/settings.yaml` (+ `.env.example`).
* `pyproject.toml`: deps (`pydantic`, `typer`, `jinja2`, `pytest`, `rich`, linters).
* `Makefile`: `setup`, `fmt`, `lint`, `test`, `run`.
* `pre-commit` (ruff/black, etc).

### 7.7 Tests

* Unit tests per generated resource (smoke tests).
* One integration test for pipeline orchestration validating sequence, loop termination, conditional branch, and that retries are attached (assert call options).

---

## 8) File layout (generated)

```
<app>/
  pyproject.toml
  .env.example
  config/
    settings.yaml
  server/
    service.py
  client/
    schedule_agent.py
    run_workflow.py
  src/<app>/
    __init__.py
    common/
      __init__.py
      retries.py
    agents/
      __init__.py
      <snake>.py
    workflows/
      __init__.py
      <snake>.py
    functions/
      __init__.py
      <snake>.py
  tests/
    test_agents/
      test_<snake>.py
    test_workflows/
      test_<snake>.py
    test_pipeline/
      test_<pipeline>.py
  restack_gen/                 # if shipped mono-repo; otherwise external package
    cli.py
    templates/*.j2
```

---

## 9) Server registration contract

**`server/service.py`** (shape):

```python
from restack_ai.client import Restack
from src.<app>.agents import *
from src.<app>.workflows import *
from src.<app>.functions import *
import asyncio

async def main():
    client = Restack()
    await client.start_service(
        agents=[...],
        workflows=[...],
        functions=[...],
        task_queue="restack",
    )

if __name__ == "__main__":
    asyncio.run(main())
```

**Generator** must:

* Append new classes/functions to the lists.
* Add imports safely (idempotent regex or `ast` edit).

---

## 10) Client usage contract

* **Schedule agent**: `await client.schedule_agent("AgentName", input?)`
* **Send event**: `await client.send_event(run_id, "event_name", payload)`
* **Start workflow**: `await client.start_workflow("WorkflowName", InputModel(...))`

*(Names must match generated class decorators; generator keeps them consistent.)*

---

## 11) `restack doctor` checks

* Python version (3.11+) and package imports (`restack_ai`, `pydantic>=2.7.0`, etc.)
* Package version compatibility warnings
* Engine connectivity (configurable base URL/host)
* Confirms `service.py` can import all registrations
* Reports missing `__init__.py`, bad names, duplicate registrations
* File system permissions (write access to project directories)
* Git repository status (warns on uncommitted changes before generation)
* Example output:
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

## 12) Observability

* Structured logging calls in templates (`log.info/debug`).
* Emit correlation IDs (run id, child run id) on each step call.
* Optional: add a `LoggingMiddleware` template pattern to centralize context injection.

---

## 13) Security & Config

* `.env.example` with redacted secrets.
* No secrets committed; load via environment in `service.py`.
* Optional per-environment config: `settings.dev.yaml`, `settings.prod.yaml` with env overrides.

---

## 14) Performance & Scale considerations

* Encourage **subworkflow** style for long steps (isolated retries & observability).
* Document fan-out pattern (v1.1) with rate-limit knobs.
* Provide `continue-as-new` hooks in long orchestrators.
* One task queue by default; support `--task-queue` per service.

---

## 15) Acceptance criteria

1. **`restack new demo`** produces a repo that:

   * `make setup && restack run:server` runs with no edits.
   * `pytest` passes generated tests.

2. **`restack g agent Hello`**, **`restack g workflow HelloFlow`**, **`restack g function SendEmail`**:

   * Files created with correct names.
   * `server/service.py` auto-updated and imports valid.

3. **`restack g pipeline BlogPipeline --operators "IDEATE ⇄ RESEARCH → PLAN → OUTLINE → DRAFT ⇄ REVIEW → POLISH → PUBLISH → PROMOTE →? REPURPOSE" --style subworkflows`**

   * Orchestrator and tokens generated.
   * Orchestrator shows **seq**, **loop**, **cond** patterns.
   * All child calls include **DEFAULT_RETRY**, **DEFAULT_STEP_TIMEOUT**, **DEFAULT_HEARTBEAT**.
   * Integration test runs end-to-end with stubs.

4. **`restack doctor`**:

   * Detects and prints actionable errors when engine unreachable or imports fail.

---

## 16) Implementation plan (high-level)

1. **CLI foundation** (Typer)

   * Command skeletons, path helpers, renderer.

2. **Templates**

   * Agents/workflows/functions/pipeline orchestrator, retries, service, client, tests.

3. **Operator parser → IR → codegen**

   * Tokenizer (regex), parser (simple state machine), IR validator.
   * Renderer for subworkflow/function styles.

4. **Service auto-registration**

   * AST-safe insert of imports and list entries.
   * Idempotency checks.

5. **Doctor**

   * Connectivity test, import validation, config checks.

6. **Docs & Examples**

   * README with quickstart, examples, and operator cheatsheet.

---

## 17) Final decisions (resolved)

* **Python version**: 3.11+ (modern async, stable ecosystem)
* **Pydantic**: v2 (with compat shim in `restack_gen/compat.py` copied to generated projects)
* **Distribution**: Standalone CLI via `uv pip install restack-gen` (not vendored into projects)
* **Header marker**: All generated files include:
  ```python
  # @generated by restack-gen v1.0.0 (2025-10-24T14:05:12Z)
  # command: restack g workflow BlogWorkflow --task-queue restack
  # do not edit this header; use --force to overwrite
  ```
* **AST fallback**: On failure, print error + snippet + write `.patch` file
* **Settings precedence**: Centralized in Settings loader (CLI > ENV > YAML > defaults)
* **Agent event enums**: Singular naming (`OnboardingEvent`)
* **Loop limits**: Configured in `settings.yaml` under `pipeline.loops.<pair>.max`
* **Dry-run modes**: `--dry-run` (full), `--dry-run=minimal` (paths only), `--dry-run=diff` (diffs only)
* **External models**: `--models external` → `src/<app>/models.py`, `--models split` for separate files
* **Task queues**: Group by queue, call `start_service` once per queue
* **Doctor scope**: Check permissions, package versions, git status
* v1.1: `⊕` parallel operator codegen, DAG visualization, `restack upgrade`

---

## 18) Developer handoff checklist

* [ ] Create repo with top-level `restack_gen/` and a sample `examples/blog/`.
* [ ] Implement CLI commands & templates listed above.
* [ ] Add CI (lint/test) and pre-commit.
* [ ] Verify acceptance criteria locally.
* [ ] Write usage docs & operator cheatsheet.

---

### Appendix A — Operator cheatsheet

* `A → B` : sequential `await child_execute(B, ...)`
* `A ⇄ B` : `while condition: await A; await B;`
* `A →? B` : `if flag: await B`
* *(v1.1)* `A ⊕ {B,C}` : `await asyncio.gather(child_start(B), child_start(C))`

