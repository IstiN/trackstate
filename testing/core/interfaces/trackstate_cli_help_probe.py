from __future__ import annotations

from typing import Protocol

from testing.core.models.trackstate_cli_help_result import TrackStateCliHelpObservation


class TrackStateCliHelpProbe(Protocol):
    def root_help(self) -> TrackStateCliHelpObservation: ...

    def session_help(self) -> TrackStateCliHelpObservation: ...
