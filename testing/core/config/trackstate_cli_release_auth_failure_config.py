from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliReleaseAuthFailureConfig:
    ticket_command: str
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    attachment_tag_prefix: str
    remote_origin_url: str
    expected_issue_key: str
    expected_attachment_name: str
    expected_attachment_relative_path: str
    expected_release_fragments: tuple[str, ...]
    expected_auth_fragments: tuple[str, ...]
    provider_capability_fragments: tuple[str, ...]

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliReleaseAuthFailureConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "TS-500 config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TS-500 config runtime_inputs must deserialize to a mapping: "
                f"{path}"
            )

        return cls(
            ticket_command=cls._require_string(runtime_inputs, "ticket_command", path),
            requested_command=cls._require_string_list(
                runtime_inputs,
                "requested_command",
                path,
            ),
            project_key=cls._require_string(runtime_inputs, "project_key", path),
            project_name=cls._require_string(runtime_inputs, "project_name", path),
            issue_key=cls._require_string(runtime_inputs, "issue_key", path),
            issue_summary=cls._require_string(runtime_inputs, "issue_summary", path),
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
            attachment_tag_prefix=cls._require_string(
                runtime_inputs,
                "attachment_tag_prefix",
                path,
            ),
            remote_origin_url=cls._require_string(
                runtime_inputs,
                "remote_origin_url",
                path,
            ),
            expected_issue_key=cls._require_string(
                runtime_inputs,
                "expected_issue_key",
                path,
            ),
            expected_attachment_name=cls._require_string(
                runtime_inputs,
                "expected_attachment_name",
                path,
            ),
            expected_attachment_relative_path=cls._require_string(
                runtime_inputs,
                "expected_attachment_relative_path",
                path,
            ),
            expected_release_fragments=cls._require_string_list(
                runtime_inputs,
                "expected_release_fragments",
                path,
            ),
            expected_auth_fragments=cls._require_string_list(
                runtime_inputs,
                "expected_auth_fragments",
                path,
            ),
            provider_capability_fragments=cls._optional_string_list(
                runtime_inputs,
                "provider_capability_fragments",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"TS-500 config runtime_inputs.{key} must be a string in {path}.")
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
                f"TS-500 config runtime_inputs.{key} must be a non-empty list in {path}."
            )
        items = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-500 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)

    @staticmethod
    def _optional_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if value is None:
            return ()
        if not isinstance(value, list):
            raise ValueError(
                f"TS-500 config runtime_inputs.{key} must be a list in {path}."
            )
        items = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-500 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)
