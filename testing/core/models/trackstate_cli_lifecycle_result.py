from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliLifecycleRepositoryState:
    deleted_issue_directory_exists: bool
    deleted_issue_main_exists: bool
    deleted_issue_archive_main_exists: bool
    archived_issue_directory_exists: bool
    archived_issue_main_exists: bool
    archived_issue_main_content: str | None
    archived_issue_archive_main_exists: bool
    archived_issue_archive_main_content: str | None
    tombstone_index_exists: bool
    tombstone_index_text: str | None
    tombstone_index_payload: object | None
    deleted_issue_tombstone_exists: bool
    deleted_issue_tombstone_text: str | None
    deleted_issue_tombstone_payload: object | None
    archived_issue_tombstone_exists: bool
    archived_issue_tombstone_text: str | None
    archived_issue_tombstone_payload: object | None


@dataclass(frozen=True)
class TrackStateCliLifecycleValidationResult:
    initial_state: TrackStateCliLifecycleRepositoryState
    after_delete_state: TrackStateCliLifecycleRepositoryState
    after_archive_state: TrackStateCliLifecycleRepositoryState
    delete_observation: TrackStateCliCommandObservation
    archive_observation: TrackStateCliCommandObservation
