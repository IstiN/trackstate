from __future__ import annotations

from pathlib import Path

from testing.components.services.theme_token_ci_workflow_probe import (
    ThemeTokenCiWorkflowProbe,
)
from testing.core.config.theme_token_ci_config import ThemeTokenCiConfig
from testing.core.interfaces.theme_token_ci_probe import ThemeTokenCiProbe
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_theme_token_ci_probe(repository_root: Path) -> ThemeTokenCiProbe:
    config = ThemeTokenCiConfig.from_file(
        repository_root / "testing/tests/TS-131/config.yaml"
    )
    return ThemeTokenCiWorkflowProbe(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )
