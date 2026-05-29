from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityConflictRemoteState:
    project_json_text: str | None
    issue_main_exists: bool
    issue_main_content: str | None
    manifest_exists: bool
    manifest_text: str | None
    manifest_sha: str | None
    release_present: bool
    release_id: int | None
    release_name: str | None
    release_asset_names: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliReleaseIdentityConflictValidationResult:
    initial_state: TrackStateCliReleaseIdentityConflictRemoteState
    final_state: TrackStateCliReleaseIdentityConflictRemoteState
    observation: TrackStateCliCommandObservation
    setup_actions: tuple[str, ...]
    cleanup_actions: tuple[str, ...]
    cleanup_error: str | None
    local_attachment_path: str
