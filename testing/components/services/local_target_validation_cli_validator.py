from __future__ import annotations

from testing.core.config.local_target_validation_cli_config import (
    LocalTargetValidationCliConfig,
)
from testing.core.interfaces.local_target_validation_cli_probe import (
    LocalTargetValidationCliProbe,
)
from testing.core.models.local_target_validation_cli_result import (
    LocalTargetValidationCliValidationResult,
)


class LocalTargetValidationCliValidator:
    def __init__(self, probe: LocalTargetValidationCliProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: LocalTargetValidationCliConfig,
    ) -> LocalTargetValidationCliValidationResult:
        return LocalTargetValidationCliValidationResult(
            observation=self._probe.invalid_local_repository(config=config)
        )
