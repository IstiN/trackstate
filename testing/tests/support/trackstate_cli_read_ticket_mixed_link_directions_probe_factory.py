from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_read_ticket_mixed_link_directions_probe import (
    TrackStateCliReadTicketMixedLinkDirectionsProbe,
)
from testing.frameworks.python.trackstate_cli_read_ticket_mixed_link_directions_framework import (
    PythonTrackStateCliReadTicketMixedLinkDirectionsFramework,
)


def create_trackstate_cli_read_ticket_mixed_link_directions_probe(
    repository_root: Path,
) -> TrackStateCliReadTicketMixedLinkDirectionsProbe:
    return PythonTrackStateCliReadTicketMixedLinkDirectionsFramework(repository_root)
