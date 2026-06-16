from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from testing.core.config.trackstate_cli_nonblocking_link_formatter_warning_config import (
    TrackStateCliNonblockingLinkFormatterWarningConfig,
)


@dataclass(frozen=True)
class TrackStateCliNonblockingLinkFormatterWarningProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    run_stderr: str | None
    observation_payload: dict[str, object] | None


class TrackStateCliNonblockingLinkFormatterWarningProbe(Protocol):
    def observe(
        self,
        *,
        config: TrackStateCliNonblockingLinkFormatterWarningConfig,
    ) -> TrackStateCliNonblockingLinkFormatterWarningProbeResult: ...
