from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class ActionlintNonWorkflowPullRequestGateConfig:
    repository: str
    base_branch: str
    probe_file_path: str
    actionlint_workflow_path: str
    expected_paths_filter: str
    branch_prefix: str
    commit_message: str
    pull_request_title: str
    pull_request_body: str
    probe_marker_template: str
    expected_actionlint_marker: str = "actionlint"
    poll_interval_seconds: int = 5
    actionlint_run_timeout_seconds: int = 45
    pull_request_timeout_seconds: int = 120

    @classmethod
    def from_file(cls, path: Path) -> "ActionlintNonWorkflowPullRequestGateConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "Actionlint non-workflow pull request gate config must deserialize "
                f"to a mapping: {path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "Actionlint non-workflow pull request gate config runtime_inputs "
                f"must deserialize to a mapping: {path}"
            )

        return cls(
            repository=cls._require_string(runtime_inputs, "repository", path),
            base_branch=cls._require_string(runtime_inputs, "base_branch", path),
            probe_file_path=cls._require_string(runtime_inputs, "probe_file_path", path),
            actionlint_workflow_path=cls._require_string(
                runtime_inputs,
                "actionlint_workflow_path",
                path,
            ),
            expected_paths_filter=cls._require_string(
                runtime_inputs,
                "expected_paths_filter",
                path,
            ),
            branch_prefix=cls._require_string(runtime_inputs, "branch_prefix", path),
            commit_message=cls._require_string(runtime_inputs, "commit_message", path),
            pull_request_title=cls._require_string(
                runtime_inputs,
                "pull_request_title",
                path,
            ),
            pull_request_body=cls._require_string(
                runtime_inputs,
                "pull_request_body",
                path,
            ),
            probe_marker_template=cls._require_string(
                runtime_inputs,
                "probe_marker_template",
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
            actionlint_run_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "actionlint_run_timeout_seconds",
                path,
                default=45,
            ),
            pull_request_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "pull_request_timeout_seconds",
                path,
                default=120,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "Actionlint non-workflow pull request gate config is missing "
                f"runtime_inputs.{key} in {path}."
            )
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
                "Actionlint non-workflow pull request gate config runtime_inputs."
                f"{key} must be a positive integer in {path}."
            )
        return value
