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
    recent_run_limit: int = 10

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

        recent_run_limit = runtime_inputs.get("recent_run_limit", 10)
        if not isinstance(recent_run_limit, int) or recent_run_limit <= 0:
            raise ValueError(
                "TS-131 config runtime_inputs.recent_run_limit must be a positive integer."
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
            recent_run_limit=recent_run_limit,
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
