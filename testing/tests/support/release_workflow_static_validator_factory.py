from __future__ import annotations

from pathlib import Path

from testing.components.services.release_workflow_static_validator import (
    LocalReleaseWorkflowStaticValidator,
)
from testing.core.interfaces.release_workflow_static_validator import (
    ReleaseWorkflowStaticValidator,
)


def create_release_workflow_static_validator(
    repository_root: Path | None = None,
) -> ReleaseWorkflowStaticValidator:
    return LocalReleaseWorkflowStaticValidator()
