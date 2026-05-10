from __future__ import annotations

from pathlib import Path

from testing.components.services.non_default_branch_release_probe import (
    NonDefaultBranchReleaseProbeService,
)
from testing.core.config.non_default_branch_release_config import (
    NonDefaultBranchReleaseConfig,
)
from testing.core.interfaces.non_default_branch_release_probe import (
    NonDefaultBranchReleaseProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.urllib_url_text_reader import UrllibUrlTextReader


def create_non_default_branch_release_probe(
    repository_root: Path,
) -> NonDefaultBranchReleaseProbe:
    config = NonDefaultBranchReleaseConfig.from_file(
        repository_root / "testing/tests/TS-252/config.yaml"
    )
    return NonDefaultBranchReleaseProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
        url_text_reader=UrllibUrlTextReader(),
    )
