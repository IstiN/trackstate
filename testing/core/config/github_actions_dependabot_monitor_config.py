from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class GitHubActionsDependabotMonitorConfig:
    repository: str
    base_branch: str
    dependabot_path: str
    expected_package_ecosystem: str
    expected_directory: str
    required_schedule_keys: tuple[str, ...]
    expected_visible_texts: tuple[str, ...]
    ui_missing_page_markers: tuple[str, ...]
    ui_timeout_seconds: int = 60

    @classmethod
    def from_file(cls, path: Path) -> "GitHubActionsDependabotMonitorConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "GitHub actions dependabot monitor config must deserialize to a "
                f"mapping: {path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "GitHub actions dependabot monitor config runtime_inputs must "
                f"deserialize to a mapping: {path}"
            )

        return cls(
            repository=cls._require_string(runtime_inputs, "repository", path),
            base_branch=cls._require_string(runtime_inputs, "base_branch", path),
            dependabot_path=cls._require_string(runtime_inputs, "dependabot_path", path),
            expected_package_ecosystem=cls._require_string(
                runtime_inputs,
                "expected_package_ecosystem",
                path,
            ),
            expected_directory=cls._require_string(
                runtime_inputs,
                "expected_directory",
                path,
            ),
            required_schedule_keys=cls._require_string_sequence(
                runtime_inputs,
                "required_schedule_keys",
                path,
            ),
            expected_visible_texts=cls._require_string_sequence(
                runtime_inputs,
                "expected_visible_texts",
                path,
            ),
            ui_missing_page_markers=cls._require_string_sequence(
                runtime_inputs,
                "ui_missing_page_markers",
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
    def _require_string(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(
                "GitHub actions dependabot monitor config is missing "
                f"runtime_inputs.{key} in {path}."
            )
        return value.strip()

    @staticmethod
    def _require_string_sequence(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise ValueError(
                "GitHub actions dependabot monitor config runtime_inputs."
                f"{key} must be a list of non-empty strings in {path}."
            )
        return tuple(item.strip() for item in value)

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
                "GitHub actions dependabot monitor config runtime_inputs."
                f"{key} must be a positive integer in {path}."
            )
        return value
