from __future__ import annotations

from pathlib import Path

from testing.components.services.live_setup_repository_git_ref_service import (
    LiveSetupRepositoryGitRefService,
)
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.interfaces.trackstate_cli_release_unpushed_branch_probe import (
    TrackStateCliReleaseUnpushedBranchProbe,
)
from testing.frameworks.python.trackstate_cli_release_unpushed_branch_framework import (
    PythonTrackStateCliReleaseUnpushedBranchFramework,
)


def create_trackstate_cli_release_unpushed_branch_probe(
    repository_root: Path,
) -> TrackStateCliReleaseUnpushedBranchProbe:
    repository_client = LiveSetupRepositoryService()
    git_ref_service = LiveSetupRepositoryGitRefService()
    return PythonTrackStateCliReleaseUnpushedBranchFramework(
        repository_root,
        repository_client,
        git_ref_service,
    )
