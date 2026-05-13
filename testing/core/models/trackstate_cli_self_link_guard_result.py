from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliSelfLinkLinksJsonSnapshot:
    relative_path: str
    content: str | None
    payload: object | None


@dataclass(frozen=True)
class TrackStateCliSelfLinkGuardObservation:
    issue_a_create_observation: TrackStateCliCommandObservation
    self_link_observation: TrackStateCliCommandObservation
    links_json_relative_path: str
    links_json_content: str | None
    links_json_payload: object | None
    discovered_links_json_files: tuple[str, ...]
    discovered_links_json_snapshots: tuple[TrackStateCliSelfLinkLinksJsonSnapshot, ...]


@dataclass(frozen=True)
class TrackStateCliSelfLinkGuardValidationResult:
    observation: TrackStateCliSelfLinkGuardObservation
