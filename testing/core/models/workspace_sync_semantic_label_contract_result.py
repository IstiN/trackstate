from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class WorkspaceSyncSemanticLabelContractResult:
    flutter_version: CliCommandResult
    pub_get: CliCommandResult
    flutter_test: CliCommandResult
    test_relative_path: Path
    source_relative_path: Path
    test_source: str
    source: str

    @staticmethod
    def combine_output(command_result: CliCommandResult) -> str:
        parts = [command_result.stdout.strip(), command_result.stderr.strip()]
        return "\n".join(part for part in parts if part)
