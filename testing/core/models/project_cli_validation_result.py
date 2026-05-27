from __future__ import annotations

import json
from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class ProjectCliValidationResult:
    target_repository: str
    upstream_repository: str
    documentation_repository: str
    project_path: str
    readme_text: str
    quick_start_section: str
    expected_project: dict[str, object]
    documented_source_repository: str | None
    documented_project_file: str | None
    documented_command_template: str | None
    documented_command: str | None
    auth_status: CliCommandResult
    viewer_login: CliCommandResult
    repository_info: CliCommandResult
    readme_fetch: CliCommandResult
    project_fetch: CliCommandResult
    expected_project_fetch: CliCommandResult

    @property
    def repository_metadata(self) -> dict[str, object]:
        if isinstance(self.repository_info.json_payload, dict):
            return self.repository_info.json_payload
        return {}

    @property
    def repository_parent(self) -> str | None:
        parent = self.repository_metadata.get("parent")
        if isinstance(parent, dict):
            full_name = parent.get("full_name")
            if isinstance(full_name, str):
                return full_name
        return None

    @property
    def repository_default_branch(self) -> str | None:
        default_branch = self.repository_metadata.get("default_branch")
        if isinstance(default_branch, str):
            return default_branch
        return None

    @property
    def repository_is_fork(self) -> bool:
        return self.repository_metadata.get("fork") is True

    @property
    def readme_repository(self) -> str:
        return self.documentation_repository

    @property
    def actual_project(self) -> dict[str, object] | None:
        stdout = self.project_fetch.stdout.strip()
        if not stdout:
            return None
        try:
            parsed = json.loads(stdout)
        except (ValueError, json.JSONDecodeError):
            return None
        if not isinstance(parsed, dict):
            return None
        content = parsed.get("content")
        encoding = parsed.get("encoding")
        if isinstance(content, str) and encoding == "base64":
            try:
                decoded_content = CliCommandResult.decode_base64_text(
                    content.replace("\n", ""),
                )
                decoded_json = json.loads(decoded_content)
            except (ValueError, json.JSONDecodeError):
                return None
            if isinstance(decoded_json, dict):
                return decoded_json
            return None
        return parsed

    @property
    def actual_project_text(self) -> str:
        actual_project = self.actual_project
        if actual_project is None:
            return ""
        return json.dumps(actual_project, indent=2)
