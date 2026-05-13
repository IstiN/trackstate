from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliLinksJsonHierarchyExclusionObservation:
    parent_create_observation: TrackStateCliCommandObservation
    child_create_observation: TrackStateCliCommandObservation
    unrelated_source_create_observation: TrackStateCliCommandObservation
    unrelated_target_create_observation: TrackStateCliCommandObservation
    link_observation: TrackStateCliCommandObservation
    links_json_relative_path: str
    links_json_files: tuple[str, ...]
    links_json_content: str | None
    links_json_payload: object | None
    child_main_relative_path: str
    child_main_content: str | None
    issue_index_relative_path: str
    issue_index_content: str | None
    issue_index_payload: object | None


@dataclass(frozen=True)
class TrackStateCliLinksJsonHierarchyExclusionValidationResult:
    observation: TrackStateCliLinksJsonHierarchyExclusionObservation
