"""Pytest configuration and fixtures."""

import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_project_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing project generation."""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_settings_yaml() -> str:
    """Sample settings.yaml content for testing."""
    return """
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
"""
