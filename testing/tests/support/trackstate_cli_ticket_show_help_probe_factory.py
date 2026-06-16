from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_ticket_show_help_probe import (
    TrackStateCliTicketShowHelpProbe,
)
from testing.frameworks.python.trackstate_cli_ticket_show_help_framework import (
    PythonTrackStateCliTicketShowHelpFramework,
)


def create_trackstate_cli_ticket_show_help_probe(
    repository_root: Path,
) -> TrackStateCliTicketShowHelpProbe:
    return PythonTrackStateCliTicketShowHelpFramework(repository_root)
