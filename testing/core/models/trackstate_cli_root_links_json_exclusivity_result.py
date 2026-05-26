from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliRootLinksJsonSnapshot:
    relative_path: str
    content: str | None
    payload: object | None


@dataclass(frozen=True)
class TrackStateCliRootLinksJsonExclusivityObservation:
    issue_a_create_observation: TrackStateCliCommandObservation
    issue_b_create_observation: TrackStateCliCommandObservation
    link_observation: TrackStateCliCommandObservation
    root_links_json_relative_path: str
    root_links_json_content: str | None
    root_links_json_payload: object | None
    discovered_links_json_files: tuple[str, ...]
    discovered_links_json_snapshots: tuple[TrackStateCliRootLinksJsonSnapshot, ...]
    issue_a_directory_relative_path: str
    issue_a_directory_entries: tuple[str, ...]
    issue_a_main_relative_path: str
    issue_a_main_content: str | None
    issue_b_directory_relative_path: str
    issue_b_directory_entries: tuple[str, ...]
    issue_b_main_relative_path: str
    issue_b_main_content: str | None


@dataclass(frozen=True)
class TrackStateCliRootLinksJsonExclusivityValidationResult:
    observation: TrackStateCliRootLinksJsonExclusivityObservation
