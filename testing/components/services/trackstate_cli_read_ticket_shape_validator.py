from __future__ import annotations

from testing.core.config.trackstate_cli_read_ticket_shape_config import (
    TrackStateCliReadTicketShapeConfig,
)
from testing.core.interfaces.trackstate_cli_read_ticket_shape_probe import (
    TrackStateCliReadTicketShapeProbe,
)
from testing.core.models.trackstate_cli_read_ticket_shape_result import (
    TrackStateCliReadTicketShapeValidationResult,
)


class TrackStateCliReadTicketShapeValidator:
    def __init__(self, probe: TrackStateCliReadTicketShapeProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReadTicketShapeConfig,
    ) -> TrackStateCliReadTicketShapeValidationResult:
        return self._probe.observe_read_ticket_shape(config=config)
