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
    probe_branch_prefix: str
    probe_file_path: str
    hardcoded_color_expression: str
    pull_request_title_prefix: str
    recent_run_limit: int = 10
    poll_interval_seconds: int = 5
    workflow_run_timeout_seconds: int = 600
    pull_request_state_timeout_seconds: int = 90

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
            probe_branch_prefix=cls._require_string(
                runtime_inputs,
                "probe_branch_prefix",
                path,
            ),
            probe_file_path=cls._require_string(runtime_inputs, "probe_file_path", path),
            hardcoded_color_expression=cls._require_string(
                runtime_inputs,
                "hardcoded_color_expression",
                path,
            ),
            pull_request_title_prefix=cls._require_string(
                runtime_inputs,
                "pull_request_title_prefix",
                path,
            ),
            recent_run_limit=cls._require_positive_int(
                runtime_inputs,
                "recent_run_limit",
                path,
                default=10,
            ),
            poll_interval_seconds=cls._require_positive_int(
                runtime_inputs,
                "poll_interval_seconds",
                path,
                default=5,
            ),
            workflow_run_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "workflow_run_timeout_seconds",
                path,
                default=600,
            ),
            pull_request_state_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "pull_request_state_timeout_seconds",
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
                f"TS-131 config runtime_inputs.{key} must be a positive integer in "
                f"{path}."
            )
        return value
