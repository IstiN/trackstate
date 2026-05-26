from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from testing.core.config.trackstate_cli_link_formatter_warning_config import (
    TrackStateCliLinkFormatterWarningConfig,
)


@dataclass(frozen=True)
class TrackStateCliLinkFormatterWarningProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    run_stderr: str | None
    observation_payload: dict[str, object] | None


class TrackStateCliLinkFormatterWarningProbe(Protocol):
    def observe(
        self,
        *,
        config: TrackStateCliLinkFormatterWarningConfig,
    ) -> TrackStateCliLinkFormatterWarningProbeResult: ...
