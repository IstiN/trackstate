from __future__ import annotations

import json
import re
from pathlib import Path

from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.project_cli_validation_result import (
    ProjectCliValidationResult,
)


class ProjectQuickStartValidator:
    def __init__(self, repository_root: Path, probe: ProjectCliProbe) -> None:
        self._repository_root = repository_root
        self._probe = probe

    def validate(
        self,
        *,
        config: ProjectCliValidationConfig,
    ) -> ProjectCliValidationResult:
        auth_status = self._probe.auth_status()
        viewer_login = self._probe.viewer_login()
        target_repository = self._resolve_target_repository(config, viewer_login)
        repository_info = self._probe.repository_metadata(target_repository)
        default_branch = self._repository_default_branch(repository_info)
        documentation_repository = config.resolved_documentation_repository
        documentation_repository_info = self._probe.repository_metadata(
            documentation_repository,
        )
        documentation_default_branch = self._repository_default_branch(
            documentation_repository_info,
        )
        readme_fetch = self._probe.get_contents(
            documentation_repository,
            documentation_default_branch,
            config.readme_path.name,
        )
        readme_text = self._decode_repository_text(readme_fetch)
        quick_start_section = self._read_quick_start_section(readme_text)
        documented_source_repository = self._documented_source_repository(
            quick_start_section,
        )
        documented_project_file = self._documented_project_file(quick_start_section)
        project_path = config.project_path
        documented_command_template = self._documented_validation_command(
            quick_start_section,
            project_path=project_path,
        )
        documented_command = self._expand_documented_command(
            documented_command_template,
            target_repository=target_repository,
            default_branch=default_branch,
            project_path=project_path,
        )
        project_fetch = self._documented_command_result(documented_command)
        expected_project_fetch = self._probe.get_raw_file(
            target_repository,
            default_branch,
            project_path,
        )
        expected_project = self._parse_expected_project(expected_project_fetch)
        return ProjectCliValidationResult(
            target_repository=target_repository,
            upstream_repository=config.upstream_repository,
            documentation_repository=documentation_repository,
            project_path=project_path,
            readme_text=readme_text,
            quick_start_section=quick_start_section,
            expected_project=expected_project,
            documented_source_repository=documented_source_repository,
            documented_project_file=documented_project_file,
            documented_command_template=documented_command_template,
            documented_command=documented_command,
            auth_status=auth_status,
            viewer_login=viewer_login,
            repository_info=repository_info,
            readme_fetch=readme_fetch,
            project_fetch=project_fetch,
            expected_project_fetch=expected_project_fetch,
        )

    def _read_quick_start_section(self, readme_text: str) -> str:
        match = re.search(
            r"^## CLI quick start\s*(.*?)(?=^## |\Z)",
            readme_text,
            re.MULTILINE | re.DOTALL,
        )
        if match is None:
            return ""
        return match.group(0).strip()

    def _decode_repository_text(self, contents_result: object) -> str:
        if hasattr(contents_result, "json_payload") and isinstance(
            contents_result.json_payload,
            dict,
        ):
            content = contents_result.json_payload.get("content")
            if isinstance(content, str):
                return CliCommandResult.decode_base64_text(content.replace("\n", ""))
        return ""

    def _resolve_target_repository(
        self,
        config: ProjectCliValidationConfig,
        viewer_login: object,
    ) -> str:
        if config.target_repository_override is not None:
            return config.target_repository_override
        login = ""
        if hasattr(viewer_login, "json_payload") and isinstance(
            viewer_login.json_payload,
            str,
        ):
            login = viewer_login.json_payload
        return (
            f"{login}/{config.fork_repository_name}"
            if login
            else config.upstream_repository
        )

    def _repository_default_branch(self, repository_info: object) -> str:
        if hasattr(repository_info, "json_payload") and isinstance(
            repository_info.json_payload,
            dict,
        ):
            default_branch = repository_info.json_payload.get("default_branch")
            if isinstance(default_branch, str):
                return default_branch
        return "main"

    def _documented_source_repository(self, quick_start_section: str) -> str | None:
        match = re.search(r"reads from\s+`([^`]+)`\s+by default", quick_start_section)
        if match is None:
            return None
        return match.group(1)

    def _documented_project_file(self, quick_start_section: str) -> str | None:
        match = re.search(r"uses\s+`([^`]+)`\s+plus\s+`([^`]+)`", quick_start_section)
        if match is None:
            return None
        return match.group(1)

    def _documented_validation_command(
        self,
        quick_start_section: str,
        *,
        project_path: str | None = None,
    ) -> str | None:
        code_block_command = self._select_documented_validation_command(
            self.documented_validation_commands_in_code_blocks(quick_start_section),
            project_path=project_path,
        )
        if code_block_command is not None:
            return code_block_command
        inline_commands = tuple(
            candidate.strip()
            for candidate in re.findall(r"`(gh [^`]+)`", quick_start_section)
            if candidate.strip().startswith("gh ")
        )
        return self._select_documented_validation_command(
            inline_commands,
            project_path=project_path,
        )

    def documented_validation_commands_in_code_blocks(
        self,
        quick_start_section: str,
    ) -> tuple[str, ...]:
        commands: list[str] = []
        code_blocks = re.findall(
            r"```(?:bash|shell|sh|text)?\n(.*?)```",
            quick_start_section,
            re.DOTALL,
        )
        for block in code_blocks:
            for line in block.splitlines():
                candidate = line.strip()
                if candidate.startswith("gh "):
                    commands.append(candidate)
        return tuple(commands)

    def _select_documented_validation_command(
        self,
        commands: tuple[str, ...],
        *,
        project_path: str | None,
    ) -> str | None:
        if not commands:
            return None
        if project_path:
            for candidate in commands:
                if project_path in candidate:
                    return candidate
            for candidate in commands:
                if "<project-path>" in candidate:
                    return candidate
        return commands[0]

    def _expand_documented_command(
        self,
        documented_command_template: str | None,
        *,
        target_repository: str,
        default_branch: str,
        project_path: str,
    ) -> str | None:
        if documented_command_template is None:
            return None
        owner, repository_name = self._split_repository(target_repository)
        replacements = (
            ("<fork>", target_repository),
            ("<fork-repository>", target_repository),
            ("<setup-repository>", target_repository),
            ("<repository>", target_repository),
            ("<owner>", owner),
            ("<repo>", repository_name),
            ("<default-branch>", default_branch),
            ("<ref>", default_branch),
            ("<project-path>", project_path),
        )
        documented_command = documented_command_template
        for placeholder, value in replacements:
            documented_command = documented_command.replace(placeholder, value)
        return documented_command

    def _split_repository(self, repository: str) -> tuple[str, str]:
        if "/" not in repository:
            return "", repository
        owner, repository_name = repository.split("/", 1)
        return owner, repository_name

    def _documented_command_result(
        self,
        documented_command: str | None,
    ) -> CliCommandResult:
        if documented_command is None:
            return CliCommandResult(
                command=("README.md",),
                exit_code=1,
                stdout="",
                stderr=(
                    "The `CLI quick start` section does not document an executable "
                    "GitHub CLI validation command."
                ),
            )
        return self._probe.run_documented_command(documented_command)

    def _parse_expected_project(
        self,
        expected_project_fetch: object,
    ) -> dict[str, object]:
        if hasattr(expected_project_fetch, "succeeded") and not expected_project_fetch.succeeded:
            return {}
        if hasattr(expected_project_fetch, "json_payload") and isinstance(
            expected_project_fetch.json_payload,
            dict,
        ):
            return expected_project_fetch.json_payload
        if hasattr(expected_project_fetch, "stdout"):
            stdout = expected_project_fetch.stdout.strip()
            if not stdout:
                return {}
            parsed = json.loads(stdout)
            if isinstance(parsed, dict):
                return parsed
        return {}
