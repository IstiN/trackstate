from __future__ import annotations

from dataclasses import dataclass

from testing.core.interfaces.trackstate_cli_canonical_link_formatter_probe import (
    TrackStateCliCanonicalLinkFormatterProbeResult,
)


@dataclass(frozen=True)
class TrackStateCliCanonicalLinkFormatterValidationResult:
    observation: TrackStateCliCanonicalLinkFormatterProbeResult
