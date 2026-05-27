from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ThemeTokenCiConfig:
    repository: str
    workflow_path: str
    workflow_name: str
    workflow_job_name: str
    workflow_step_name: str
    gate_command: str
    base_branch: str
    probe_path: str
    branch_prefix: str
    pr_title: str
    pr_body: str
    poll_interval_seconds: int = 5
    run_timeout_seconds: int = 600
    pull_request_timeout_seconds: int = 90

    @classmethod
    def from_file(cls, path: Path) -> "ThemeTokenCiConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-131 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-131 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            repository=cls._require_string(runtime_inputs, "repository", path),
            workflow_path=cls._require_string(runtime_inputs, "workflow_path", path),
            workflow_name=cls._require_string(runtime_inputs, "workflow_name", path),
            workflow_job_name=cls._require_string(
                runtime_inputs,
                "workflow_job_name",
                path,
            ),
            workflow_step_name=cls._require_string(
                runtime_inputs,
                "workflow_step_name",
                path,
            ),
            gate_command=cls._require_string(runtime_inputs, "gate_command", path),
            base_branch=cls._require_string(runtime_inputs, "base_branch", path),
            probe_path=cls._require_string(runtime_inputs, "probe_path", path),
            branch_prefix=cls._require_string(runtime_inputs, "branch_prefix", path),
            pr_title=cls._require_string(runtime_inputs, "pr_title", path),
            pr_body=cls._require_string(runtime_inputs, "pr_body", path),
            poll_interval_seconds=cls._require_positive_int(
                runtime_inputs,
                "poll_interval_seconds",
                path,
                default=5,
            ),
            run_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "run_timeout_seconds",
                path,
                default=600,
            ),
            pull_request_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "pull_request_timeout_seconds",
                path,
                default=90,
            ),
        )

    @staticmethod
    def _require_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"TS-131 config is missing runtime_inputs.{key} in {path}.")
        return value.strip()

    @staticmethod
    def _require_positive_int(
        payload: dict[str, Any],
        key: str,
        path: Path,
        *,
        default: int,
    ) -> int:
        value = payload.get(key, default)
        if not isinstance(value, int) or value <= 0:
            raise ValueError(
                f"TS-131 config runtime_inputs.{key} must be a positive integer in {path}."
            )
        return value
