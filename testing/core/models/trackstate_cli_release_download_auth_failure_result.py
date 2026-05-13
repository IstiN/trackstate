from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseDownloadAuthFailureRepositoryState:
    issue_main_exists: bool
    attachments_metadata_exists: bool
    metadata_attachment_ids: tuple[str, ...]
    expected_output_exists: bool
    expected_output_size_bytes: int | None
    downloads_directory_exists: bool
    git_status_lines: tuple[str, ...]
    remote_origin_url: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseDownloadAuthFailureValidationResult:
    initial_state: TrackStateCliReleaseDownloadAuthFailureRepositoryState
    final_state: TrackStateCliReleaseDownloadAuthFailureRepositoryState
    observation: TrackStateCliCommandObservation
    stripped_environment_variables: tuple[str, ...]
