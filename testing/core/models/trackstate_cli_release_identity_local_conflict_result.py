from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityLocalConflictStoredFile:
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityLocalConflictRepositoryState:
    issue_main_exists: bool
    source_file_exists: bool
    attachment_directory_exists: bool
    expected_attachment_exists: bool
    stored_files: tuple[TrackStateCliReleaseIdentityLocalConflictStoredFile, ...]
    manifest_exists: bool
    manifest_text: str | None
    git_status_lines: tuple[str, ...]
    remote_names: tuple[str, ...]
    remote_origin_url: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityLocalConflictRemoteState:
    release_present: bool
    release_id: int | None
    release_name: str | None
    release_asset_names: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityLocalConflictValidationResult:
    initial_repository_state: TrackStateCliReleaseIdentityLocalConflictRepositoryState
    final_repository_state: TrackStateCliReleaseIdentityLocalConflictRepositoryState
    initial_remote_state: TrackStateCliReleaseIdentityLocalConflictRemoteState
    final_remote_state: TrackStateCliReleaseIdentityLocalConflictRemoteState
    observation: TrackStateCliCommandObservation
    setup_actions: tuple[str, ...]
    cleanup_actions: tuple[str, ...]
    cleanup_error: str | None
    local_attachment_path: str
