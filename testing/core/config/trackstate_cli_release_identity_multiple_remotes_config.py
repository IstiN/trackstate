from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityMultipleRemotesConfig:
    ticket_command: str
    supported_ticket_command: str
    requested_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    attachment_name: str
    attachment_relative_path: str
    attachment_media_type: str
    attachment_size_bytes: int
    attachment_revision_or_oid: str
    attachment_created_at: str
    attachment_author: str
    attachment_tag_prefix: str
    attachment_release_tag: str
    attachment_release_asset_name: str
    origin_remote_name: str
    origin_remote_url: str
    upstream_remote_name: str
    upstream_remote_url: str
    output_file_argument: str
    expected_output_relative_path: str
    expected_download_sha256: str
    expected_download_size_bytes: int
    expected_output_fragments: tuple[str, ...]
    provider_capability_fragments: tuple[str, ...]

    @classmethod
    def from_file(
        cls,
        path: Path,
    ) -> "TrackStateCliReleaseIdentityMultipleRemotesConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                "TS-542 config must deserialize to a mapping: "
                f"{path}"
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "TS-542 config runtime_inputs must deserialize to a mapping: "
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
            attachment_name=cls._require_string(
                runtime_inputs,
                "attachment_name",
                path,
            ),
            attachment_relative_path=cls._require_string(
                runtime_inputs,
                "attachment_relative_path",
                path,
            ),
            attachment_media_type=cls._require_string(
                runtime_inputs,
                "attachment_media_type",
                path,
            ),
            attachment_size_bytes=cls._require_int(
                runtime_inputs,
                "attachment_size_bytes",
                path,
            ),
            attachment_revision_or_oid=cls._require_string(
                runtime_inputs,
                "attachment_revision_or_oid",
                path,
            ),
            attachment_created_at=cls._require_string(
                runtime_inputs,
                "attachment_created_at",
                path,
            ),
            attachment_author=cls._require_string(
                runtime_inputs,
                "attachment_author",
                path,
            ),
            attachment_tag_prefix=cls._require_string(
                runtime_inputs,
                "attachment_tag_prefix",
                path,
            ),
            attachment_release_tag=cls._require_string(
                runtime_inputs,
                "attachment_release_tag",
                path,
            ),
            attachment_release_asset_name=cls._require_string(
                runtime_inputs,
                "attachment_release_asset_name",
                path,
            ),
            origin_remote_name=cls._require_string(
                runtime_inputs,
                "origin_remote_name",
                path,
            ),
            origin_remote_url=cls._require_string(
                runtime_inputs,
                "origin_remote_url",
                path,
            ),
            upstream_remote_name=cls._require_string(
                runtime_inputs,
                "upstream_remote_name",
                path,
            ),
            upstream_remote_url=cls._require_string(
                runtime_inputs,
                "upstream_remote_url",
                path,
            ),
            output_file_argument=cls._require_string(
                runtime_inputs,
                "output_file_argument",
                path,
            ),
            expected_output_relative_path=cls._require_string(
                runtime_inputs,
                "expected_output_relative_path",
                path,
            ),
            expected_download_sha256=cls._require_string(
                runtime_inputs,
                "expected_download_sha256",
                path,
            ),
            expected_download_size_bytes=cls._require_int(
                runtime_inputs,
                "expected_download_size_bytes",
                path,
            ),
            expected_output_fragments=cls._require_lower_string_list(
                runtime_inputs,
                "expected_output_fragments",
                path,
            ),
            provider_capability_fragments=cls._optional_lower_string_list(
                runtime_inputs,
                "provider_capability_fragments",
                path,
            ),
        )

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"TS-542 config runtime_inputs.{key} must be a string in {path}."
            )
        return value

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, path: Path) -> int:
        value = payload.get(key)
        if isinstance(value, int):
            return value
        raise ValueError(
            f"TS-542 config runtime_inputs.{key} must be an integer in {path}."
        )

    @staticmethod
    def _require_string_list(
        payload: dict[str, Any],
        key: str,
        path: Path,
    ) -> tuple[str, ...]:
        value = payload.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(
                f"TS-542 config runtime_inputs.{key} must be a non-empty list in {path}."
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-542 config runtime_inputs."
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
            item.lower()
            for item in TrackStateCliReleaseIdentityMultipleRemotesConfig._require_string_list(
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
                f"TS-542 config runtime_inputs.{key} must be a list in {path}."
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "TS-542 config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}."
                )
            items.append(item.lower())
        return tuple(items)
