from __future__ import annotations

import base64
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
        auth_status = self._probe.auth_status()
        viewer_login = self._probe.viewer_login()
        target_repository = self._resolve_target_repository(config, viewer_login)
        repository_info = self._probe.repository_metadata(target_repository)
        default_branch = self._repository_default_branch(repository_info)
        readme_fetch = self._probe.get_contents(
            target_repository,
            default_branch,
            config.readme_path.name,
        )
        readme_text = self._decode_repository_text(readme_fetch)
        quick_start_section = self._read_quick_start_section(readme_text)
        project_template_fetch = self._probe.get_contents(
            target_repository,
            default_branch,
            config.project_template_path.name,
        )
        project_template = self._parse_json_contents(project_template_fetch)
        documented_source_repository = self._documented_source_repository(
            quick_start_section,
        )
        documented_project_file = self._documented_project_file(quick_start_section)
        documented_config_glob = self._documented_config_glob(quick_start_section)
        documented_tree_route, documented_contents_route = self._documented_api_routes(
            readme_text,
        )
        project_path = documented_project_file or self._project_path_from_template(
            project_template,
            config,
        )
        tree_fetch = self._probe.list_tree(target_repository, default_branch)
        project_fetch = self._probe.get_project(
            target_repository,
            default_branch,
            project_path,
        )
        expected_project_fetch = self._probe.get_raw_file(
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
            documented_source_repository=documented_source_repository,
            documented_project_file=documented_project_file,
            documented_config_glob=documented_config_glob,
            documented_tree_route=documented_tree_route,
            documented_contents_route=documented_contents_route,
            auth_status=auth_status,
            viewer_login=viewer_login,
            repository_info=repository_info,
            readme_fetch=readme_fetch,
            project_template_fetch=project_template_fetch,
            tree_fetch=tree_fetch,
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
                return self._decode_base64_text(content)
        return ""

    def _parse_json_contents(self, contents_result: object) -> dict[str, object]:
        decoded_text = self._decode_repository_text(contents_result)
        if not decoded_text:
            return {}
        try:
            parsed = json.loads(decoded_text)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
        return {}

    def _decode_base64_text(self, content: str) -> str:
        normalized = content.replace("\n", "")
        return base64.b64decode(normalized).decode("utf-8")

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

    def _documented_config_glob(self, quick_start_section: str) -> str | None:
        match = re.search(r"uses\s+`([^`]+)`\s+plus\s+`([^`]+)`", quick_start_section)
        if match is None:
            return None
        return match.group(2)

    def _documented_api_routes(self, readme_text: str) -> tuple[str | None, str | None]:
        match = re.search(
            r"GitHub API \(`([^`]+)` for file discovery and `([^`]+)` for "
            r"markdown/config reads\)",
            readme_text,
        )
        if match is None:
            return None, None
        return match.group(1), match.group(2)

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
