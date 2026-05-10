from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class PullRequestReleaseDryRunConfig:
    repository: str
    workflow_path: str
    workflow_name: str
    dry_run_name_markers: tuple[str, ...]
    dry_run_command_markers: tuple[str, ...]
    base_branch: str
    probe_file_path: str
    branch_prefix: str
    pull_request_title: str
    pull_request_body: str
    poll_interval_seconds: int = 5
    run_timeout_seconds: int = 90
    pull_request_timeout_seconds: int = 60

    @classmethod
    def from_file(cls, path: Path) -> "PullRequestReleaseDryRunConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-250 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-250 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            repository=cls._require_string(runtime_inputs, "repository", path),
            workflow_path=cls._require_string(runtime_inputs, "workflow_path", path),
            workflow_name=cls._require_string(runtime_inputs, "workflow_name", path),
            dry_run_name_markers=cls._require_string_list(
                runtime_inputs,
                "dry_run_name_markers",
                path,
            ),
            dry_run_command_markers=cls._require_string_list(
                runtime_inputs,
                "dry_run_command_markers",
                path,
            ),
            base_branch=cls._require_string(runtime_inputs, "base_branch", path),
            probe_file_path=cls._require_string(
                runtime_inputs,
                "probe_file_path",
                path,
            ),
            branch_prefix=cls._require_string(runtime_inputs, "branch_prefix", path),
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
                default=90,
            ),
            pull_request_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "pull_request_timeout_seconds",
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
            raise ValueError(f"TS-250 config is missing runtime_inputs.{key} in {path}.")
        return value.strip()

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list):
            raise ValueError(
                f"TS-250 config runtime_inputs.{key} must be a list in {path}."
            )

        normalized: list[str] = []
        for entry in value:
            if not isinstance(entry, str) or not entry.strip():
                raise ValueError(
                    f"TS-250 config runtime_inputs.{key} must contain non-empty strings in {path}."
                )
            normalized.append(entry.strip())
        if not normalized:
            raise ValueError(
                f"TS-250 config runtime_inputs.{key} must not be empty in {path}."
            )
        return tuple(normalized)

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
                f"TS-250 config runtime_inputs.{key} must be a positive integer in {path}."
            )
        return value
