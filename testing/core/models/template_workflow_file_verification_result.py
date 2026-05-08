from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class TemplateWorkflowFileVerificationResult:
    target_repository: str
    workflow_path: str
    workflow_directory_path: str
    workflow_filename: str
    repository_info: CliCommandResult
    directory_fetch: CliCommandResult
    tree_fetch: CliCommandResult
    workflow_contents_fetch: CliCommandResult
    workflow_raw_fetch: CliCommandResult

    @property
    def repository_metadata(self) -> dict[str, object]:
        if isinstance(self.repository_info.json_payload, dict):
            return self.repository_info.json_payload
        return {}

    @property
    def repository_default_branch(self) -> str | None:
        default_branch = self.repository_metadata.get("default_branch")
        if isinstance(default_branch, str) and default_branch:
            return default_branch
        return None

    @property
    def workflow_directory_entries(self) -> list[str]:
        payload = self.directory_fetch.json_payload
        if not isinstance(payload, list):
            return []

        entries: list[str] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str):
                entries.append(name)
        return entries

    @property
    def tree_paths(self) -> list[str]:
        payload = self.tree_fetch.json_payload
        if not isinstance(payload, dict):
            return []

        tree = payload.get("tree")
        if not isinstance(tree, list):
            return []

        paths: list[str] = []
        for item in tree:
            if not isinstance(item, dict):
                continue
            path = item.get("path")
            if isinstance(path, str):
                paths.append(path)
        return paths

    @property
    def workflow_entry_metadata(self) -> dict[str, object]:
        payload = self.workflow_contents_fetch.json_payload
        if isinstance(payload, dict):
            return payload
        return {}

    @property
    def workflow_entry_type(self) -> str | None:
        entry_type = self.workflow_entry_metadata.get("type")
        if isinstance(entry_type, str) and entry_type:
            return entry_type
        return None

    @property
    def workflow_html_url(self) -> str | None:
        html_url = self.workflow_entry_metadata.get("html_url")
        if isinstance(html_url, str) and html_url:
            return html_url
        return None

    @property
    def workflow_raw_text(self) -> str:
        return self.workflow_raw_fetch.stdout
