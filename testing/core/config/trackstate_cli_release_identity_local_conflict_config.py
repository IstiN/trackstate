from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from testing.core.config.live_setup_test_config import load_live_setup_test_config


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityLocalConflictConfig:
    ticket_command: str
    requested_command: tuple[str, ...]
    repository: str
    branch: str
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    release_tag_prefix: str
    conflicting_release_title: str
    expected_release_title: str
    source_file_name: str
    source_file_text: str
    expected_attachment_relative_path: str
    expected_exit_code: int
    expected_error_code: str
    expected_error_category: str
    required_reason_fragments: tuple[str, ...]
    required_stdout_fragments: tuple[str, ...]

    @property
    def expected_release_tag(self) -> str:
        return f"{self.release_tag_prefix}{self.issue_key}"

    @property
    def remote_origin_url(self) -> str:
        return f"https://github.com/{self.repository}.git"

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @classmethod
    def from_file(
        cls,
        path: Path,
    ) -> "TrackStateCliReleaseIdentityLocalConflictConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-551 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-551 config runtime_inputs must deserialize to a mapping: {path}",
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
            release_tag_prefix=cls._require_string(
                runtime_inputs,
                "release_tag_prefix",
                path,
            ),
            conflicting_release_title=cls._require_string(
                runtime_inputs,
                "conflicting_release_title",
                path,
            ),
            expected_release_title=cls._require_string(
                runtime_inputs,
                "expected_release_title",
                path,
            ),
            source_file_name=cls._require_string(
                runtime_inputs,
                "source_file_name",
                path,
            ),
            source_file_text=cls._require_string(
                runtime_inputs,
                "source_file_text",
                path,
            ),
            expected_attachment_relative_path=cls._require_string(
                runtime_inputs,
                "expected_attachment_relative_path",
                path,
            ),
            expected_exit_code=cls._require_int(
                runtime_inputs,
                "expected_exit_code",
                path,
            ),
            expected_error_code=cls._require_string(
                runtime_inputs,
                "expected_error_code",
                path,
            ),
            expected_error_category=cls._require_string(
                runtime_inputs,
                "expected_error_category",
                path,
            ),
            required_reason_fragments=cls._require_string_list(
                runtime_inputs,
                "required_reason_fragments",
                path,
            ),
            required_stdout_fragments=cls._require_string_list(
                runtime_inputs,
                "required_stdout_fragments",
                path,
            ),
        )

    @staticmethod
    def _optional_string(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"TS-551 config runtime_inputs.{key} must be a string.")
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"TS-551 config runtime_inputs.{key} must be a string in {path}.",
            )
        return value

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, path: Path) -> int:
        value = payload.get(key)
        if not isinstance(value, int):
            raise ValueError(
                f"TS-551 config runtime_inputs.{key} must be an integer in {path}.",
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
                f"TS-551 config runtime_inputs.{key} must be a non-empty list in {path}.",
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-551 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}.",
                )
            items.append(item)
        return tuple(items)
