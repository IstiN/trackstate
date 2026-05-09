from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class HardcodedHexLintValidationResult:
    flutter_version: CliCommandResult
    pub_get: CliCommandResult
    tokenized_analyze: CliCommandResult
    hardcoded_analyze: CliCommandResult
    temp_repository_root: Path
    probe_relative_path: Path

    @property
    def probe_path(self) -> Path:
        return self.temp_repository_root / self.probe_relative_path

    @staticmethod
    def combine_output(command_result: CliCommandResult) -> str:
        parts = [command_result.stdout.strip(), command_result.stderr.strip()]
        return "\n".join(part for part in parts if part)
