from __future__ import annotations

from dataclasses import dataclass

from testing.core.interfaces.trackstate_cli_link_formatter_warning_probe import (
    TrackStateCliLinkFormatterWarningProbeResult,
)


@dataclass(frozen=True)
class TrackStateCliLinkFormatterWarningValidationResult:
    observation: TrackStateCliLinkFormatterWarningProbeResult
