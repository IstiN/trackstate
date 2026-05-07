from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class ProjectCliValidationResult:
    target_repository: str
    upstream_repository: str
    project_path: str
    quick_start_section: str
    project_template: dict[str, object]
    expected_project: dict[str, object]
    auth_status: CliCommandResult
    viewer_login: CliCommandResult
    repository_info: CliCommandResult
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
    def actual_project(self) -> dict[str, object] | None:
        if isinstance(self.project_fetch.json_payload, dict):
            return self.project_fetch.json_payload
        return None
