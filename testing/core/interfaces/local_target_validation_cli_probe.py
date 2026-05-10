from __future__ import annotations

from typing import Protocol

from testing.core.config.local_target_validation_cli_config import (
    LocalTargetValidationCliConfig,
)
from testing.core.models.local_target_validation_cli_result import (
    LocalTargetValidationCliObservation,
)


class LocalTargetValidationCliProbe(Protocol):
    def invalid_local_repository(
        self,
        *,
        config: LocalTargetValidationCliConfig,
    ) -> LocalTargetValidationCliObservation: ...
