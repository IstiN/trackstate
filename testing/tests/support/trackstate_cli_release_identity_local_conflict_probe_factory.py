from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.interfaces.trackstate_cli_release_identity_local_conflict_probe import (
    TrackStateCliReleaseIdentityLocalConflictProbe,
)
from testing.frameworks.python.trackstate_cli_release_identity_local_conflict_framework import (
    PythonTrackStateCliReleaseIdentityLocalConflictFramework,
)


def create_trackstate_cli_release_identity_local_conflict_probe(
    repository_root: Path,
) -> TrackStateCliReleaseIdentityLocalConflictProbe:
    return PythonTrackStateCliReleaseIdentityLocalConflictFramework(
        repository_root,
        repository_client=LiveSetupRepositoryService(),
    )
