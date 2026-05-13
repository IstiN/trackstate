from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseDownloadIdentityMissingRemoteRepositoryState:
    issue_main_exists: bool
    attachments_metadata_exists: bool
    metadata_attachment_ids: tuple[str, ...]
    expected_output_exists: bool
    expected_output_size_bytes: int | None
    downloads_directory_exists: bool
    git_status_lines: tuple[str, ...]
    remote_names: tuple[str, ...]
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseDownloadIdentityMissingRemoteValidationResult:
    initial_state: TrackStateCliReleaseDownloadIdentityMissingRemoteRepositoryState
    final_state: TrackStateCliReleaseDownloadIdentityMissingRemoteRepositoryState
    observation: TrackStateCliCommandObservation
    stripped_environment_variables: tuple[str, ...]
