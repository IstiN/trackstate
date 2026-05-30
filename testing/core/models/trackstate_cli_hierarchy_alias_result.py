from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliHierarchyAliasObservation:
    create_observation: TrackStateCliCommandObservation
    update_observation: TrackStateCliCommandObservation
    created_issue_relative_path: str | None
    created_issue_content: str | None
    original_subtask_relative_path: str
    original_subtask_exists_after_update: bool
    updated_subtask_relative_path: str
    updated_subtask_exists_after_update: bool
    updated_subtask_content: str | None
    final_git_status: str


@dataclass(frozen=True)
class TrackStateCliHierarchyAliasValidationResult:
    observation: TrackStateCliHierarchyAliasObservation
