from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseForeignAssetConflictRepositoryState:
    issue_main_exists: bool
    manifest_exists: bool
    manifest_text: str | None
    attachments_directory_exists: bool
    stored_files: tuple[str, ...]
    source_file_exists: bool
    git_status_lines: tuple[str, ...]
    remote_names: tuple[str, ...]
    remote_origin_url: str | None


@dataclass(frozen=True)
class TrackStateCliReleaseForeignAssetConflictReleaseState:
    release_tag: str | None
    release_title: str | None
    release_asset_names: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation:
    exit_code: int
    stdout: str
    stderr: str
    payload: object | None
    asset_names: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliReleaseForeignAssetConflictCleanupResult:
    status: str
    release_tag: str
    deleted_assets: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True)
class TrackStateCliReleaseForeignAssetConflictValidationResult:
    initial_state: TrackStateCliReleaseForeignAssetConflictRepositoryState
    fixture_release_state: TrackStateCliReleaseForeignAssetConflictReleaseState
    preflight_gh_release_view: TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation
    observation: TrackStateCliCommandObservation
    final_state: TrackStateCliReleaseForeignAssetConflictRepositoryState
    remote_state_after_command: TrackStateCliReleaseForeignAssetConflictReleaseState
    gh_release_view: TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation
    cleanup: TrackStateCliReleaseForeignAssetConflictCleanupResult
    release_tag_prefix: str
    release_tag: str
    remote_origin_url: str
