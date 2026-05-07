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
        quick_start_section = self._read_quick_start_section(config.readme_path)
        auth_status = self._probe.auth_status()
        viewer_login = self._probe.viewer_login()
        target_repository = self._resolve_target_repository(config, viewer_login)
        repository_info = self._probe.repository_metadata(target_repository)
        default_branch = self._repository_default_branch(repository_info)
        project_fetch = self._probe.get_project(target_repository, config.project_path)
        expected_project_fetch = self._probe.get_raw_project(
            target_repository,
            default_branch,
            config.project_path,
        )
        expected_project = self._parse_expected_project(expected_project_fetch)
        return ProjectCliValidationResult(
            target_repository=target_repository,
            upstream_repository=config.upstream_repository,
            project_path=config.project_path,
            quick_start_section=quick_start_section,
            expected_project=expected_project,
            auth_status=auth_status,
            viewer_login=viewer_login,
            repository_info=repository_info,
            project_fetch=project_fetch,
            expected_project_fetch=expected_project_fetch,
        )

    def _read_quick_start_section(self, readme_path: Path) -> str:
        readme_text = (self._repository_root / readme_path).read_text(encoding="utf-8")
        match = re.search(
            r"^## CLI quick start\s*(.*?)(?=^## |\Z)",
            readme_text,
            re.MULTILINE | re.DOTALL,
        )
        if match is None:
            return ""
        return match.group(0).strip()

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
