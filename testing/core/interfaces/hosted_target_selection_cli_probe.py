from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from testing.core.config.hosted_target_selection_cli_config import (
    HostedTargetSelectionCliConfig,
)


@dataclass(frozen=True)
class HostedTargetSelectionCliProbeResult:
    succeeded: bool
    analyze_output: str
    run_output: str | None
    observation_payload: dict[str, object] | None


class HostedTargetSelectionCliProbe(Protocol):
    def observe(
        self,
        *,
        config: HostedTargetSelectionCliConfig,
    ) -> HostedTargetSelectionCliProbeResult: ...
