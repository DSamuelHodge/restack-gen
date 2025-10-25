# CLI Reference

The `restack` CLI is built with Typer. Commands follow a convention-over-configuration style.

Use `restack --help` or `restack <command> --help` for details.

## Global

```bash
restack --version
restack --help
```

---

## Create a new app

```bash
restack new <app_name>
```

- Creates a new project with the omakase layout.

Options:
- `--force` Overwrite existing destination
- `--dry-run [minimal|diff]` Preview without writing

Examples:
```bash
restack new myapp
restack new myapp --dry-run=diff
```

---

## Generator: agent

```bash
restack g agent <Name>
```

- Creates an agent with events, handlers, and tests.

Common options (generators):
- `--task-queue <name>` Set task queue
- `--omit-tests` Skip test generation
- `--models [external|split]` Model placement strategy
- `--map TOKEN:CustomName` Override token-to-class mapping (repeatable)
- `--force` Overwrite existing files
- `--dry-run [minimal|diff]` Preview without writing

---

## Generator: workflow

```bash
restack g workflow <Name>
```

- Creates a typed, stepwise orchestrator and tests.

(Uses the same common generator options as above.)

---

## Generator: function

```bash
restack g function <Name>
```

- Creates a stateless leaf operation and tests.

(Uses the same common generator options as above.)

---

## Generator: pipeline

```bash
restack g pipeline <Name> --operators "..." [--style subworkflows]
```

- Parses operator grammar and emits code.
- Operators:
  - `→` sequence (A then B)
  - `⇄` refinement loop (iterate between A and B)
  - `→?` conditional (run B only if condition met)

Options:
- `--operators` Required operator string
- `--style` Pipeline style (e.g., `subworkflows`)
- Common generator options apply

Examples:
```bash
restack g pipeline BlogPipeline \
  --operators "IDEATE ⇄ RESEARCH → PLAN → OUTLINE → DRAFT ⇄ REVIEW → POLISH → PUBLISH → PROMOTE →? REPURPOSE" \
  --style subworkflows
```

---

## Run server

```bash
restack run:server [--config <path>]
```

- Starts the service by importing `server/service.py`.
- Merges environment variables from `.env` (if present).
- Sets `RESTACK_CONFIG` to the provided config path, if any.
- Gracefully handles Ctrl+C (SIGINT) and termination (SIGTERM).

Options:
- `--config <path>` Path to a YAML/TOML/JSON settings file

Common errors:
- `service.py not found` → Run from a project root created by `restack new`.

---

## Doctor

```bash
restack doctor
```

- Validates environment, packages, import resolution, file permissions, and connectivity.
- Prints clear warnings and suggestions.

Notes:
- Run this before `run:server` to catch issues early.
