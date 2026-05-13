from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from testing.core.config.live_setup_test_config import load_live_setup_test_config


@dataclass(frozen=True)
class TrackStateCliReleaseAssetFilenameSanitizationConfig:
    ticket_command: str
    requested_command: tuple[str, ...]
    repository: str
    branch: str
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    release_tag_prefix_base: str
    expected_sanitized_asset_name: str
    manifest_poll_timeout_seconds: int
    manifest_poll_interval_seconds: int
    release_poll_timeout_seconds: int
    release_poll_interval_seconds: int

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @property
    def manifest_path(self) -> str:
        return f"{self.project_key}/{self.issue_key}/attachments.json"

    @classmethod
    def from_file(
        cls,
        path: Path,
    ) -> "TrackStateCliReleaseAssetFilenameSanitizationConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                f"Release asset sanitization config must deserialize to a mapping: {path}",
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "Release asset sanitization config runtime_inputs must deserialize "
                f"to a mapping: {path}",
            )

        live_setup = load_live_setup_test_config()
        repository = cls._optional_string(runtime_inputs, "repository") or live_setup.repository
        branch = cls._optional_string(runtime_inputs, "branch") or live_setup.ref

        return cls(
            ticket_command=cls._require_string(runtime_inputs, "ticket_command", path),
            requested_command=cls._require_string_list(
                runtime_inputs,
                "requested_command",
                path,
            ),
            repository=repository,
            branch=branch,
            project_key=cls._require_string(runtime_inputs, "project_key", path),
            project_name=cls._require_string(runtime_inputs, "project_name", path),
            issue_key=cls._require_string(runtime_inputs, "issue_key", path),
            issue_summary=cls._require_string(runtime_inputs, "issue_summary", path),
            source_file_name=cls._require_string(runtime_inputs, "source_file_name", path),
            source_file_text=cls._require_string(runtime_inputs, "source_file_text", path),
            release_tag_prefix_base=cls._require_string(
                runtime_inputs,
                "release_tag_prefix_base",
                path,
            ),
            expected_sanitized_asset_name=cls._require_string(
                runtime_inputs,
                "expected_sanitized_asset_name",
                path,
            ),
            manifest_poll_timeout_seconds=cls._require_int(
                runtime_inputs,
                "manifest_poll_timeout_seconds",
                path,
            ),
            manifest_poll_interval_seconds=cls._require_int(
                runtime_inputs,
                "manifest_poll_interval_seconds",
                path,
            ),
            release_poll_timeout_seconds=cls._require_int(
                runtime_inputs,
                "release_poll_timeout_seconds",
                path,
            ),
            release_poll_interval_seconds=cls._require_int(
                runtime_inputs,
                "release_poll_interval_seconds",
                path,
            ),
        )

    @staticmethod
    def _optional_string(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(
                f"Release asset sanitization config runtime_inputs.{key} must be a string.",
            )
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                "Release asset sanitization config runtime_inputs."
                f"{key} must be a string in {path}.",
            )
        return value

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, path: Path) -> int:
        value = payload.get(key)
        if not isinstance(value, int):
            raise ValueError(
                "Release asset sanitization config runtime_inputs."
                f"{key} must be an integer in {path}.",
            )
        return value

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(
                "Release asset sanitization config runtime_inputs."
                f"{key} must be a non-empty list in {path}.",
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "Release asset sanitization config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}.",
                )
            items.append(item)
        return tuple(items)
