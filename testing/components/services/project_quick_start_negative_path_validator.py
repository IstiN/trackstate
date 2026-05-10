from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

from testing.components.services.project_quick_start_validator import (
    ProjectQuickStartValidator,
)
from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.project_quick_start_negative_path_result import (
    ProjectCliNegativeCommandCheck,
    ProjectQuickStartNegativePathResult,
)


class ProjectQuickStartNegativePathValidator:
    def __init__(self, *, repository_root: Path, probe: ProjectCliProbe) -> None:
        self._repository_root = Path(repository_root)
        self._probe = probe
        self._quick_start_validator = ProjectQuickStartValidator(
            repository_root=self._repository_root,
            probe=probe,
        )

    def validate(
        self,
        *,
        config: ProjectCliValidationConfig,
    ) -> ProjectQuickStartNegativePathResult:
        auth_status = self._probe.auth_status()
        documentation_repository = config.resolved_documentation_repository
        repository_info = self._probe.repository_metadata(documentation_repository)
        default_branch = self._quick_start_validator._repository_default_branch(
            repository_info,
        )
        readme_fetch = self._probe.get_contents(
            documentation_repository,
            default_branch,
            config.readme_path.name,
        )
        readme_text = self._quick_start_validator._decode_repository_text(readme_fetch)
        quick_start_section = self._quick_start_validator._read_quick_start_section(
            readme_text,
        )
        positive_project_path = (
            self._quick_start_validator._documented_project_file(
                quick_start_section,
            )
            or config.project_path
        )
        tree_fetch = self._probe.list_tree(documentation_repository, default_branch)

        inline_negative_paths = self._inline_negative_paths(quick_start_section)
        negative_command_checks = self._negative_command_checks(
            quick_start_section,
            documentation_repository=documentation_repository,
            default_branch=default_branch,
        )
        command_negative_paths = tuple(
            check.path for check in negative_command_checks
        )
        negative_paths = self._dedupe(
            (*inline_negative_paths, *command_negative_paths),
        )

        return ProjectQuickStartNegativePathResult(
            documentation_repository=documentation_repository,
            default_branch=default_branch,
            positive_project_path=positive_project_path,
            quick_start_section=quick_start_section,
            auth_status=auth_status,
            repository_info=repository_info,
            readme_fetch=readme_fetch,
            tree_fetch=tree_fetch,
            inline_negative_paths=inline_negative_paths,
            command_negative_paths=command_negative_paths,
            negative_paths=negative_paths,
            negative_command_checks=negative_command_checks,
        )

    def _inline_negative_paths(self, quick_start_section: str) -> tuple[str, ...]:
        candidate_paths: list[str] = []
        for paragraph in quick_start_section.split("\n\n"):
            normalized_paragraph = paragraph.lower()
            if (
                "negative" not in normalized_paragraph
                and "404" not in normalized_paragraph
                and "non-existent" not in normalized_paragraph
            ):
                continue
            for candidate in re.findall(r"`([^`]+)`", paragraph):
                if "/" not in candidate or candidate.startswith("<"):
                    continue
                candidate_paths.append(candidate)
        return tuple(candidate_paths)

    def _negative_command_checks(
        self,
        quick_start_section: str,
        *,
        documentation_repository: str,
        default_branch: str,
    ) -> tuple[ProjectCliNegativeCommandCheck, ...]:
        checks: list[ProjectCliNegativeCommandCheck] = []
        for command_template in self._quick_start_validator.documented_validation_commands_in_code_blocks(
            quick_start_section,
        ):
            command_path = self._documented_command_path(command_template)
            if command_path is None or "<" in command_path:
                continue
            documented_command = self._quick_start_validator._expand_documented_command(
                command_template,
                target_repository=documentation_repository,
                default_branch=default_branch,
                project_path=command_path,
            )
            if documented_command is None:
                continue
            checks.append(
                ProjectCliNegativeCommandCheck(
                    path=command_path,
                    documented_command_template=command_template,
                    documented_command=documented_command,
                    command_result=self._probe.run_documented_command(
                        documented_command,
                    ),
                ),
            )
        return tuple(checks)

    def _documented_command_path(self, command_template: str) -> str | None:
        match = re.search(r"/contents/([^?\s]+)\?ref=", command_template)
        if match is None:
            return None
        return unquote(match.group(1))

    def _dedupe(self, values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
        unique_values: list[str] = []
        for value in values:
            if value not in unique_values:
                unique_values.append(value)
        return tuple(unique_values)
