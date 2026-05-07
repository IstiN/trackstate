from __future__ import annotations

from typing import Protocol

from testing.core.models.cli_command_result import CliCommandResult


class ProjectCliProbe(Protocol):
    def auth_status(self) -> CliCommandResult: ...

    def run_documented_command(self, command: str) -> CliCommandResult: ...

    def viewer_login(self) -> CliCommandResult: ...

    def repository_metadata(self, repository: str) -> CliCommandResult: ...

    def run_documented_command(self, command: str) -> CliCommandResult: ...

    def get_contents(
        self,
        repository: str,
        ref: str,
        path: str,
    ) -> CliCommandResult: ...

    def get_raw_file(
        self,
        repository: str,
        ref: str,
        path: str,
    ) -> CliCommandResult: ...

    def list_tree(
        self,
        repository: str,
        ref: str,
    ) -> CliCommandResult: ...

    def get_project(
        self,
        repository: str,
        default_branch: str,
        project_path: str,
    ) -> CliCommandResult: ...
