from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.frameworks.python.trackstate_cli_release_identity_conflict_framework import (
    PythonTrackStateCliReleaseIdentityConflictFramework,
)


def create_trackstate_cli_release_identity_conflict_probe(
    repository_root: Path,
) -> PythonTrackStateCliReleaseIdentityConflictFramework:
    return PythonTrackStateCliReleaseIdentityConflictFramework(
        repository_root,
        repository_client=LiveSetupRepositoryService(),
    )
