from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityMissingRemoteConfig:
    ticket_command: str
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    source_file_name: str
    source_file_text: str
    attachment_tag_prefix: str
    expected_attachment_relative_path: str
    expected_identity_fragments: tuple[str, ...]
    generic_release_auth_fragments: tuple[str, ...]

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @classmethod
    def from_file(
        cls, path: Path
    ) -> "TrackStateCliReleaseIdentityMissingRemoteConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "Release identity missing-remote config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "Release identity missing-remote config runtime_inputs must deserialize "
                f"to a mapping: {path}"
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
            expected_attachment_relative_path=cls._require_string(
                runtime_inputs,
                "expected_attachment_relative_path",
                path,
            ),
            expected_identity_fragments=cls._require_lower_string_list(
                runtime_inputs,
                "expected_identity_fragments",
                path,
            ),
            generic_release_auth_fragments=cls._optional_lower_string_list(
                runtime_inputs,
                "generic_release_auth_fragments",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                "Release identity missing-remote config runtime_inputs."
                f"{key} must be a string in {path}."
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
                "Release identity missing-remote config runtime_inputs."
                f"{key} must be a non-empty list in {path}."
            )
        items = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "Release identity missing-remote config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
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
            item.lower() for item in TrackStateCliReleaseIdentityMissingRemoteConfig._require_string_list(
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
                "Release identity missing-remote config runtime_inputs."
                f"{key} must be a list in {path}."
            )
        items = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "Release identity missing-remote config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item.lower())
        return tuple(items)
