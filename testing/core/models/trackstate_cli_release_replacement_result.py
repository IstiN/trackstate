from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseReplacementSeededRelease:
    release_id: int
    release_tag: str
    release_name: str
    asset_id: int
    asset_name: str


@dataclass(frozen=True)
class TrackStateCliReleaseReplacementRepositoryState:
    issue_main_exists: bool
    source_file_exists: bool
    manifest_exists: bool
    manifest_text: str | None
    matching_manifest_entries: tuple[dict[str, object], ...]
    release_present: bool
    release_id: int | None
    release_tag: str | None
    release_title: str | None
    release_asset_names: tuple[str, ...]
    release_asset_ids: tuple[int, ...]
    release_asset_downloaded_id: int | None
    release_asset_downloaded_size_bytes: int | None
    release_asset_downloaded_sha256: str | None
    release_asset_download_error: str | None
    remote_origin_url: str | None
    git_status_lines: tuple[str, ...]
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseReplacementManifestObservation:
    manifest_exists: bool
    manifest_text: str | None
    matching_entry: dict[str, object] | None
    entry_count: int
    matches_expected: bool


@dataclass(frozen=True)
class TrackStateCliReleaseReplacementReleaseObservation:
    release_present: bool
    release_id: int | None
    release_tag: str | None
    release_name: str | None
    asset_names: tuple[str, ...]
    asset_ids: tuple[int, ...]
    downloaded_asset_sha256: str | None
    downloaded_asset_size_bytes: int | None
    download_error: str | None
    matches_expected: bool


@dataclass(frozen=True)
class TrackStateCliReleaseReplacementCleanupResult:
    status: str
    release_tag: str | None
    deleted_release_ids: tuple[int, ...]
    deleted_asset_ids: tuple[int, ...]
    error: str | None = None


@dataclass(frozen=True)
class TrackStateCliReleaseReplacementValidationResult:
    seeded_release: TrackStateCliReleaseReplacementSeededRelease
    initial_state: TrackStateCliReleaseReplacementRepositoryState
    final_state: TrackStateCliReleaseReplacementRepositoryState
    observation: TrackStateCliCommandObservation
    expected_release_tag: str
    release_tag_prefix: str
    remote_origin_url: str
    manifest_observation: TrackStateCliReleaseReplacementManifestObservation | None
    release_observation: TrackStateCliReleaseReplacementReleaseObservation | None
    cleanup: TrackStateCliReleaseReplacementCleanupResult
