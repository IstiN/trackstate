from __future__ import annotations

from pathlib import Path

from testing.components.services.actionlint_ruleset_enforcement_probe import (
    ActionlintRulesetEnforcementProbeService,
)
from testing.core.config.actionlint_ruleset_enforcement_config import (
    ActionlintRulesetEnforcementConfig,
)
from testing.core.interfaces.actionlint_ruleset_enforcement_probe import (
    ActionlintRulesetEnforcementProbe,
)
from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


def create_actionlint_ruleset_enforcement_probe(
    repository_root: Path,
    *,
    config_path: Path | None = None,
) -> ActionlintRulesetEnforcementProbe:
    config = ActionlintRulesetEnforcementConfig.from_file(
        config_path or repository_root / "testing/tests/TS-261/config.yaml"
    )
    return ActionlintRulesetEnforcementProbeService(
        config,
        github_api_client=GhCliApiClient(repository_root),
    )
