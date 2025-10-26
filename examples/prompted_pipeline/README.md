# Prompted Pipeline Example

This example demonstrates a multi-step pipeline that uses a simple prompt loader to guide processing.

It reads `config/prompts.yaml` to find the latest version of a prompt and loads the corresponding Markdown file from `prompts/`.

## Project Structure

```
prompted_pipeline/
├── README.md
├── pyproject.toml
├── Makefile
├── settings.yaml
├── config/
│   └── prompts.yaml           # Registry with versions and latest pointer
├── prompts/
│   └── analyze/
│       └── v1.0.0.md         # Prompt content
├── client/
│   └── run_workflow.py
└── src/
    └── prompted_pipeline/
        ├── __init__.py
        ├── service.py
        ├── common/
        │   └── prompt_loader.py
        └── workflows/
            └── prompted_pipeline_workflow.py
```

## Run

```bash
pip install -e .
make dev  # starts service
# in another terminal
python client/run_workflow.py
```

## How it works

- The workflow loads the latest "Analyze" prompt from the registry
- Chunks the input (simulated), summarizes each chunk (simulated), and merges results
- Replace the simulated parts with real LLM calls if desired (see LLM Router docs)

See also:
- Prompt versioning: ../../docs/prompt-versioning.md
- LLM Router: ../../docs/llm-router.md
- Troubleshooting: ../../docs/troubleshooting.md
