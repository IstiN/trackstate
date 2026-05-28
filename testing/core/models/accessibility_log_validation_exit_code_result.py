from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class AccessibilityLogValidationExitCodeObservation:
    requested_command: tuple[str, ...]
    workflow_relative_path: str
    node_test_relative_path: str
    validator_relative_path: str
    log_validation_step_name: str
    original_workflow_contains_log_validation_step: bool
    mutated_workflow_contains_log_validation_step: bool
    control_run: CliCommandResult
    mutated_run: CliCommandResult

    @property
    def requested_command_text(self) -> str:
        return " ".join(self.requested_command)

    @property
    def mutation_removed_log_validation_step(self) -> bool:
        return (
            self.original_workflow_contains_log_validation_step
            and not self.mutated_workflow_contains_log_validation_step
        )
