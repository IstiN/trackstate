from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class ProjectCliNegativeCommandCheck:
    path: str
    documented_command_template: str
    documented_command: str
    command_result: CliCommandResult


@dataclass(frozen=True)
class ProjectQuickStartNegativePathResult:
    documentation_repository: str
    default_branch: str
    positive_project_path: str
    quick_start_section: str
    auth_status: CliCommandResult
    repository_info: CliCommandResult
    readme_fetch: CliCommandResult
    tree_fetch: CliCommandResult
    inline_negative_paths: tuple[str, ...]
    command_negative_paths: tuple[str, ...]
    negative_paths: tuple[str, ...]
    negative_command_checks: tuple[ProjectCliNegativeCommandCheck, ...]

    @property
    def tree_paths(self) -> tuple[str, ...]:
        payload = self.tree_fetch.json_payload
        if not isinstance(payload, dict):
            return ()
        tree = payload.get("tree")
        if not isinstance(tree, list):
            return ()

        paths: list[str] = []
        for entry in tree:
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            if isinstance(path, str):
                paths.append(path)
        return tuple(paths)

    @property
    def existing_negative_paths(self) -> tuple[str, ...]:
        tree_paths = set(self.tree_paths)
        return tuple(path for path in self.negative_paths if path in tree_paths)
