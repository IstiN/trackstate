from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliSymmetricLinkShowObservation:
    issue_a_create_observation: TrackStateCliCommandObservation
    issue_b_create_observation: TrackStateCliCommandObservation
    relates_to_link_observation: TrackStateCliCommandObservation
    ticket_show_observation: TrackStateCliCommandObservation
    read_ticket_observation: TrackStateCliCommandObservation


@dataclass(frozen=True)
class TrackStateCliSymmetricLinkShowValidationResult:
    observation: TrackStateCliSymmetricLinkShowObservation
