from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliAttachmentStorageModeValidationStoredFile:
    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class TrackStateCliAttachmentStorageModeValidationRepositoryState:
    issue_main_exists: bool
    source_file_exists: bool
    attachment_directory_exists: bool
    attachments_metadata_exists: bool
    stored_files: tuple[TrackStateCliAttachmentStorageModeValidationStoredFile, ...]
    git_status_lines: tuple[str, ...]
    head_commit_subject: str | None
    head_commit_count: int
    project_json_text: str | None


@dataclass(frozen=True)
class TrackStateCliAttachmentStorageModeValidationResult:
    initial_state: TrackStateCliAttachmentStorageModeValidationRepositoryState
    final_state: TrackStateCliAttachmentStorageModeValidationRepositoryState
    observation: TrackStateCliCommandObservation
