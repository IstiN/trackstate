from __future__ import annotations

import json
import re
from pathlib import Path

from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
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
        readme_text = self._read_readme_text(config.readme_path)
        quick_start_section = self._read_quick_start_section(readme_text)
        project_template = self._read_project_template(config.project_template_path)
        auth_status = self._probe.auth_status()
        viewer_login = self._probe.viewer_login()
        target_repository = self._resolve_target_repository(config, viewer_login)
        repository_info = self._probe.repository_metadata(target_repository)
        default_branch = self._repository_default_branch(repository_info)
        project_path = self._project_path_from_template(project_template, config)
        tree_fetch = self._probe.list_tree(target_repository, default_branch)
        project_fetch = self._probe.get_project(
            target_repository,
            default_branch,
            project_path,
        )
        expected_project_fetch = self._probe.get_raw_project(
            target_repository,
            default_branch,
            project_path,
        )
        expected_project = self._parse_expected_project(expected_project_fetch)
        return ProjectCliValidationResult(
            target_repository=target_repository,
            upstream_repository=config.upstream_repository,
            project_path=project_path,
            readme_text=readme_text,
            quick_start_section=quick_start_section,
            project_template=project_template,
            expected_project=expected_project,
            auth_status=auth_status,
            viewer_login=viewer_login,
            repository_info=repository_info,
            tree_fetch=tree_fetch,
            project_fetch=project_fetch,
            expected_project_fetch=expected_project_fetch,
        )

    def _read_readme_text(self, readme_path: Path) -> str:
        return (self._repository_root / readme_path).read_text(encoding="utf-8")

    def _read_quick_start_section(self, readme_text: str) -> str:
        match = re.search(
            r"^## CLI quick start\s*(.*?)(?=^## |\Z)",
            readme_text,
            re.MULTILINE | re.DOTALL,
        )
        if match is None:
            return ""
        return match.group(0).strip()

    def _read_project_template(self, project_template_path: Path) -> dict[str, object]:
        project_template_text = (self._repository_root / project_template_path).read_text(
            encoding="utf-8",
        )
        parsed = json.loads(project_template_text)
        if isinstance(parsed, dict):
            return parsed
        return {}

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
        return f"{login}/{config.fork_repository_name}" if login else config.upstream_repository

    def _repository_default_branch(self, repository_info: object) -> str:
        if hasattr(repository_info, "json_payload") and isinstance(
            repository_info.json_payload,
            dict,
        ):
            default_branch = repository_info.json_payload.get("default_branch")
            if isinstance(default_branch, str):
                return default_branch
        return "main"

    def _project_path_from_template(
        self,
        project_template: dict[str, object],
        config: ProjectCliValidationConfig,
    ) -> str:
        trackstate = project_template.get("trackstate")
        if isinstance(trackstate, dict):
            project_file = trackstate.get("projectFile")
            if isinstance(project_file, str) and project_file:
                return project_file
        return config.project_path

    def _parse_expected_project(
        self,
        expected_project_fetch: object,
    ) -> dict[str, object]:
        if hasattr(expected_project_fetch, "json_payload") and isinstance(
            expected_project_fetch.json_payload,
            dict,
        ):
            return expected_project_fetch.json_payload
        if hasattr(expected_project_fetch, "stdout"):
            return json.loads(expected_project_fetch.stdout)
        return {}
