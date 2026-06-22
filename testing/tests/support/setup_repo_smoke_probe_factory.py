from __future__ import annotations

from testing.core.config.setup_repo_smoke_config import SetupRepoSmokeConfig
from testing.core.interfaces.setup_repo_smoke_probe import SetupRepoSmokeProbe
from testing.frameworks.python.setup_repo_smoke_framework import SetupRepoSmokeFramework


def create_setup_repo_smoke_probe(
    config: SetupRepoSmokeConfig,
) -> SetupRepoSmokeProbe:
    """Create the default SetupRepoSmokeProbe for the given config."""
    return SetupRepoSmokeFramework(config)
