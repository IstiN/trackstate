from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliLocalAttachmentUploadStoredFile:
    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class TrackStateCliLocalAttachmentUploadRepositoryState:
    issue_main_exists: bool
    attachment_directory_exists: bool
    stored_files: tuple[TrackStateCliLocalAttachmentUploadStoredFile, ...]
    git_status_lines: tuple[str, ...]
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliLocalAttachmentUploadValidationResult:
    initial_state: TrackStateCliLocalAttachmentUploadRepositoryState
    final_state: TrackStateCliLocalAttachmentUploadRepositoryState
    observation: TrackStateCliCommandObservation
