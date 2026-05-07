from __future__ import annotations

from typing import Protocol

from testing.core.models.cli_command_result import CliCommandResult


class ProjectCliProbe(Protocol):
    def auth_status(self) -> CliCommandResult: ...

    def get_project(self, repository: str, project_path: str) -> CliCommandResult: ...
