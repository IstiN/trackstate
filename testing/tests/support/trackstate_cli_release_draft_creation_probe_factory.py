from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.components.services.trackstate_cli_release_draft_creation_probe import (
    TrackStateCliReleaseDraftCreationProbe,
)


def create_trackstate_cli_release_draft_creation_probe(
    repository_root: Path,
) -> TrackStateCliReleaseDraftCreationProbe:
    return TrackStateCliReleaseDraftCreationProbe(
        repository_root,
        LiveSetupRepositoryService(),
    )
