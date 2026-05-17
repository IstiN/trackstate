from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliInvalidLinkTypeObservation:
    issue_a_create_observation: TrackStateCliCommandObservation
    issue_b_create_observation: TrackStateCliCommandObservation
    invalid_link_observation: TrackStateCliCommandObservation
    discovered_links_json_files: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliInvalidLinkTypeValidationResult:
    observation: TrackStateCliInvalidLinkTypeObservation
