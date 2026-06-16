from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_ticket_show_help_config import (
    TrackStateCliTicketShowHelpConfig,
)
from testing.core.models.trackstate_cli_ticket_show_help_result import (
    TrackStateCliTicketShowHelpValidationResult,
)


class TrackStateCliTicketShowHelpProbe(Protocol):
    def observe_ticket_help(
        self,
        *,
        config: TrackStateCliTicketShowHelpConfig,
    ) -> TrackStateCliTicketShowHelpValidationResult: ...
