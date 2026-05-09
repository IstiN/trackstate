from __future__ import annotations

from pathlib import Path

from testing.core.config.theme_token_policy_directory_config import (
    ThemeTokenPolicyDirectoryConfig,
)
from testing.core.interfaces.flutter_analyze_probe import FlutterAnalyzeProbe
from testing.core.models.theme_token_policy_directory_validation_result import (
    ThemeTokenPolicyDirectoryValidationResult,
)


class ThemeTokenPolicyDirectoryValidator:
    def __init__(self, repository_root: Path, probe: FlutterAnalyzeProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: ThemeTokenPolicyDirectoryConfig,
    ) -> ThemeTokenPolicyDirectoryValidationResult:
        flutter_version = self._probe.flutter_version()
        theme_token_check = self._probe.theme_token_check(
            self._repository_root,
            config.target_path,
        )
        return ThemeTokenPolicyDirectoryValidationResult(
            flutter_version=flutter_version,
            theme_token_check=theme_token_check,
            repository_root=self._repository_root,
            target_path=config.target_path,
        )
