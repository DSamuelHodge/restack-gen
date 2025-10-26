"""PR #9: Doctor Enhancements tests.

Covers:
- Kong reachability detection
- Prompt registry file existence
- Provider env var validation
"""

from __future__ import annotations

import os
from pathlib import Path

from restack_gen import doctor


def write_llm_config(
    tmp: Path,
    *,
    backend: str,
    url: str = "http://localhost:8000",
    timeout: int = 1,
    env_var: str = "OPENAI_API_KEY",
) -> None:
    cfg_dir = tmp / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "llm_router.yaml").write_text(
        f"""
llm:
  router:
    backend: "{backend}"
    url: "{url}"
    timeout: {timeout}
  providers:
    - name: "openai-primary"
      type: "openai"
      model: "gpt-4o-mini"
      base_url: "${{OPENAI_BASE_URL:-https://api.openai.com/v1}}"
      api_key: "${{{env_var}}}"
      priority: 1
  fallback:
    conditions: [timeout, 5xx, rate_limit]
    max_retries_per_provider: 1
    circuit_breaker:
      enabled: true
      failure_threshold: 3
      cooldown_seconds: 1
""",
        encoding="utf-8",
    )


def test_kong_unreachable(tmp_path: Path) -> None:
    # Use an unlikely-to-be-open port to simulate unreachable
    write_llm_config(tmp_path, backend="kong", url="http://localhost:9", timeout=1)
    res = doctor.check_kong_gateway(tmp_path)
    assert res.name == "kong"
    assert res.status == "fail"
    assert "not reachable" in res.message.lower()


def test_prompts_missing_files(tmp_path: Path) -> None:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    prompts = cfg_dir / "prompts.yaml"
    prompts.write_text(
        """
prompts:
  demo:
    description: "Demo prompt"
    versions:
      "1.0.0": "prompts/demo/v1.0.0.md"
    latest: "1.0.0"
""",
        encoding="utf-8",
    )
    # Do not create the referenced file to trigger warning
    res = doctor.check_prompts(tmp_path)
    assert res.name == "prompts"
    assert res.status in {"warn", "fail"}
    assert "missing" in (res.details or "").lower()


def test_llm_config_env_var_validation(tmp_path: Path) -> None:
    missing_env = "RESTACK_TEST_ENV_MISSING"
    # Ensure it's not set
    prev = os.environ.pop(missing_env, None)
    try:
        write_llm_config(tmp_path, backend="direct", env_var=missing_env)
        res = doctor.check_llm_config(tmp_path)
        assert res.name == "llm_config"
        assert res.status in {"warn", "fail"}
        assert missing_env in res.message
    finally:
        if prev is not None:
            os.environ[missing_env] = prev
