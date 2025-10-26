"""Minimal prompt loader for the example.

It reads config/prompts.yaml and returns the file content for the latest
version of the requested prompt.
"""
from __future__ import annotations

from pathlib import Path

import yaml


def load_prompt(base_dir: str, name: str) -> str | None:
    root = Path(base_dir)
    cfg = root / "config" / "prompts.yaml"
    if not cfg.exists():
        return None
    data = yaml.safe_load(cfg.read_text(encoding="utf-8")) or {}
    prompts = data.get("prompts", {})
    p = prompts.get(name)
    if not p:
        return None
    latest = p.get("latest")
    versions = p.get("versions", {})
    path = versions.get(latest)
    if not path:
        return None
    content_path = (root / path).resolve()
    if not content_path.exists():
        return None
    return content_path.read_text(encoding="utf-8")
