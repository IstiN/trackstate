from __future__ import annotations

from pathlib import Path

from testing.components.services.release_on_merge_probe import ReleaseOnMergeProbeService
from testing.core.config.release_on_merge_config import ReleaseOnMergeConfig
from testing.core.interfaces.release_on_merge_probe import ReleaseOnMergeProbe
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient
from testing.frameworks.python.urllib_url_text_reader import UrllibUrlTextReader


def create_release_on_merge_probe(repository_root: Path) -> ReleaseOnMergeProbe:
    config = ReleaseOnMergeConfig.from_file(
        repository_root / "testing/tests/TS-230/config.yaml"
    )
    return ReleaseOnMergeProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
        url_text_reader=UrllibUrlTextReader(),
    )
