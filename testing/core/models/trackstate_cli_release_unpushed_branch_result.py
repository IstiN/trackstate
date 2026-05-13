from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseUnpushedBranchStoredFile:
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class TrackStateCliReleaseUnpushedBranchRepositoryState:
    issue_main_exists: bool
    source_file_exists: bool
    attachment_directory_exists: bool
    expected_attachment_exists: bool
    stored_files: tuple[TrackStateCliReleaseUnpushedBranchStoredFile, ...]
    manifest_exists: bool
    manifest_text: str | None
    git_status_lines: tuple[str, ...]
    remote_names: tuple[str, ...]
    remote_origin_url: str | None
    current_branch: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseUnpushedBranchRemoteState:
    branch_exists_on_remote: bool
    release_count: int
    release_ids: tuple[int, ...]
    release_names: tuple[str, ...]
    release_asset_names: tuple[str, ...]
    matching_tag_refs: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliReleaseUnpushedBranchValidationResult:
    initial_repository_state: TrackStateCliReleaseUnpushedBranchRepositoryState
    final_repository_state: TrackStateCliReleaseUnpushedBranchRepositoryState
    initial_remote_state: TrackStateCliReleaseUnpushedBranchRemoteState
    final_remote_state: TrackStateCliReleaseUnpushedBranchRemoteState
    observation: TrackStateCliCommandObservation
    setup_actions: tuple[str, ...]
    pre_run_cleanup_actions: tuple[str, ...]
    cleanup_actions: tuple[str, ...]
    cleanup_error: str | None
