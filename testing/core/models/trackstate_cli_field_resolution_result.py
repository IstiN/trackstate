from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class TrackStateCliFieldCommandObservation:
    requested_command: tuple[str, ...]
    executed_command: tuple[str, ...]
    result: CliCommandResult

    @property
    def requested_command_text(self) -> str:
        return " ".join(self.requested_command)

    @property
    def executed_command_text(self) -> str:
        return " ".join(self.executed_command)


@dataclass(frozen=True)
class TrackStateCliFieldResolutionObservation:
    fallback_reason: str | None
    repository_path: str
    initial_head_revision: str
    after_exact_head_revision: str
    after_display_head_revision: str
    before_ambiguous_head_revision: str
    final_head_revision: str
    initial_commit_count: int
    after_exact_commit_count: int
    after_display_commit_count: int
    before_ambiguous_commit_count: int
    final_commit_count: int
    after_display_latest_commit_subject: str
    latest_commit_subject: str
    git_status: str
    main_file_relative_path: str
    main_file_content: str
    exact_id: TrackStateCliFieldCommandObservation
    display_name: TrackStateCliFieldCommandObservation
    ambiguous_name: TrackStateCliFieldCommandObservation


@dataclass(frozen=True)
class TrackStateCliFieldResolutionValidationResult:
    observation: TrackStateCliFieldResolutionObservation
