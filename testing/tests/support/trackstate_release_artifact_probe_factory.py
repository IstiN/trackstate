from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import LiveSetupTestConfig
from testing.core.config.trackstate_release_artifact_config import (
    TrackStateReleaseArtifactConfig,
)
from testing.core.interfaces.trackstate_release_artifact_probe import (
    TrackStateReleaseArtifactProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.trackstate_release_artifact_framework import (
    PythonTrackStateReleaseArtifactFramework,
)


def create_trackstate_release_artifact_probe(
    repository_root: Path,
) -> TrackStateReleaseArtifactProbe:
    config = TrackStateReleaseArtifactConfig.from_file(
        repository_root / "testing/tests/TS-708/config.yaml"
    )
    repository_service = LiveSetupRepositoryService(
        config=LiveSetupTestConfig(
            app_url=config.releases_page_url,
            repository=config.repository,
            ref=config.default_branch,
        )
    )
    return PythonTrackStateReleaseArtifactFramework(
        repository_root,
        github_api_client=GhCliApiClient(repository_root),
        release_asset_reader=repository_service,
    )
