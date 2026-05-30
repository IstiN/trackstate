from __future__ import annotations

from typing import Protocol

from testing.core.config.accessibility_log_validation_exit_code_config import (
    AccessibilityLogValidationExitCodeConfig,
)
from testing.core.models.accessibility_log_validation_exit_code_result import (
    AccessibilityLogValidationExitCodeObservation,
)


class AccessibilityLogValidationExitCodeProbe(Protocol):
    def validate(
        self,
        config: AccessibilityLogValidationExitCodeConfig,
    ) -> AccessibilityLogValidationExitCodeObservation: ...
