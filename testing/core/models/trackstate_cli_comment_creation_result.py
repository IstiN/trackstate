from __future__ import annotations

from dataclasses import dataclass

from testing.core.models.cli_command_result import CliCommandResult


@dataclass(frozen=True)
class CommentFileObservation:
    relative_path: str
    content: str


@dataclass(frozen=True)
class TrackStateCliCommentCreationObservation:
    requested_commands: tuple[tuple[str, ...], tuple[str, ...]]
    executed_commands: tuple[tuple[str, ...], tuple[str, ...]]
    fallback_reason: str | None
    repository_path: str
    initial_head_revision: str
    first_head_revision: str
    second_head_revision: str
    git_status: str
    first_result: CliCommandResult
    second_result: CliCommandResult
    comment_files: tuple[CommentFileObservation, ...]

    @property
    def requested_command(self) -> tuple[str, ...]:
        return self.requested_commands[0]

    @property
    def second_requested_command(self) -> tuple[str, ...]:
        return self.requested_commands[1]

    @property
    def executed_command(self) -> tuple[str, ...]:
        return self.executed_commands[0]

    @property
    def second_executed_command(self) -> tuple[str, ...]:
        return self.executed_commands[1]

    @property
    def requested_command_text(self) -> str:
        return " ".join(self.requested_command)

    @property
    def executed_command_text(self) -> str:
        return " ".join(self.executed_command)


@dataclass(frozen=True)
class TrackStateCliCommentCreationValidationResult:
    observation: TrackStateCliCommentCreationObservation
