from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class ThemeTokenPolicyMultiTargetValidationResult:
    flutter_version: CliCommandResult
    theme_token_check: CliCommandResult
    repository_root: Path
    target_paths: tuple[str, ...]

    @staticmethod
    def combine_output(command_result: CliCommandResult) -> str:
        parts = [command_result.stdout.strip(), command_result.stderr.strip()]
        return "\n".join(part for part in parts if part)
