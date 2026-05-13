from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)


@dataclass(frozen=True)
class TrackStateCliIssueLinkTypesValidationResult:
    ticket_observation: TrackStateCliCommandObservation
    canonical_observation: TrackStateCliCommandObservation
