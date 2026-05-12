from __future__ import annotations

import json
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchFixtureIssue,
)
from testing.core.config.trackstate_cli_lifecycle_config import (
    TrackStateCliLifecycleConfig,
)
from testing.core.interfaces.trackstate_cli_lifecycle_probe import (
    TrackStateCliLifecycleProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_lifecycle_result import (
    TrackStateCliLifecycleRepositoryState,
    TrackStateCliLifecycleValidationResult,
)
from testing.frameworks.python.trackstate_cli_jira_search_framework import (
    PythonTrackStateCliJiraSearchFramework,
)


class PythonTrackStateCliLifecycleFramework(
    PythonTrackStateCliJiraSearchFramework,
    TrackStateCliLifecycleProbe,
):
    def observe_lifecycle_behavior(
        self,
        *,
        config: TrackStateCliLifecycleConfig,
    ) -> TrackStateCliLifecycleValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-461-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-461-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-461 can run the exact ticket commands from the "
                    "seeded repository as the current working directory."
                )
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                delete_observation = self._observe_command(
                    requested_command=config.delete_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                after_delete_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                archive_observation = self._observe_command(
                    requested_command=config.archive_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                after_archive_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                return TrackStateCliLifecycleValidationResult(
                    initial_state=initial_state,
                    after_delete_state=after_delete_state,
                    after_archive_state=after_archive_state,
                    delete_observation=delete_observation,
                    archive_observation=archive_observation,
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
        config: TrackStateCliLifecycleConfig,
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
        self._seed_issue(
            repository_path=repository_path,
            project_key=config.project_key,
            issue=config.delete_issue,
        )
        self._seed_issue(
            repository_path=repository_path,
            project_key=config.project_key,
            issue=config.archive_issue,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-461 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts461@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-461 fixture")

    def _seed_issue(
        self,
        *,
        repository_path: Path,
        project_key: str,
        issue: TrackStateCliJiraSearchFixtureIssue,
    ) -> None:
        self._write_file(
            repository_path / project_key / issue.key / "main.md",
            f"""---
key: {issue.key}
project: {project_key}
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

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliLifecycleConfig,
    ) -> TrackStateCliLifecycleRepositoryState:
        project_root = repository_path / config.project_key
        deleted_issue_dir = project_root / config.delete_issue.key
        deleted_issue_main = deleted_issue_dir / "main.md"
        deleted_issue_archive_main = (
            project_root / ".trackstate" / "archive" / config.delete_issue.key / "main.md"
        )
        archived_issue_dir = project_root / config.archive_issue.key
        archived_issue_main = archived_issue_dir / "main.md"
        archived_issue_archive_main = (
            project_root / ".trackstate" / "archive" / config.archive_issue.key / "main.md"
        )
        tombstone_index = project_root / ".trackstate" / "index" / "tombstones.json"
        deleted_issue_tombstone = (
            project_root / ".trackstate" / "tombstones" / f"{config.delete_issue.key}.json"
        )
        archived_issue_tombstone = (
            project_root / ".trackstate" / "tombstones" / f"{config.archive_issue.key}.json"
        )
        return TrackStateCliLifecycleRepositoryState(
            deleted_issue_directory_exists=deleted_issue_dir.is_dir(),
            deleted_issue_main_exists=deleted_issue_main.is_file(),
            deleted_issue_archive_main_exists=deleted_issue_archive_main.is_file(),
            archived_issue_directory_exists=archived_issue_dir.is_dir(),
            archived_issue_main_exists=archived_issue_main.is_file(),
            archived_issue_main_content=self._read_text_if_exists(archived_issue_main),
            archived_issue_archive_main_exists=archived_issue_archive_main.is_file(),
            archived_issue_archive_main_content=self._read_text_if_exists(
                archived_issue_archive_main
            ),
            tombstone_index_exists=tombstone_index.is_file(),
            tombstone_index_text=self._read_text_if_exists(tombstone_index),
            tombstone_index_payload=self._read_json_if_exists(tombstone_index),
            deleted_issue_tombstone_exists=deleted_issue_tombstone.is_file(),
            deleted_issue_tombstone_text=self._read_text_if_exists(
                deleted_issue_tombstone
            ),
            deleted_issue_tombstone_payload=self._read_json_if_exists(
                deleted_issue_tombstone
            ),
            archived_issue_tombstone_exists=archived_issue_tombstone.is_file(),
            archived_issue_tombstone_text=self._read_text_if_exists(
                archived_issue_tombstone
            ),
            archived_issue_tombstone_payload=self._read_json_if_exists(
                archived_issue_tombstone
            ),
        )

    @staticmethod
    def _read_text_if_exists(path: Path) -> str | None:
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _read_json_if_exists(path: Path) -> object | None:
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
