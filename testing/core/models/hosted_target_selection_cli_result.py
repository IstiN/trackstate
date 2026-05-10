from __future__ import annotations

from dataclasses import dataclass

from testing.core.interfaces.hosted_target_selection_cli_probe import (
    HostedTargetSelectionCliProbeResult,
)


@dataclass(frozen=True)
class HostedTargetSelectionCliValidationResult:
    observation: HostedTargetSelectionCliProbeResult
