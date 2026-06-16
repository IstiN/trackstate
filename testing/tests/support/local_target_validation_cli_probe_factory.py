from __future__ import annotations

from pathlib import Path

from testing.core.interfaces.local_target_validation_cli_probe import (
    LocalTargetValidationCliProbe,
)
from testing.frameworks.python.local_target_validation_cli_framework import (
    PythonLocalTargetValidationCliFramework,
)


def create_local_target_validation_cli_probe(
    repository_root: Path,
) -> LocalTargetValidationCliProbe:
    return PythonLocalTargetValidationCliFramework(repository_root)
