from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from testing.core.config.live_setup_test_config import load_live_setup_test_config


@dataclass(frozen=True)
class TrackStateCliReleaseReplacementConfig:
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
    expected_attachment_name: str
    release_tag_prefix_base: str
    seeded_attachment_text: str
    seeded_attachment_created_at: str
    attachment_media_type: str
    manifest_poll_timeout_seconds: int
    manifest_poll_interval_seconds: int
    release_poll_timeout_seconds: int
    release_poll_interval_seconds: int
    delete_release_asset_override_status_code: int | None
    delete_release_asset_override_body: str | None
    upload_release_asset_override_status_code: int | None
    upload_release_asset_override_body: str | None
    override_release_tag_lookup_without_assets: bool

    @property
    def issue_path(self) -> str:
        return f"{self.project_key}/{self.issue_key}"

    @property
    def issue_main_path(self) -> str:
        return f"{self.issue_path}/main.md"

    @property
    def manifest_path(self) -> str:
        return f"{self.issue_path}/attachments.json"

    @property
    def expected_attachment_relative_path(self) -> str:
        return f"{self.issue_path}/attachments/{self.expected_attachment_name}"

    @property
    def expected_release_title(self) -> str:
        return f"Attachments for {self.issue_key}"

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @property
    def seeded_attachment_bytes(self) -> bytes:
        return self.seeded_attachment_text.encode("utf-8")

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliReleaseReplacementConfig":
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(
                f"Release replacement config must deserialize to a mapping: {path}",
            )

        runtime_inputs = payload.get("runtime_inputs") or {}
        if not isinstance(runtime_inputs, dict):
            raise ValueError(
                "Release replacement config runtime_inputs must deserialize to a "
                f"mapping: {path}",
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
            expected_attachment_name=cls._require_string(
                runtime_inputs,
                "expected_attachment_name",
                path,
            ),
            release_tag_prefix_base=cls._require_string(
                runtime_inputs,
                "release_tag_prefix_base",
                path,
            ),
            seeded_attachment_text=cls._require_string(
                runtime_inputs,
                "seeded_attachment_text",
                path,
            ),
            seeded_attachment_created_at=cls._require_string(
                runtime_inputs,
                "seeded_attachment_created_at",
                path,
            ),
            attachment_media_type=cls._require_string(
                runtime_inputs,
                "attachment_media_type",
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
            delete_release_asset_override_status_code=cls._optional_int(
                runtime_inputs,
                "delete_release_asset_override_status_code",
                path,
            ),
            delete_release_asset_override_body=cls._optional_string(
                runtime_inputs,
                "delete_release_asset_override_body",
            ),
            upload_release_asset_override_status_code=cls._optional_int(
                runtime_inputs,
                "upload_release_asset_override_status_code",
                path,
            ),
            upload_release_asset_override_body=cls._optional_string(
                runtime_inputs,
                "upload_release_asset_override_body",
            ),
            override_release_tag_lookup_without_assets=cls._optional_bool(
                runtime_inputs,
                "override_release_tag_lookup_without_assets",
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
                f"Release replacement config runtime_inputs.{key} must be a string.",
            )
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _optional_int(payload: dict[str, Any], key: str, path: Path) -> int | None:
        value = payload.get(key)
        if value is None:
            return None
        if not isinstance(value, int):
            raise ValueError(
                "Release replacement config runtime_inputs."
                f"{key} must be an integer in {path}.",
            )
        return value

    @staticmethod
    def _optional_bool(payload: dict[str, Any], key: str, path: Path) -> bool:
        value = payload.get(key)
        if value is None:
            return False
        if not isinstance(value, bool):
            raise ValueError(
                "Release replacement config runtime_inputs."
                f"{key} must be a boolean in {path}.",
            )
        return value

    @staticmethod
    def _require_string(payload: dict[str, Any], key: str, path: Path) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(
                "Release replacement config runtime_inputs."
                f"{key} must be a string in {path}.",
            )
        return value

    @staticmethod
    def _require_int(payload: dict[str, Any], key: str, path: Path) -> int:
        value = payload.get(key)
        if not isinstance(value, int):
            raise ValueError(
                "Release replacement config runtime_inputs."
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
                "Release replacement config runtime_inputs."
                f"{key} must be a non-empty list in {path}.",
            )
        items: list[str] = []
        for index, item in enumerate(value):
            if not isinstance(item, str) or not item:
                raise ValueError(
                    "Release replacement config runtime_inputs."
                    f"{key}[{index}] must be a non-empty string in {path}.",
                )
            items.append(item)
        return tuple(items)
