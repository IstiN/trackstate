from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_read_alias_config import (
    TrackStateCliReadAliasConfig,
)
from testing.core.interfaces.trackstate_cli_read_alias_probe import (
    TrackStateCliReadAliasProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_read_alias_result import (
    TrackStateCliReadAliasCaseResult,
    TrackStateCliReadAliasValidationResult,
)
from testing.frameworks.python.trackstate_cli_jira_search_framework import (
    PythonTrackStateCliJiraSearchFramework,
)


class PythonTrackStateCliReadAliasFramework(
    PythonTrackStateCliJiraSearchFramework,
    TrackStateCliReadAliasProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_read_alias_responses(
        self,
        *,
        config: TrackStateCliReadAliasConfig,
    ) -> TrackStateCliReadAliasValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-379-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-379-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-379 can run the exact alias and canonical read "
                    "commands from the seeded repository as the current working "
                    "directory."
                )
                return TrackStateCliReadAliasValidationResult(
                    case_results=tuple(
                        TrackStateCliReadAliasCaseResult(
                            case=case,
                            alias_observation=self._observe_command(
                                requested_command=case.alias_command,
                                repository_path=repository_path,
                                executable_path=executable_path,
                                fallback_reason=fallback_reason,
                            ),
                            canonical_observation=self._observe_command(
                                requested_command=case.canonical_command,
                                repository_path=repository_path,
                                executable_path=executable_path,
                                fallback_reason=fallback_reason,
                            ),
                        )
                        for case in config.cases
                    )
                )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        fallback_reason: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
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
        config: TrackStateCliReadAliasConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/project.json",
            (
                "{"
                f'"key":"{config.project_key}",'
                f'"name":"{config.project_name}"'
                "}\n"
            ),
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._seed_issue(repository_path, config=config)
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-379 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts379@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-379 fixture")

    def _seed_issue(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliReadAliasConfig,
    ) -> None:
        issue = config.fixture_ticket
        self._write_file(
            repository_path / config.project_key / issue.key / "main.md",
            f"""---
key: {issue.key}
project: {config.project_key}
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
