from __future__ import annotations

from testing.core.config.trackstate_cli_ticket_show_help_config import (
    TrackStateCliTicketShowHelpConfig,
)
from testing.core.interfaces.trackstate_cli_ticket_show_help_probe import (
    TrackStateCliTicketShowHelpProbe,
)
from testing.core.models.trackstate_cli_ticket_show_help_result import (
    TrackStateCliTicketShowHelpValidationResult,
)


class TrackStateCliTicketShowHelpValidator:
    def __init__(self, probe: TrackStateCliTicketShowHelpProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliTicketShowHelpConfig,
    ) -> TrackStateCliTicketShowHelpValidationResult:
        return self._probe.observe_ticket_help(config=config)
