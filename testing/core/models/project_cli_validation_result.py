from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class ProjectCliValidationResult:
    target_repository: str
    upstream_repository: str
    project_path: str
    readme_text: str
    quick_start_section: str
    project_template: dict[str, object]
    expected_project: dict[str, object]
    auth_status: CliCommandResult
    viewer_login: CliCommandResult
    repository_info: CliCommandResult
    tree_fetch: CliCommandResult
    project_fetch: CliCommandResult
    expected_project_fetch: CliCommandResult

    @property
    def repository_metadata(self) -> dict[str, object]:
        if isinstance(self.repository_info.json_payload, dict):
            return self.repository_info.json_payload
        return {}

    @property
    def template_trackstate(self) -> dict[str, object]:
        trackstate = self.project_template.get("trackstate")
        if isinstance(trackstate, dict):
            return trackstate
        return {}

    @property
    def documented_source_repository(self) -> str | None:
        source_repository = self.template_trackstate.get("sourceRepository")
        if isinstance(source_repository, str):
            return source_repository
        return None

    @property
    def documented_project_file(self) -> str | None:
        project_file = self.template_trackstate.get("projectFile")
        if isinstance(project_file, str):
            return project_file
        return None

    @property
    def documented_config_path(self) -> str | None:
        config_path = self.template_trackstate.get("configPath")
        if isinstance(config_path, str):
            return config_path
        return None

    @property
    def documented_default_ref(self) -> str | None:
        default_ref = self.template_trackstate.get("defaultRef")
        if isinstance(default_ref, str):
            return default_ref
        return None

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
    def tree_payload(self) -> dict[str, object]:
        if isinstance(self.tree_fetch.json_payload, dict):
            return self.tree_fetch.json_payload
        return {}

    @property
    def tree_paths(self) -> list[str]:
        tree = self.tree_payload.get("tree")
        if not isinstance(tree, list):
            return []
        paths: list[str] = []
        for entry in tree:
            if isinstance(entry, dict):
                path = entry.get("path")
                if isinstance(path, str):
                    paths.append(path)
        return paths

    @property
    def project_fetch_payload(self) -> dict[str, object]:
        if isinstance(self.project_fetch.json_payload, dict):
            return self.project_fetch.json_payload
        return {}

    @property
    def project_fetch_path(self) -> str | None:
        path = self.project_fetch_payload.get("path")
        if isinstance(path, str):
            return path
        return None

    @property
    def project_fetch_encoding(self) -> str | None:
        encoding = self.project_fetch_payload.get("encoding")
        if isinstance(encoding, str):
            return encoding
        return None

    @property
    def project_fetch_content(self) -> str | None:
        content = self.project_fetch_payload.get("content")
        if isinstance(content, str):
            return content.replace("\n", "")
        return None

    @property
    def actual_project(self) -> dict[str, object] | None:
        encoded_content = self.project_fetch_content
        if not encoded_content:
            return None
        try:
            decoded_content = base64.b64decode(encoded_content).decode("utf-8")
            parsed = json.loads(decoded_content)
        except (ValueError, json.JSONDecodeError):
            return None
        if isinstance(parsed, dict):
            return parsed
        return None

    @property
    def actual_project_text(self) -> str:
        actual_project = self.actual_project
        if actual_project is None:
            return ""
        return json.dumps(actual_project, indent=2)
