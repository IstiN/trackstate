from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class SemanticLabelContextComplianceResult:
    flutter_version: CliCommandResult
    pub_get: CliCommandResult
    analyze: CliCommandResult
    temp_repository_root: Path
    target_relative_path: Path
    localization_relative_path: Path
    source: str
    localization_source: str

    @property
    def target_path(self) -> Path:
        return self.temp_repository_root / self.target_relative_path

    @property
    def localization_path(self) -> Path:
        return self.temp_repository_root / self.localization_relative_path

    @staticmethod
    def combine_output(command_result: CliCommandResult) -> str:
        parts = [command_result.stdout.strip(), command_result.stderr.strip()]
        return "\n".join(part for part in parts if part)
