from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_raw_jira_comment_response_config import (
    TrackStateCliRawJiraCommentFixture,
    TrackStateCliRawJiraCommentResponseConfig,
)
from testing.core.interfaces.trackstate_cli_raw_jira_comment_response_probe import (
    TrackStateCliRawJiraCommentResponseProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_raw_jira_comment_response_result import (
    TrackStateCliRawJiraCommentResponseValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliRawJiraCommentResponseFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliRawJiraCommentResponseProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_raw_comment_response(
        self,
        *,
        config: TrackStateCliRawJiraCommentResponseConfig,
    ) -> TrackStateCliRawJiraCommentResponseValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-384-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-384-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Preserved the exact legacy ticket command text, but executed the "
                    "current `--request-path` equivalent from a repository-local CLI "
                    "binary so TS-384 can validate the live allowlisted response shape "
                    "from a seeded Local Git repository."
                )
                return TrackStateCliRawJiraCommentResponseValidationResult(
                    observation=self._observe_command(
                        requested_command=config.ticket_command,
                        compatibility_command=config.compatibility_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
                    )
                )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        compatibility_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        fallback_reason: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *compatibility_command[1:])
        return TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=fallback_reason,
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=self._run(executed_command, cwd=repository_path),
        )

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliRawJiraCommentResponseConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / config.project_key / "project.json",
            (
                "{"
                f'"key":"{config.project_key}",'
                f'"name":"{config.project_name}"'
                "}\n"
            ),
        )
        self._write_file(
            repository_path / config.project_key / "config" / "statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / config.project_key / "config" / "issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / config.project_key / "config" / "fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / config.project_key / config.issue_key / "main.md",
            f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
priority: medium
summary: "{config.issue_summary}"
assignee: qa-user
reporter: qa-user
updated: 2026-05-12T09:06:00Z
---

# Description

TS-384 raw Jira-compatible response fixture.
""",
        )
        for comment in config.fixture_comments:
            self._seed_comment(
                repository_path=repository_path,
                project_key=config.project_key,
                issue_key=config.issue_key,
                comment=comment,
            )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-384 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts384@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-384 fixture")

    def _seed_comment(
        self,
        *,
        repository_path: Path,
        project_key: str,
        issue_key: str,
        comment: TrackStateCliRawJiraCommentFixture,
    ) -> None:
        self._write_file(
            repository_path
            / project_key
            / issue_key
            / "comments"
            / f"{comment.id}.md",
            f"""---
author: {comment.author}
created: {comment.created}
updated: {comment.updated}
---

{comment.body}
""",
        )
