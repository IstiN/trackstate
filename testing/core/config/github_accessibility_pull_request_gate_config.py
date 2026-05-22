from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class GitHubAccessibilityPullRequestGateConfig:
    repository: str
    base_branch: str
    target_workflow_name: str
    target_workflow_path: str
    probe_path: str
    probe_render_host_path: str
    branch_prefix: str
    commit_message: str
    pull_request_title: str
    pull_request_body: str
    expected_accessibility_markers: list[str]
    contrast_evidence_markers: list[str]
    semantic_evidence_markers: list[str]
    accessibility_job_markers: list[str] = field(
        default_factory=lambda: ["Accessibility checks", "accessibility"]
    )
    downstream_job_markers: list[str] = field(
        default_factory=lambda: ["Deploy", "deployment", "publish", "pages", "distribution"]
    )
    poll_interval_seconds: int = 5
    run_timeout_seconds: int = 600
    pull_request_timeout_seconds: int = 120

    @classmethod
    def from_file(cls, path: Path) -> "GitHubAccessibilityPullRequestGateConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "GitHub accessibility pull request gate config must deserialize to a "
                f"mapping: {path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "GitHub accessibility pull request gate config runtime_inputs must "
                f"deserialize to a mapping: {path}"
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
            probe_path=cls._require_string(runtime_inputs, "probe_path", path),
            probe_render_host_path=cls._require_string(
                runtime_inputs,
                "probe_render_host_path",
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
            expected_accessibility_markers=cls._require_string_list(
                runtime_inputs,
                "expected_accessibility_markers",
                path,
            ),
            contrast_evidence_markers=cls._require_string_list(
                runtime_inputs,
                "contrast_evidence_markers",
                path,
            ),
            semantic_evidence_markers=cls._require_string_list(
                runtime_inputs,
                "semantic_evidence_markers",
                path,
            ),
            accessibility_job_markers=cls._optional_string_list(
                runtime_inputs,
                "accessibility_job_markers",
                default=["Accessibility checks", "accessibility"],
            ),
            downstream_job_markers=cls._optional_string_list(
                runtime_inputs,
                "downstream_job_markers",
                default=["Deploy", "deployment", "publish", "pages", "distribution"],
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
                default=600,
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
                "GitHub accessibility pull request gate config is missing "
                f"runtime_inputs.{key} in {path}."
            )
        return value.strip()

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> list[str]:
        raw = payload.get(key)
        if not isinstance(raw, list):
            raise ValueError(
                "GitHub accessibility pull request gate config runtime_inputs."
                f"{key} must be a list in {path}."
            )
        values = [str(entry).strip() for entry in raw if str(entry).strip()]
        if not values:
            raise ValueError(
                "GitHub accessibility pull request gate config runtime_inputs."
                f"{key} must contain at least one non-empty string in {path}."
            )
        return values

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
                "GitHub accessibility pull request gate config runtime_inputs."
                f"{key} must be a positive integer in {path}."
            )
        return value

    @staticmethod
    def _optional_string_list(
        payload: dict[str, Any],
        key: str,
        *,
        default: list[str],
    ) -> list[str]:
        raw = payload.get(key, default)
        if not isinstance(raw, list):
            return list(default)
        values = [str(entry).strip() for entry in raw if str(entry).strip()]
        return values or list(default)
