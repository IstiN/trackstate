from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.trackstate_cli_read_ticket_shape_probe import (
    TrackStateCliReadTicketShapeProbe,
)
from testing.frameworks.python.trackstate_cli_read_ticket_shape_framework import (
    PythonTrackStateCliReadTicketShapeFramework,
)


def create_trackstate_cli_read_ticket_shape_probe(
    repository_root: Path,
) -> TrackStateCliReadTicketShapeProbe:
    return PythonTrackStateCliReadTicketShapeFramework(repository_root)
