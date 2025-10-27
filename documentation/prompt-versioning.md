# Prompt Registry & Versioning

Flexible, explicit prompt management with a simple registry, semantic versions, and a tiny loader.

## Overview

Prompt content lives in versioned Markdown files with YAML frontmatter. A central registry
(`config/prompts.yaml`) maps logical prompt names to available versions and the file path for each
version. At runtime you resolve either a specific version (e.g. `1.2.0`) or the latest version.

Key pieces:
- Registry file: `config/prompts.yaml`
- Versioned prompt files: `prompts/<name>/<version>.md` (frontmatter + Markdown body)
- Loader: `PromptLoader` resolves prompt by name and version and returns the parsed result
- Generator: `restack g prompt <Name> --version X.Y.Z` scaffolds registry + first file

## Registry schema

`config/prompts.yaml` is a plain map of prompt names to their versions and paths:

```yaml
prompts:
  summarize:
    latest: 1.0.0
    versions:
      "1.0.0": prompts/summarize/1.0.0.md
  extract_entities:
    latest: 0.2.0
    versions:
      "0.1.0": prompts/extract_entities/0.1.0.md
      "0.2.0": prompts/extract_entities/0.2.0.md
```

Notes:
- Versions are semantic (X.Y.Z). The generator quotes them in YAML to avoid implicit numeric parsing.
- `latest` is just a pointer for convenience—update it as you publish a new version.

## Prompt file format

Each prompt file is Markdown with YAML frontmatter:

```markdown
---
name: summarize
version: 1.0.0
tags: [default, summarization]
inputs:
  - name: text
    type: string
    required: true
---

Summarize the following content in 3 bullet points:

{{ text }}
```

The loader parses frontmatter and returns both the metadata and the body.

## Using PromptLoader

The loader supports two resolution modes: exact version and latest.

```python
from myapp.common.prompt_loader import PromptLoader

loader = PromptLoader(root_dir=".")

# Exact version
prompt = await loader.load("summarize", version="1.0.0")

# Latest
prompt_latest = await loader.load("summarize")

print(prompt.metadata)  # dict with name/version/inputs/tags
print(prompt.content)   # markdown string after frontmatter
```

Error modes:
- Unknown prompt name → raises a descriptive error
- Unknown version for known prompt → raises a descriptive error
- Missing file or invalid frontmatter → raises a descriptive error

## Generating a new prompt

```powershell
restack g prompt Summarize --version 1.0.0
```

What this does:
- Creates `prompts/summarize/1.0.0.md` with a starter frontmatter block
- Creates or updates `config/prompts.yaml` with `latest` and `versions`
- Adds generated marker comments so re-runs are safe; use `--force` to overwrite

## Versioning workflow

1) Start with `1.0.0` and wire it to your agents/workflows
2) To iterate without breaking callers, add `1.1.0` (or `2.0.0` if breaking)
3) Update `latest` in `config/prompts.yaml` to the new version
4) Consumers that opt into `latest` pick up the update; consumers pinned to an exact version stay stable

## Tips

- Keep frontmatter small and focused: name, version, optional tags and inputs for clarity.
- Treat prompts like code: version with intent; prefer additive changes in minor versions.
- Consider adding unit tests around template variables to catch accidental changes.

## Troubleshooting

- “prompt not found”: Check the `prompts` map in `config/prompts.yaml`.
- “version not found”: Ensure the specific X.Y.Z exists under `versions` for that prompt.
- “invalid frontmatter”: Verify the YAML header is well-formed and closed with `---`.

## See also

- CLI Reference: `restack g prompt --help`
- Templates: browse `restack_gen/templates/prompt_loader.py.j2` for implementation details
- Project docs: Quickstart, Pipelines, Templates
