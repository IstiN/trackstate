from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class ProjectCliValidationResult:
    repository: str
    project_path: str
    expected_project: dict[str, object]
    auth_status: CliCommandResult
    project_fetch: CliCommandResult

    @property
    def actual_project(self) -> dict[str, object] | None:
        return self.project_fetch.json_payload
