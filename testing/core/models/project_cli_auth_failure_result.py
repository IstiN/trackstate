from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class ProjectCliAuthFailureResult:
    target_repository: str
    default_branch: str
    project_path: str
    quick_start_section: str
    documented_command_template: str | None
    documented_command: str | None
    auth_status: CliCommandResult
    viewer_login: CliCommandResult
    repository_info: CliCommandResult
    invalid_command_result: CliCommandResult

    @property
    def invalid_command_output(self) -> str:
        fragments = [
            self.invalid_command_result.stdout.strip(),
            self.invalid_command_result.stderr.strip(),
        ]
        return "\n".join(fragment for fragment in fragments if fragment).strip()

