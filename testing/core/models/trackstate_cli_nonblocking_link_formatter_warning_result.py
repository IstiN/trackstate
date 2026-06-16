from __future__ import annotations

from dataclasses import dataclass

from testing.core.interfaces.trackstate_cli_nonblocking_link_formatter_warning_probe import (
    TrackStateCliNonblockingLinkFormatterWarningProbeResult,
)


@dataclass(frozen=True)
class TrackStateCliNonblockingLinkFormatterWarningValidationResult:
    observation: TrackStateCliNonblockingLinkFormatterWarningProbeResult
