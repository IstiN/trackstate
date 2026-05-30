from __future__ import annotations

from testing.core.config.trackstate_cli_read_ticket_mixed_link_directions_config import (
    TrackStateCliReadTicketMixedLinkDirectionsConfig,
)
from testing.core.interfaces.trackstate_cli_read_ticket_mixed_link_directions_probe import (
    TrackStateCliReadTicketMixedLinkDirectionsProbe,
)
from testing.core.models.trackstate_cli_read_ticket_mixed_link_directions_result import (
    TrackStateCliReadTicketMixedLinkDirectionsValidationResult,
)


class TrackStateCliReadTicketMixedLinkDirectionsValidator:
    def __init__(
        self,
        probe: TrackStateCliReadTicketMixedLinkDirectionsProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReadTicketMixedLinkDirectionsConfig,
    ) -> TrackStateCliReadTicketMixedLinkDirectionsValidationResult:
        return self._probe.observe_read_ticket_mixed_link_directions(config=config)
