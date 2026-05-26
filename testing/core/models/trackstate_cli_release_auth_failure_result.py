from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseAuthFailureStoredFile:
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class TrackStateCliReleaseAuthFailureRepositoryState:
    issue_main_exists: bool
    attachment_directory_exists: bool
    expected_attachment_exists: bool
    stored_files: tuple[TrackStateCliReleaseAuthFailureStoredFile, ...]
    git_status_lines: tuple[str, ...]
    remote_origin_url: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseAuthFailureValidationResult:
    initial_state: TrackStateCliReleaseAuthFailureRepositoryState
    final_state: TrackStateCliReleaseAuthFailureRepositoryState
    observation: TrackStateCliCommandObservation
    stripped_environment_variables: tuple[str, ...]
