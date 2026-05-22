from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from testing.components.services.github_accessibility_cancellation_probe import (
    GitHubAccessibilityCancellationProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)
from testing.core.interfaces.github_accessibility_cancellation_probe import (
    GitHubAccessibilityCancellationProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_github_accessibility_cancellation_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> GitHubAccessibilityCancellationProbe:
    resolved_config_path = config_path or repository_root / "testing/tests/TS-962/config.yaml"
    config = GitHubAccessibilityPullRequestGateConfig.from_file(resolved_config_path)
    raw_config = _load_yaml(resolved_config_path)
    runtime_inputs = raw_config.get("runtime_inputs", {})
    if not isinstance(runtime_inputs, dict):
        raise ValueError(
            f"runtime_inputs must deserialize to a mapping in {resolved_config_path}."
        )
    return GitHubAccessibilityCancellationProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
        accessibility_job_name=_required_string(runtime_inputs, "accessibility_job_name"),
        axe_step_name=_required_string(runtime_inputs, "axe_step_name"),
        log_validation_step_name=_required_string(
            runtime_inputs,
            "log_validation_step_name",
        ),
        cancellation_hold_seconds=_required_positive_int(
            runtime_inputs,
            "cancellation_hold_seconds",
        ),
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must deserialize to a mapping.")
    return payload


def _required_string(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"runtime_inputs.{key} must be a non-empty string.")
    return value.strip()


def _required_positive_int(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"runtime_inputs.{key} must be a positive integer.")
    return value
