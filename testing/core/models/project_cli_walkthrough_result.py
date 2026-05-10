from __future__ import annotations

import json
from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class QuickStartCommandObservation:
    template: str
    command: str
    project_path: str
    result: CliCommandResult

    @property
    def output(self) -> str:
        fragments = [
            self.result.stdout.strip(),
            self.result.stderr.strip(),
        ]
        return "\n".join(fragment for fragment in fragments if fragment).strip()

    def to_dict(self) -> dict[str, object]:
        return {
            "template": self.template,
            "command": self.command,
            "project_path": self.project_path,
            "result": {
                "command": list(self.result.command),
                "command_text": self.result.command_text,
                "exit_code": self.result.exit_code,
                "stdout": self.result.stdout,
                "stderr": self.result.stderr,
                "succeeded": self.result.succeeded,
            },
        }


@dataclass(frozen=True)
class ProjectCliWalkthroughResult:
    documentation_repository: str
    target_repository: str
    upstream_repository: str
    default_branch: str
    project_path: str
    quick_start_section: str
    code_block_commands: tuple[str, ...]
    auth_status: CliCommandResult
    viewer_login: CliCommandResult
    repository_info: CliCommandResult
    readme_fetch: CliCommandResult
    positive_command: QuickStartCommandObservation
    negative_command: QuickStartCommandObservation
    expected_project_fetch: CliCommandResult
    negative_project_fetch: CliCommandResult

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
    def repository_is_fork(self) -> bool:
        return self.repository_metadata.get("fork") is True

    @property
    def expected_project(self) -> dict[str, object] | None:
        parsed, _ = self._parse_project_payload(self.expected_project_fetch.stdout)
        return parsed

    @property
    def expected_project_parse_error(self) -> str | None:
        _, error = self._parse_project_payload(self.expected_project_fetch.stdout)
        return error

    @property
    def actual_project(self) -> dict[str, object] | None:
        parsed, _ = self._parse_project_payload(self.positive_command.result.stdout)
        return parsed

    @property
    def actual_project_parse_error(self) -> str | None:
        _, error = self._parse_project_payload(self.positive_command.result.stdout)
        return error

    def to_dict(self) -> dict[str, object]:
        return {
            "documentation_repository": self.documentation_repository,
            "target_repository": self.target_repository,
            "upstream_repository": self.upstream_repository,
            "default_branch": self.default_branch,
            "project_path": self.project_path,
            "quick_start_section": self.quick_start_section,
            "code_block_commands": list(self.code_block_commands),
            "repository_is_fork": self.repository_is_fork,
            "repository_parent": self.repository_parent,
            "auth_status": self._serialize_command_result(self.auth_status),
            "viewer_login": self._serialize_command_result(self.viewer_login),
            "repository_info": self._serialize_command_result(self.repository_info),
            "readme_fetch": self._serialize_command_result(self.readme_fetch),
            "positive_command": self.positive_command.to_dict(),
            "negative_command": self.negative_command.to_dict(),
            "expected_project_fetch": self._serialize_command_result(
                self.expected_project_fetch,
            ),
            "negative_project_fetch": self._serialize_command_result(
                self.negative_project_fetch,
            ),
            "actual_project": self.actual_project,
            "actual_project_parse_error": self.actual_project_parse_error,
            "expected_project": self.expected_project,
            "expected_project_parse_error": self.expected_project_parse_error,
        }

    def _parse_project_payload(
        self,
        text: str,
    ) -> tuple[dict[str, object] | None, str | None]:
        stripped = text.strip()
        if not stripped:
            return None, None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as error:
            return None, str(error)
        if isinstance(parsed, dict):
            return parsed, None
        return None, f"Expected a JSON object but observed {type(parsed).__name__}."

    def _serialize_command_result(
        self,
        result: CliCommandResult,
    ) -> dict[str, object]:
        return {
            "command": list(result.command),
            "command_text": result.command_text,
            "exit_code": result.exit_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "succeeded": result.succeeded,
            "json_payload": result.json_payload,
        }
