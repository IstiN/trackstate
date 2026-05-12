from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.interfaces.trackstate_cli_hosted_lfs_restriction_probe import (
    TrackStateCliHostedLfsRestrictionProbe,
)
from testing.frameworks.python.trackstate_cli_hosted_lfs_restriction_framework import (
    PythonTrackStateCliHostedLfsRestrictionFramework,
)


def create_trackstate_cli_hosted_lfs_restriction_probe(
    repository_root: Path,
) -> TrackStateCliHostedLfsRestrictionProbe:
    return PythonTrackStateCliHostedLfsRestrictionFramework(
        repository_root,
        repository_client=LiveSetupRepositoryService(),
    )
