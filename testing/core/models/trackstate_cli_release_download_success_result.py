from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseDownloadSuccessFixture:
    repository: str
    repository_ref: str
    remote_origin_url: str
    tag_name: str
    title: str
    asset_name: str
    asset_id: int
    asset_bytes: bytes
    release_id: int


@dataclass(frozen=True)
class TrackStateCliReleaseDownloadSuccessRepositoryState:
    issue_main_exists: bool
    attachments_metadata_exists: bool
    metadata_attachment_ids: tuple[str, ...]
    metadata_storage_backends: tuple[str, ...]
    metadata_release_tags: tuple[str, ...]
    metadata_release_asset_names: tuple[str, ...]
    expected_output_exists: bool
    expected_output_size_bytes: int | None
    downloads_directory_exists: bool
    git_status_lines: tuple[str, ...]
    remote_origin_url: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseDownloadSuccessValidationResult:
    initial_state: TrackStateCliReleaseDownloadSuccessRepositoryState
    final_state: TrackStateCliReleaseDownloadSuccessRepositoryState
    observation: TrackStateCliCommandObservation
    saved_file_absolute_path: str
    saved_file_bytes: bytes | None
    stripped_environment_variables: tuple[str, ...]
