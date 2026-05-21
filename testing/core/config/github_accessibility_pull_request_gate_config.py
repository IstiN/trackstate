from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class GitHubAccessibilityPullRequestGateConfig:
    repository: str
    base_branch: str
    target_workflow_name: str
    target_workflow_path: str
    expected_accessibility_markers: list[str]
    ui_timeout_seconds: int = 60

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
            expected_accessibility_markers=cls._require_string_list(
                runtime_inputs,
                "expected_accessibility_markers",
                path,
            ),
            ui_timeout_seconds=cls._require_positive_int(
                runtime_inputs,
                "ui_timeout_seconds",
                path,
                default=60,
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
