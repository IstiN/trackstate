from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseExistingTagStoredFile:
    relative_path: str
    size_bytes: int


@dataclass(frozen=True)
class TrackStateCliReleaseExistingTagRepositoryState:
    issue_main_exists: bool
    attachments_metadata_exists: bool
    attachments_metadata_text: str | None
    matching_attachment_entries: tuple[dict[str, object], ...]
    metadata_attachment_ids: tuple[str, ...]
    metadata_storage_backends: tuple[str, ...]
    metadata_release_tags: tuple[str, ...]
    metadata_release_asset_names: tuple[str, ...]
    attachment_directory_exists: bool
    expected_attachment_exists: bool
    stored_files: tuple[TrackStateCliReleaseExistingTagStoredFile, ...]
    git_status_lines: tuple[str, ...]
    remote_origin_url: str | None
    head_commit_subject: str | None
    head_commit_count: int


@dataclass(frozen=True)
class TrackStateCliReleaseExistingTagValidationResult:
    initial_state: TrackStateCliReleaseExistingTagRepositoryState
    final_state: TrackStateCliReleaseExistingTagRepositoryState
    observation: TrackStateCliCommandObservation
    stripped_environment_variables: tuple[str, ...]
