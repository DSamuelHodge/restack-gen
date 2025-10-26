"""Tests for prompt registry and versioning (PR #5)."""

import importlib
import sys
from pathlib import Path

import pytest

from restack_gen.generator import GenerationError, generate_prompt
from restack_gen.project import create_new_project


class TestPromptVersioning:
    @pytest.fixture
    def temp_project(self, tmp_path, monkeypatch):
        project_path = tmp_path / "testapp"
        create_new_project("testapp", parent_dir=tmp_path, force=False)
        monkeypatch.chdir(project_path)
        return project_path

    def _add_src_to_path(self, project_path: Path):
        pkg = project_path.name
        src_path = project_path / "src"
        # Prepend project src for import resolution
        if str(src_path) not in sys.path:
            sys.path.insert(0, str(src_path))
        # Avoid cross-test package caching (other tests also use 'testapp')
        for mod in list(sys.modules.keys()):
            if mod == pkg or mod.startswith(f"{pkg}."):
                sys.modules.pop(mod, None)
        return pkg

    def test_generate_prompt_creates_files_and_registry(self, temp_project):
        files = generate_prompt("AnalyzeResearch", version="1.0.0", force=True)
        assert files["prompt"].exists()
        assert files["config"].exists()
        # first call should generate loader
        assert files["loader"] is not None

        # Path correctness
        assert files["prompt"].as_posix().endswith("prompts/analyze_research/v1.0.0.md")

        # Registry content
        text = files["config"].read_text()
        assert "prompts:" in text
        assert "analyze_research:" in text
        assert "versions:" in text
        assert '"1.0.0": "prompts/analyze_research/v1.0.0.md"' in text
        assert 'latest: "1.0.0"' in text

    @pytest.mark.asyncio
    async def test_prompt_loader_resolves_versions(self, temp_project):
        # Create multiple versions
        generate_prompt("AnalyzeResearch", version="1.0.0", force=True)
        generate_prompt("AnalyzeResearch", version="1.2.3", force=True)

        pkg = self._add_src_to_path(temp_project)
        loader_mod = importlib.import_module(f"{pkg}.common.prompt_loader")
        PromptLoader = loader_mod.PromptLoader

        loader = PromptLoader("config/prompts.yaml")
        # Latest
        tpl_latest = await loader.load("analyze_research")
        assert tpl_latest.version in {"1.0.0", "1.2.3"}
        # Exact
        tpl_exact = await loader.load("analyze_research", "1.0.0")
        assert tpl_exact.version == "1.0.0"
        # Prefix '1' -> highest 1.x.x
        tpl_major = await loader.load("analyze_research", "1")
        assert tpl_major.version == "1.2.3"
        # Prefix '1.2' -> highest 1.2.x
        tpl_minor = await loader.load("analyze_research", "1.2")
        assert tpl_minor.version == "1.2.3"

    def test_generate_prompt_outside_project_fails(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(GenerationError):
            generate_prompt("Research", version="1.0.0")

    def test_generate_prompt_refuses_overwrite_without_force(self, temp_project):
        files = generate_prompt("Research", version="1.0.0", force=True)
        assert files["prompt"].exists()
        with pytest.raises(GenerationError):
            generate_prompt("Research", version="1.0.0", force=False)
