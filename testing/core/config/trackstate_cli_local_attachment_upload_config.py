from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliLocalAttachmentUploadConfig:
    ticket_command: str
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    expected_issue_key: str
    expected_attachment_name: str
    expected_media_type: str

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @property
    def expected_size_bytes(self) -> int:
        return len(self.source_file_bytes)

    @property
    def expected_attachment_directory(self) -> str:
        return f"{self.project_key}/{self.issue_key}/attachments"

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliLocalAttachmentUploadConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "TS-381 config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TS-381 config runtime_inputs must deserialize to a mapping: "
                f"{path}"
            )

        requested_command = cls._require_string_list(
            runtime_inputs,
            "requested_command",
            path,
        )

        return cls(
            ticket_command=cls._require_string(runtime_inputs, "ticket_command", path),
            requested_command=requested_command,
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
            expected_media_type=cls._require_string(
                runtime_inputs,
                "expected_media_type",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"TS-381 config runtime_inputs.{key} must be a string in {path}.")
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
                f"TS-381 config runtime_inputs.{key} must be a non-empty list in {path}."
            )
        items = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-381 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)
