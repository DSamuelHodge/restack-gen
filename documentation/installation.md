# Installation

This guide covers requirements, installation methods, and verification steps for Restack Gen.

## Requirements

- Python 3.11 or newer
- Windows, macOS, or Linux
- Recommended: a virtual environment (venv)

## Install

You can install with uv (recommended) or pip.

PowerShell (Windows):

```powershell
# Optional: create and activate a virtual environment
py -3.11 -m venv .venv; . .venv/Scripts/Activate.ps1

# Install with uv
uv pip install restack-gen

# Or install with pip
pip install --upgrade pip; pip install restack-gen
```

macOS/Linux (bash/zsh):

```bash
# Optional: create and activate a virtual environment
python3.11 -m venv .venv && source .venv/bin/activate

# Install with uv
uv pip install restack-gen

# Or install with pip
python -m pip install --upgrade pip && pip install restack-gen
```

## Verify

```bash
restack --version
restack --help
```

You should see the CLI version (e.g., 1.0.0) and a list of commands.

## Upgrade

```bash
pip install --upgrade restack-gen
# or
uv pip install --upgrade restack-gen
```

## Uninstall

```bash
pip uninstall restack-gen
```

## Troubleshooting install

- "Command not found": ensure your Python Scripts directory is on PATH, or activate your venv.
  - On Windows venv: `. .venv/Scripts/Activate.ps1`
  - On macOS/Linux venv: `source .venv/bin/activate`
- Multiple Python versions: prefer `py -3.11` on Windows or `python3.11` on Unix.
- Corporate proxies: configure pip with `--proxy` or set environment variables as needed.
