from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class TrackStateCliCreateNativeHierarchyObservation:
    requested_command: tuple[str, ...]
    executed_command: tuple[str, ...]
    fallback_reason: str | None
    repository_path: str
    result: CliCommandResult
    git_status: str
    epic_directory_entries: tuple[str, ...]
    created_issue_main_relative_path: str
    created_issue_main_exists: bool
    created_issue_main_content: str | None
    issue_index_relative_path: str
    issue_index_content: str | None
    issue_index_payload: object | None

    @property
    def requested_command_text(self) -> str:
        return " ".join(self.requested_command)

    @property
    def executed_command_text(self) -> str:
        return " ".join(self.executed_command)


@dataclass(frozen=True)
class TrackStateCliCreateNativeHierarchyValidationResult:
    observation: TrackStateCliCreateNativeHierarchyObservation
