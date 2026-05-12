from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliAttachmentUploadBoundaryRepositoryState:
    issue_main_exists: bool
    attachment_directory_exists: bool
    uploaded_attachment_paths: tuple[str, ...]
    issue_main_content: str | None
    git_status_lines: tuple[str, ...]
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliAttachmentUploadBoundaryValidationResult:
    initial_state: TrackStateCliAttachmentUploadBoundaryRepositoryState
    final_state: TrackStateCliAttachmentUploadBoundaryRepositoryState
    observation: TrackStateCliCommandObservation
