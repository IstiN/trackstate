from __future__ import annotations

from pathlib import Path

from testing.components.services.accessibility_log_validation_exit_code_probe import (
    AccessibilityLogValidationExitCodeProbeService,
)
from testing.core.interfaces.accessibility_log_validation_exit_code_probe import (
    AccessibilityLogValidationExitCodeProbe,
)


def create_accessibility_log_validation_exit_code_probe(
    repository_root: Path,
) -> AccessibilityLogValidationExitCodeProbe:
    return AccessibilityLogValidationExitCodeProbeService(repository_root)
