from __future__ import annotations

from testing.core.config.hosted_target_selection_cli_config import (
    HostedTargetSelectionCliConfig,
)
from testing.core.interfaces.hosted_target_selection_cli_probe import (
    HostedTargetSelectionCliProbe,
)
from testing.core.models.hosted_target_selection_cli_result import (
    HostedTargetSelectionCliValidationResult,
)


class HostedTargetSelectionCliValidator:
    def __init__(self, probe: HostedTargetSelectionCliProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: HostedTargetSelectionCliConfig,
    ) -> HostedTargetSelectionCliValidationResult:
        return HostedTargetSelectionCliValidationResult(
            observation=self._probe.observe(config=config)
        )
