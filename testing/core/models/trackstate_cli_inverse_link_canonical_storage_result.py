from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliLinksJsonSnapshot:
    relative_path: str
    content: str | None
    payload: object | None


@dataclass(frozen=True)
class TrackStateCliInverseLinkCanonicalStorageObservation:
    issue_a_create_observation: TrackStateCliCommandObservation
    issue_b_create_observation: TrackStateCliCommandObservation
    inverse_link_observation: TrackStateCliCommandObservation
    source_links_json_relative_path: str
    source_links_json_content: str | None
    source_links_json_payload: object | None
    target_links_json_relative_path: str
    target_links_json_content: str | None
    target_links_json_payload: object | None
    discovered_links_json_files: tuple[str, ...]
    discovered_links_json_snapshots: tuple[TrackStateCliLinksJsonSnapshot, ...]


@dataclass(frozen=True)
class TrackStateCliInverseLinkCanonicalStorageValidationResult:
    observation: TrackStateCliInverseLinkCanonicalStorageObservation
