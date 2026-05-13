from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliMixedAttachmentResolutionRepositoryState:
    issue_main_exists: bool
    manifest_exists: bool
    manifest_text: str | None
    legacy_attachment_exists: bool
    new_attachment_source_exists: bool
    project_json_text: str | None
    attachment_file_paths: tuple[str, ...]
    git_status_lines: tuple[str, ...]
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliMixedAttachmentResolutionDownloadObservation:
    command_observation: TrackStateCliCommandObservation
    saved_file_absolute_path: str
    saved_file_exists: bool
    saved_file_bytes: bytes | None


@dataclass(frozen=True)
class TrackStateCliMixedAttachmentResolutionValidationResult:
    initial_state: TrackStateCliMixedAttachmentResolutionRepositoryState
    post_upload_state: TrackStateCliMixedAttachmentResolutionRepositoryState
    upload_observation: TrackStateCliCommandObservation
    download_observation: TrackStateCliMixedAttachmentResolutionDownloadObservation
