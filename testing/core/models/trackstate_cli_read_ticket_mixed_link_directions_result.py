from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliReadTicketMixedLinkDirectionsObservation:
    issue_a_create_observation: TrackStateCliCommandObservation
    issue_b_create_observation: TrackStateCliCommandObservation
    issue_c_create_observation: TrackStateCliCommandObservation
    inward_relates_link_observation: TrackStateCliCommandObservation
    outward_blocks_link_observation: TrackStateCliCommandObservation
    read_ticket_observation: TrackStateCliCommandObservation


@dataclass(frozen=True)
class TrackStateCliReadTicketMixedLinkDirectionsValidationResult:
    observation: TrackStateCliReadTicketMixedLinkDirectionsObservation
