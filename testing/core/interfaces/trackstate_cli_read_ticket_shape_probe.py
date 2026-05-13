from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_read_ticket_shape_config import (
    TrackStateCliReadTicketShapeConfig,
)
from testing.core.models.trackstate_cli_read_ticket_shape_result import (
    TrackStateCliReadTicketShapeValidationResult,
)


class TrackStateCliReadTicketShapeProbe(Protocol):
    def observe_read_ticket_shape(
        self,
        *,
        config: TrackStateCliReadTicketShapeConfig,
    ) -> TrackStateCliReadTicketShapeValidationResult: ...
