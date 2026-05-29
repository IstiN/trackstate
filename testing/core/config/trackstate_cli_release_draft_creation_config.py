from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from testing.core.config.trackstate_cli_release_asset_filename_sanitization_config import (
    TrackStateCliReleaseAssetFilenameSanitizationConfig,
)


@dataclass(frozen=True)
class TrackStateCliReleaseDraftCreationConfig:
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
    release_tag_prefix_base: str
    expected_asset_name: str
    manifest_poll_timeout_seconds: int
    manifest_poll_interval_seconds: int
    release_poll_timeout_seconds: int
    release_poll_interval_seconds: int

    @property
    def source_file_bytes(self) -> bytes:
        return self.source_file_text.encode("utf-8")

    @property
    def manifest_path(self) -> str:
        return f"{self.project_key}/{self.issue_key}/attachments.json"

    @property
    def expected_sanitized_asset_name(self) -> str:
        return self.expected_asset_name

    @classmethod
    def from_file(cls, path: Path) -> "TrackStateCliReleaseDraftCreationConfig":
        legacy = TrackStateCliReleaseAssetFilenameSanitizationConfig.from_file(path)
        return cls(
            ticket_command=legacy.ticket_command,
            requested_command=legacy.requested_command,
            repository=legacy.repository,
            branch=legacy.branch,
            project_key=legacy.project_key,
            project_name=legacy.project_name,
            issue_key=legacy.issue_key,
            issue_summary=legacy.issue_summary,
            source_file_name=legacy.source_file_name,
            source_file_text=legacy.source_file_text,
            release_tag_prefix_base=legacy.release_tag_prefix_base,
            expected_asset_name=legacy.expected_sanitized_asset_name,
            manifest_poll_timeout_seconds=legacy.manifest_poll_timeout_seconds,
            manifest_poll_interval_seconds=legacy.manifest_poll_interval_seconds,
            release_poll_timeout_seconds=legacy.release_poll_timeout_seconds,
            release_poll_interval_seconds=legacy.release_poll_interval_seconds,
        )
