from __future__ import annotations

from pathlib import Path

from testing.core.config.theme_token_policy_multi_target_config import (
    ThemeTokenPolicyMultiTargetConfig,
)
from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.core.models.theme_token_policy_multi_target_validation_result import (
    ThemeTokenPolicyMultiTargetValidationResult,
)


class ThemeTokenPolicyMultiTargetValidator:
    def __init__(self, repository_root: Path, probe: FlutterAnalyzeProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: ThemeTokenPolicyMultiTargetConfig,
    ) -> ThemeTokenPolicyMultiTargetValidationResult:
        flutter_version = self._probe.flutter_version()
        theme_token_check = self._probe.theme_token_check_many(
            self._repository_root,
            config.command_targets,
        )
        return ThemeTokenPolicyMultiTargetValidationResult(
            flutter_version=flutter_version,
            theme_token_check=theme_token_check,
            repository_root=self._repository_root,
            target_paths=config.command_targets,
        )
