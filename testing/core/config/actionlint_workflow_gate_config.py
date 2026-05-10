from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ActionlintWorkflowGateConfig:
    repository: str
    base_branch: str
    target_workflow_name: str
    target_workflow_path: str
    branch_prefix: str
    commit_message: str
    mutation_search_text: str
    mutation_replacement_text: str
    expected_actionlint_marker: str = "actionlint"
    poll_interval_seconds: int = 5
    run_timeout_seconds: int = 60

    @classmethod
    def from_file(cls, path: Path) -> "ActionlintWorkflowGateConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-251 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-251 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            repository=cls._require_string(runtime_inputs, "repository", path),
            base_branch=cls._require_string(runtime_inputs, "base_branch", path),
            target_workflow_name=cls._require_string(
                runtime_inputs,
                "target_workflow_name",
                path,
            ),
            target_workflow_path=cls._require_string(
                runtime_inputs,
                "target_workflow_path",
                path,
            ),
            branch_prefix=cls._require_string(runtime_inputs, "branch_prefix", path),
            commit_message=cls._require_string(runtime_inputs, "commit_message", path),
            mutation_search_text=cls._require_string(
                runtime_inputs,
                "mutation_search_text",
                path,
            ),
            mutation_replacement_text=cls._require_string(
                runtime_inputs,
                "mutation_replacement_text",
                path,
            ),
            expected_actionlint_marker=cls._require_string(
                runtime_inputs,
                "expected_actionlint_marker",
                path,
            ),
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
                default=60,
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
            raise ValueError(f"TS-251 config is missing runtime_inputs.{key} in {path}.")
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
                f"TS-251 config runtime_inputs.{key} must be a positive integer in {path}."
            )
        return value
