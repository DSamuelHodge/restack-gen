# Quickstart

Get up and running with Restack Gen in minutes.

## 1) Install

See Installation guide or:

```powershell
uv pip install restack-gen
# or
pip install restack-gen
```

## 2) Create a new app

```powershell
restack new myapp
cd myapp
```

Generated layout:

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

## 3) Sanity check

```powershell
restack doctor
```

Fix any warnings shown.

## 4) Run the server

```powershell
restack run:server
```

This imports `server/service.py` and registers all resources with the Restack engine (in offline mode by default).

## 5) Trigger a workflow

```powershell
python client/run_workflow.py
```

## 6) Generate resources

```powershell
# Generate an agent
restack g agent Onboarding

# Generate a workflow
restack g workflow EmailCampaign

# Generate a function
restack g function SendEmail
```

## 7) Pipelines via operator grammar

```powershell
restack g pipeline BlogPipeline \
  --operators "IDEATE ⇄ RESEARCH → PLAN → OUTLINE → DRAFT ⇄ REVIEW → POLISH → PUBLISH → PROMOTE →? REPURPOSE" \
  --style subworkflows
```

- `→` : sequence (A then B)
- `⇄` : refinement loop (iterate between A and B)
- `→?` : conditional (run B only if condition met)

## Next steps

- Explore CLI Reference for all flags and options
- Check Troubleshooting if anything behaves unexpectedly
- Review templates to see generated code patterns and safe customization points
