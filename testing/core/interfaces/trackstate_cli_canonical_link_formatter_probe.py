from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from testing.core.config.trackstate_cli_canonical_link_formatter_config import (
    TrackStateCliCanonicalLinkFormatterConfig,
)


@dataclass(frozen=True)
class TrackStateCliCanonicalLinkFormatterProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    run_stderr: str | None
    observation_payload: dict[str, object] | None


class TrackStateCliCanonicalLinkFormatterProbe(Protocol):
    def observe(
        self,
        *,
        config: TrackStateCliCanonicalLinkFormatterConfig,
    ) -> TrackStateCliCanonicalLinkFormatterProbeResult: ...
