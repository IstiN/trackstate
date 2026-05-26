from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseAssetFilenameSanitizationStoredFile:
    relative_path: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class TrackStateCliReleaseAssetFilenameSanitizationRepositoryState:
    issue_main_exists: bool
    source_file_exists: bool
    manifest_exists: bool
    manifest_text: str | None
    attachments_directory_exists: bool
    stored_files: tuple[TrackStateCliReleaseAssetFilenameSanitizationStoredFile, ...]
    git_status_lines: tuple[str, ...]
    remote_origin_url: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseAssetFilenameSanitizationManifestObservation:
    manifest_exists: bool
    manifest_text: str | None
    matching_entry: dict[str, object] | None
    raw_asset_names: tuple[str, ...]
    matches_expected: bool


@dataclass(frozen=True)
class TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation:
    release_present: bool
    release_id: int | None
    release_tag: str | None
    release_name: str | None
    release_draft: bool | None
    asset_names: tuple[str, ...]
    asset_ids: tuple[int, ...]
    downloaded_asset_sha256: str | None
    downloaded_asset_size_bytes: int | None
    download_error: str | None
    matches_expected: bool


@dataclass(frozen=True)
class TrackStateCliReleaseAssetFilenameSanitizationGhReleaseViewObservation:
    exit_code: int
    stdout: str
    stderr: str
    json_payload: object | None
    asset_names: tuple[str, ...]
    matches_expected: bool


@dataclass(frozen=True)
class TrackStateCliReleaseAssetFilenameSanitizationCleanupResult:
    status: str
    release_tag: str | None
    deleted_asset_names: tuple[str, ...]
    error: str | None = None


@dataclass(frozen=True)
class TrackStateCliReleaseAssetFilenameSanitizationValidationResult:
    initial_state: TrackStateCliReleaseAssetFilenameSanitizationRepositoryState
    final_state: TrackStateCliReleaseAssetFilenameSanitizationRepositoryState
    observation: TrackStateCliCommandObservation
    expected_release_tag: str
    release_tag_prefix: str
    remote_origin_url: str
    manifest_observation: (
        TrackStateCliReleaseAssetFilenameSanitizationManifestObservation | None
    )
    release_observation: (
        TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation | None
    )
    gh_release_view: (
        TrackStateCliReleaseAssetFilenameSanitizationGhReleaseViewObservation | None
    )
    cleanup: TrackStateCliReleaseAssetFilenameSanitizationCleanupResult
