from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliMixedAttachmentResolutionConfig:
    ticket_command_upload: str
    ticket_command_download: str
    requested_upload_command: tuple[str, ...]
    requested_download_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    legacy_attachment_name: str
    legacy_attachment_text: str
    legacy_attachment_created_at: str
    legacy_attachment_author: str
    new_attachment_name: str
    new_attachment_base64: str
    github_release_tag_prefix: str
    expected_legacy_backend: str
    expected_new_backend: str
    expected_upload_command_name: str
    expected_download_command_name: str

    @property
    def manifest_relative_path(self) -> str:
        return f"{self.project_key}/{self.issue_key}/attachments.json"

    @property
    def issue_main_relative_path(self) -> str:
        return f"{self.project_key}/{self.issue_key}/main.md"

    @property
    def legacy_attachment_relative_path(self) -> str:
        return (
            f"{self.project_key}/{self.issue_key}/attachments/"
            f"{self.legacy_attachment_name}"
        )

    @property
    def legacy_attachment_bytes(self) -> bytes:
        return self.legacy_attachment_text.encode("utf-8")

    @property
    def new_attachment_bytes(self) -> bytes:
        return base64.b64decode(self.new_attachment_base64)

    @property
    def expected_github_release_tag(self) -> str:
        return f"{self.github_release_tag_prefix}{self.issue_key}"

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliMixedAttachmentResolutionConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-485 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                f"TS-485 config runtime_inputs must deserialize to a mapping: {path}"
            )

        return cls(
            ticket_command_upload=cls._require_string(
                runtime_inputs,
                "ticket_command_upload",
                path,
            ),
            ticket_command_download=cls._require_string(
                runtime_inputs,
                "ticket_command_download",
                path,
            ),
            requested_upload_command=cls._require_string_list(
                runtime_inputs,
                "requested_upload_command",
                path,
            ),
            requested_download_command=cls._require_string_list(
                runtime_inputs,
                "requested_download_command",
                path,
            ),
            project_key=cls._require_string(runtime_inputs, "project_key", path),
            project_name=cls._require_string(runtime_inputs, "project_name", path),
            issue_key=cls._require_string(runtime_inputs, "issue_key", path),
            issue_summary=cls._require_string(runtime_inputs, "issue_summary", path),
            legacy_attachment_name=cls._require_string(
                runtime_inputs,
                "legacy_attachment_name",
                path,
            ),
            legacy_attachment_text=cls._require_string(
                runtime_inputs,
                "legacy_attachment_text",
                path,
            ),
            legacy_attachment_created_at=cls._require_string(
                runtime_inputs,
                "legacy_attachment_created_at",
                path,
            ),
            legacy_attachment_author=cls._require_string(
                runtime_inputs,
                "legacy_attachment_author",
                path,
            ),
            new_attachment_name=cls._require_string(
                runtime_inputs,
                "new_attachment_name",
                path,
            ),
            new_attachment_base64=cls._require_string(
                runtime_inputs,
                "new_attachment_base64",
                path,
            ),
            github_release_tag_prefix=cls._require_string(
                runtime_inputs,
                "github_release_tag_prefix",
                path,
            ),
            expected_legacy_backend=cls._require_string(
                runtime_inputs,
                "expected_legacy_backend",
                path,
            ),
            expected_new_backend=cls._require_string(
                runtime_inputs,
                "expected_new_backend",
                path,
            ),
            expected_upload_command_name=cls._require_string(
                runtime_inputs,
                "expected_upload_command_name",
                path,
            ),
            expected_download_command_name=cls._require_string(
                runtime_inputs,
                "expected_download_command_name",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"TS-485 config runtime_inputs.{key} must be a string in {path}."
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
                f"TS-485 config runtime_inputs.{key} must be a non-empty list in {path}."
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-485 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)
