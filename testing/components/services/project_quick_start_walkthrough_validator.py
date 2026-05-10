from __future__ import annotations

import re
from pathlib import Path

from testing.components.services.project_quick_start_validator import (
    ProjectQuickStartValidator,
)
from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.project_cli_walkthrough_result import (
    ProjectCliWalkthroughResult,
    QuickStartCommandObservation,
)


class ProjectQuickStartWalkthroughValidator:
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
    ) -> ProjectCliWalkthroughResult:
        auth_status = self._probe.auth_status()
        viewer_login = self._probe.viewer_login()
        target_repository = self._quick_start_validator._resolve_target_repository(
            config,
            viewer_login,
        )
        repository_info = self._probe.repository_metadata(target_repository)
        default_branch = self._quick_start_validator._repository_default_branch(
            repository_info,
        )
        documentation_repository = config.resolved_documentation_repository
        documentation_repository_info = self._probe.repository_metadata(
            documentation_repository,
        )
        documentation_default_branch = self._quick_start_validator._repository_default_branch(
            documentation_repository_info,
        )
        readme_fetch = self._probe.get_contents(
            documentation_repository,
            documentation_default_branch,
            config.readme_path.name,
        )
        readme_text = self._quick_start_validator._decode_repository_text(readme_fetch)
        quick_start_section = self._quick_start_validator._read_quick_start_section(
            readme_text,
        )
        code_block_commands = self._quick_start_validator.documented_validation_commands_in_code_blocks(
            quick_start_section,
        )
        positive_template = self._find_positive_command_template(
            code_block_commands=code_block_commands,
            project_path=config.project_path,
        )
        negative_template = self._find_negative_command_template(
            code_block_commands=code_block_commands,
            positive_template=positive_template,
        )
        positive_command = self._expand_command(
            template=positive_template,
            target_repository=target_repository,
            default_branch=default_branch,
            project_path=config.project_path,
        )
        negative_command = self._expand_command(
            template=negative_template,
            target_repository=target_repository,
            default_branch=default_branch,
            project_path=config.project_path,
        )
        positive_project_path = self._extract_project_path(positive_command)
        negative_project_path = self._extract_project_path(negative_command)
        positive_result = self._probe.run_documented_command(positive_command)
        negative_result = self._probe.run_documented_command(negative_command)
        expected_project_fetch = self._probe.get_raw_file(
            target_repository,
            default_branch,
            positive_project_path,
        )
        negative_project_fetch = self._probe.get_raw_file(
            target_repository,
            default_branch,
            negative_project_path,
        )
        return ProjectCliWalkthroughResult(
            documentation_repository=documentation_repository,
            target_repository=target_repository,
            upstream_repository=config.upstream_repository,
            default_branch=default_branch,
            project_path=positive_project_path,
            quick_start_section=quick_start_section,
            code_block_commands=code_block_commands,
            auth_status=auth_status,
            viewer_login=viewer_login,
            repository_info=repository_info,
            readme_fetch=readme_fetch,
            positive_command=QuickStartCommandObservation(
                template=positive_template,
                command=positive_command,
                project_path=positive_project_path,
                result=positive_result,
            ),
            negative_command=QuickStartCommandObservation(
                template=negative_template,
                command=negative_command,
                project_path=negative_project_path,
                result=negative_result,
            ),
            expected_project_fetch=expected_project_fetch,
            negative_project_fetch=negative_project_fetch,
        )

    def _find_positive_command_template(
        self,
        *,
        code_block_commands: tuple[str, ...],
        project_path: str,
    ) -> str:
        for command in code_block_commands:
            if "<project-path>" in command or project_path in command:
                return command
        raise AssertionError(
            "The `CLI quick start` section does not include a positive validation "
            "command for the project JSON file.\n"
            f"Observed code-block commands: {code_block_commands}",
        )

    def _find_negative_command_template(
        self,
        *,
        code_block_commands: tuple[str, ...],
        positive_template: str,
    ) -> str:
        for command in code_block_commands:
            if command == positive_template:
                continue
            if "missing" in command.lower():
                return command
        for command in code_block_commands:
            if command != positive_template:
                return command
        raise AssertionError(
            "The `CLI quick start` section does not include a negative validation "
            "command alongside the positive project-read command.\n"
            f"Observed code-block commands: {code_block_commands}",
        )

    def _expand_command(
        self,
        *,
        template: str,
        target_repository: str,
        default_branch: str,
        project_path: str,
    ) -> str:
        command = self._quick_start_validator._expand_documented_command(
            template,
            target_repository=target_repository,
            default_branch=default_branch,
            project_path=project_path,
        )
        if command is None:
            raise AssertionError(
                "The README quick-start command could not be expanded into an "
                "executable terminal command."
            )
        return command

    def _extract_project_path(self, command: str) -> str:
        match = re.search(r"repos/.+/contents/(.+?)\?ref=", command)
        if match is None:
            raise AssertionError(
                "Could not determine the project path from the README quick-start "
                f"command.\nCommand: {command}"
            )
        return match.group(1)
