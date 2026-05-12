from __future__ import annotations

from pathlib import Path
import tempfile

from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchConfig,
    TrackStateCliJiraSearchFixtureIssue,
)
from testing.core.interfaces.trackstate_cli_jira_search_probe import (
    TrackStateCliJiraSearchProbe,
)
from testing.core.models.trackstate_cli_jira_search_result import (
    TrackStateCliJiraSearchObservation,
    TrackStateCliJiraSearchValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliJiraSearchFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliJiraSearchProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_search_response_shape(
        self,
        *,
        config: TrackStateCliJiraSearchConfig,
    ) -> TrackStateCliJiraSearchValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-319-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-319-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-319 can run the exact ticket command from the "
                    "seeded repository as the current working directory."
                )
                return TrackStateCliJiraSearchValidationResult(
                    ticket_command=self._observe_command(
                        requested_command=config.requested_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
                    ),
                    supported_control=self._observe_command(
                        requested_command=config.supported_control_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
                    ),
                )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        fallback_reason: str,
    ) -> TrackStateCliJiraSearchObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        return TrackStateCliJiraSearchObservation(
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
        config: TrackStateCliJiraSearchConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / "TRACK/project.json",
            '{"key":"TRACK","name":"Track Project"}\n',
        )
        self._write_file(
            repository_path / "TRACK/config/statuses.json",
            '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / "TRACK/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / "TRACK/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        for issue in config.fixture_issues:
            self._seed_issue(repository_path, issue)
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-319 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts319@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-319 fixture")

    def _seed_issue(
        self,
        repository_path: Path,
        issue: TrackStateCliJiraSearchFixtureIssue,
    ) -> None:
        self._write_file(
            repository_path / "TRACK" / issue.key / "main.md",
            f"""---
key: {issue.key}
project: TRACK
issueType: {issue.issue_type}
status: {issue.status}
summary: "{issue.summary}"
assignee: {issue.assignee}
reporter: {issue.reporter}
updated: {issue.updated}
---

# Description

{issue.issue_description}
""",
        )
