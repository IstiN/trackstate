from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class TrackStateCliFallbackBoundaryObservation:
    name: str
    ticket_command: str
    execution_cwd: str
    executed_command: tuple[str, ...]
    result: CliCommandResult

    @property
    def executed_command_text(self) -> str:
        return " ".join(self.executed_command)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "ticketCommand": self.ticket_command,
            "executionCwd": self.execution_cwd,
            "executedCommand": list(self.executed_command),
            "executedCommandText": self.executed_command_text,
            "result": {
                "command": list(self.result.command),
                "commandText": self.result.command_text,
                "exitCode": self.result.exit_code,
                "stdout": self.result.stdout,
                "stderr": self.result.stderr,
                "jsonPayload": self.result.json_payload,
            },
        }


@dataclass(frozen=True)
class TrackStateCliFallbackBoundariesValidationResult:
    observations: tuple[TrackStateCliFallbackBoundaryObservation, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "observations": [observation.to_dict() for observation in self.observations]
        }
