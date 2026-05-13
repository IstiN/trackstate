from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliAttachmentStorageModeValidationConfig:
    ticket_command: str
    supported_ticket_command: str
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    unsupported_attachment_mode: str
    expected_provider: str
    expected_target_type: str
    expected_exit_code: int
    expected_reason_message: str
    expected_visible_reason_fragments: tuple[str, ...]
    disallowed_error_code: str
    disallowed_error_category: str
    disallowed_error_message_fragment: str

    @classmethod
    def from_file(
        cls,
        path: Path,
    ) -> "TrackStateCliAttachmentStorageModeValidationConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"TS-603 config must deserialize to a mapping: {path}")

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TS-603 config runtime_inputs must deserialize to a mapping: "
                f"{path}"
            )

        return cls(
            ticket_command=cls._require_string(runtime_inputs, "ticket_command", path),
            supported_ticket_command=cls._require_string(
                runtime_inputs,
                "supported_ticket_command",
                path,
            ),
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
            unsupported_attachment_mode=cls._require_string(
                runtime_inputs,
                "unsupported_attachment_mode",
                path,
            ),
            expected_provider=cls._require_string(
                runtime_inputs,
                "expected_provider",
                path,
            ),
            expected_target_type=cls._require_string(
                runtime_inputs,
                "expected_target_type",
                path,
            ),
            expected_exit_code=cls._require_int(
                runtime_inputs,
                "expected_exit_code",
                path,
            ),
            expected_reason_message=cls._require_string(
                runtime_inputs,
                "expected_reason_message",
                path,
            ),
            expected_visible_reason_fragments=cls._require_string_list(
                runtime_inputs,
                "expected_visible_reason_fragments",
                path,
            ),
            disallowed_error_code=cls._require_string(
                runtime_inputs,
                "disallowed_error_code",
                path,
            ),
            disallowed_error_category=cls._require_string(
                runtime_inputs,
                "disallowed_error_category",
                path,
            ),
            disallowed_error_message_fragment=cls._require_string(
                runtime_inputs,
                "disallowed_error_message_fragment",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"TS-603 config runtime_inputs.{key} must be a string in {path}.")
        return value

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, path: Path) -> int:
        value = payload.get(key)
        if isinstance(value, int):
            return value
        raise ValueError(f"TS-603 config runtime_inputs.{key} must be an integer in {path}.")

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(
                f"TS-603 config runtime_inputs.{key} must be a non-empty list in {path}."
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-603 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item)
        return tuple(items)
