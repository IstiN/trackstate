from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliHostedLfsRestrictionRemoteState:
    zip_lfs_rule_present: bool
    zip_lfs_rule_line: str | None
    present_fixture_paths: tuple[str, ...]
    issue_main_exists: bool
    issue_main_content: str | None
    attachment_exists: bool
    attachment_sha: str | None


@dataclass(frozen=True)
class TrackStateCliHostedLfsRestrictionValidationResult:
    initial_state: TrackStateCliHostedLfsRestrictionRemoteState
    final_state: TrackStateCliHostedLfsRestrictionRemoteState
    observation: TrackStateCliCommandObservation
    setup_actions: tuple[str, ...]
    cleanup_actions: tuple[str, ...]
    cleanup_error: str | None
    local_attachment_path: str
