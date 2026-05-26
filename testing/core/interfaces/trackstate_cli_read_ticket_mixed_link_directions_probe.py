from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_read_ticket_mixed_link_directions_config import (
    TrackStateCliReadTicketMixedLinkDirectionsConfig,
)
from testing.core.models.trackstate_cli_read_ticket_mixed_link_directions_result import (
    TrackStateCliReadTicketMixedLinkDirectionsValidationResult,
)


class TrackStateCliReadTicketMixedLinkDirectionsProbe(Protocol):
    def observe_read_ticket_mixed_link_directions(
        self,
        *,
        config: TrackStateCliReadTicketMixedLinkDirectionsConfig,
    ) -> TrackStateCliReadTicketMixedLinkDirectionsValidationResult: ...
