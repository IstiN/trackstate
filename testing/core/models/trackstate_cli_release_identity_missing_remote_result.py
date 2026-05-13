from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityMissingRemoteStoredFile:
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityMissingRemoteRepositoryState:
    issue_main_exists: bool
    attachment_directory_exists: bool
    expected_attachment_exists: bool
    stored_files: tuple[TrackStateCliReleaseIdentityMissingRemoteStoredFile, ...]
    git_status_lines: tuple[str, ...]
    remote_names: tuple[str, ...]
    remote_origin_url: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityMissingRemoteValidationResult:
    initial_state: TrackStateCliReleaseIdentityMissingRemoteRepositoryState
    final_state: TrackStateCliReleaseIdentityMissingRemoteRepositoryState
    observation: TrackStateCliCommandObservation
    stripped_environment_variables: tuple[str, ...]
