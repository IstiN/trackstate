from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliReleaseExistingTagConfig:
    ticket_command: str
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    attachment_tag_prefix: str
    expected_issue_key: str
    expected_attachment_name: str
    expected_attachment_relative_path: str
    expected_release_tag: str
    expected_release_title: str
    expected_release_body: str

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @property
    def issue_path(self) -> str:
        return f"{self.project_key}/{self.issue_key}"

    @property
    def manifest_path(self) -> str:
        return f"{self.issue_path}/attachments.json"

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliReleaseExistingTagConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "TS-555 config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TS-555 config runtime_inputs must deserialize to a mapping: "
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
            expected_release_tag=cls._require_string(
                runtime_inputs,
                "expected_release_tag",
                path,
            ),
            expected_release_title=cls._require_string(
                runtime_inputs,
                "expected_release_title",
                path,
            ),
            expected_release_body=cls._require_string(
                runtime_inputs,
                "expected_release_body",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"TS-555 config runtime_inputs.{key} must be a string in {path}.")
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
                f"TS-555 config runtime_inputs.{key} must be a non-empty list in {path}."
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-555 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)
