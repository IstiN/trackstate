from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class TrackStateCliSessionContractObservation:
    requested_command: tuple[str, ...]
    executed_command: tuple[str, ...]
    fallback_reason: str | None
    repository_path: str
    result: CliCommandResult

    @property
    def requested_command_text(self) -> str:
        return " ".join(self.requested_command)

    @property
    def executed_command_text(self) -> str:
        return " ".join(self.executed_command)


@dataclass(frozen=True)
class TrackStateCliSessionContractValidationResult:
    observation: TrackStateCliSessionContractObservation
