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
    probe_relative_path: str
    pull_request_branch_prefix: str = "ts131-non-tokenized-color"
    recent_run_limit: int = 10
    run_timeout_seconds: int = 900
    poll_interval_seconds: int = 5

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
        run_timeout_seconds = runtime_inputs.get("run_timeout_seconds", 900)
        if not isinstance(run_timeout_seconds, int) or run_timeout_seconds <= 0:
            raise ValueError(
                "TS-131 config runtime_inputs.run_timeout_seconds must be a positive integer."
            )
        poll_interval_seconds = runtime_inputs.get("poll_interval_seconds", 5)
        if not isinstance(poll_interval_seconds, int) or poll_interval_seconds <= 0:
            raise ValueError(
                "TS-131 config runtime_inputs.poll_interval_seconds must be a positive integer."
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
            probe_relative_path=cls._require_string(
                runtime_inputs,
                "probe_relative_path",
                path,
            ),
            pull_request_branch_prefix=cls._require_string(
                runtime_inputs,
                "pull_request_branch_prefix",
                path,
            ),
            recent_run_limit=recent_run_limit,
            run_timeout_seconds=run_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
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
