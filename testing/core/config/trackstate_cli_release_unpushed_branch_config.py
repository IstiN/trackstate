from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from testing.core.config.live_setup_test_config import load_live_setup_test_config


@dataclass(frozen=True)
class TrackStateCliReleaseUnpushedBranchConfig:
    ticket_command: str
    requested_command: tuple[str, ...]
    repository: str
    base_branch: str
    unpushed_branch: str
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    release_tag_prefix: str
    source_file_name: str
    source_file_text: str
    expected_attachment_relative_path: str
    required_visible_fragments: tuple[str, ...]
    required_any_visible_fragments: tuple[str, ...]
    prohibited_visible_fragments: tuple[str, ...]

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
    ) -> "TrackStateCliReleaseUnpushedBranchConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-593 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-593 config runtime_inputs must deserialize to a mapping: {path}",
            )

        live_setup = load_live_setup_test_config()
        repository = cls._optional_string(runtime_inputs, "repository") or live_setup.repository
        base_branch = cls._optional_string(runtime_inputs, "base_branch") or live_setup.ref

        return cls(
            ticket_command=cls._require_string(runtime_inputs, "ticket_command", path),
            requested_command=cls._require_string_list(
                runtime_inputs,
                "requested_command",
                path,
            ),
            repository=repository,
            base_branch=base_branch,
            unpushed_branch=cls._require_string(runtime_inputs, "unpushed_branch", path),
            project_key=cls._require_string(runtime_inputs, "project_key", path),
            project_name=cls._require_string(runtime_inputs, "project_name", path),
            issue_key=cls._require_string(runtime_inputs, "issue_key", path),
            issue_summary=cls._require_string(runtime_inputs, "issue_summary", path),
            release_tag_prefix=cls._require_string(
                runtime_inputs,
                "release_tag_prefix",
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
            required_visible_fragments=cls._require_lower_string_list(
                runtime_inputs,
                "required_visible_fragments",
                path,
            ),
            required_any_visible_fragments=cls._optional_lower_string_list(
                runtime_inputs,
                "required_any_visible_fragments",
                path,
            ),
            prohibited_visible_fragments=cls._optional_lower_string_list(
                runtime_inputs,
                "prohibited_visible_fragments",
                path,
            ),
        )

    @staticmethod
    def _optional_string(payload: dict[str, Any], key: str) -> str | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"TS-593 config runtime_inputs.{key} must be a string.")
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"TS-593 config runtime_inputs.{key} must be a string in {path}.",
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
                f"TS-593 config runtime_inputs.{key} must be a non-empty list in {path}.",
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-593 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}.",
                )
            items.append(item)
        return tuple(items)

    @staticmethod
    def _require_lower_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        return tuple(
            item.lower()
            for item in TrackStateCliReleaseUnpushedBranchConfig._require_string_list(
                payload,
                key,
                path,
            )
        )

    @staticmethod
    def _optional_lower_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ValueError(
                f"TS-593 config runtime_inputs.{key} must be a list in {path}.",
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-593 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}.",
                )
            items.append(item.lower())
        return tuple(items)
