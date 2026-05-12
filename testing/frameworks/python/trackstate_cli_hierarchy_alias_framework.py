from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from testing.core.config.trackstate_cli_hierarchy_alias_config import (
    TrackStateCliHierarchyAliasConfig,
)
from testing.core.interfaces.trackstate_cli_hierarchy_alias_probe import (
    TrackStateCliHierarchyAliasProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_hierarchy_alias_result import (
    TrackStateCliHierarchyAliasObservation,
)


class PythonTrackStateCliHierarchyAliasFramework(TrackStateCliHierarchyAliasProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_hierarchy_alias_mapping(
        self,
        *,
        config: TrackStateCliHierarchyAliasConfig,
    ) -> TrackStateCliHierarchyAliasObservation:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-459-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-459-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-459 can run the Jira-compatible aliases from the "
                    "seeded repository as the current working directory."
                )
                create_observation = self._observe_command(
                    requested_command=config.requested_create_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                create_issue_relative_path = self._issue_relative_path(
                    create_observation.result.json_payload
                )
                create_issue_content = self._read_relative_path(
                    repository_path, create_issue_relative_path
                )
                update_observation = self._observe_command(
                    requested_command=config.requested_update_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                original_subtask_path = (
                    repository_path / config.expected_original_subtask_path
                )
                updated_subtask_path = (
                    repository_path / config.expected_updated_subtask_path
                )
                return TrackStateCliHierarchyAliasObservation(
                    create_observation=create_observation,
                    update_observation=update_observation,
                    created_issue_relative_path=create_issue_relative_path,
                    created_issue_content=create_issue_content,
                    original_subtask_relative_path=config.expected_original_subtask_path,
                    original_subtask_exists_after_update=original_subtask_path.exists(),
                    updated_subtask_relative_path=config.expected_updated_subtask_path,
                    updated_subtask_exists_after_update=updated_subtask_path.exists(),
                    updated_subtask_content=(
                        updated_subtask_path.read_text(encoding="utf-8")
                        if updated_subtask_path.exists()
                        else None
                    ),
                    final_git_status=self._git_output(
                        repository_path, "status", "--short"
                    ),
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

    def _compile_executable(self, destination: Path) -> None:
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            (
                dart_bin,
                "compile",
                "exe",
                "bin/trackstate.dart",
                "-o",
                str(destination),
            ),
            cwd=self._repository_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                "Failed to compile a temporary TrackState CLI executable for TS-459.\n"
                f"Command: {dart_bin} compile exe bin/trackstate.dart -o {destination}\n"
                f"Exit code: {completed.returncode}\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

    def _run(self, command: tuple[str, ...], *, cwd: Path) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=self._parse_json(completed.stdout),
        )

    @staticmethod
    def _parse_json(stdout: str) -> object | None:
        payload = stdout.strip()
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _issue_relative_path(payload: object | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        issue = data.get("issue")
        if not isinstance(issue, dict):
            return None
        storage_path = issue.get("storagePath")
        return storage_path if isinstance(storage_path, str) else None

    @staticmethod
    def _read_relative_path(repository_path: Path, relative_path: str | None) -> str | None:
        if relative_path is None:
            return None
        absolute_path = repository_path / relative_path
        if not absolute_path.exists():
            return None
        return absolute_path.read_text(encoding="utf-8")

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliHierarchyAliasConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/project.json",
            json.dumps({"key": config.project_key, "name": config.project_name}) + "\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do"},{"id":"in-progress","name":"In Progress"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"},{"id":"epic","name":"Epic"},{"id":"subtask","name":"Sub-task"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            (
                '[{"id":"summary","name":"Summary","type":"string","required":true},'
                '{"id":"description","name":"Description","type":"markdown","required":false}]\n'
            ),
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/priorities.json",
            '[{"id":"medium","name":"Medium"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/resolutions.json",
            '[{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/workflows.json",
            (
                '{"default":{"statuses":["To Do","In Progress"],"transitions":'
                '[{"id":"start","name":"Start work","from":"To Do","to":"In Progress"}]}}\n'
            ),
        )
        epic_content = f"""---
key: {config.epic_key}
project: {config.project_key}
issueType: epic
status: in-progress
priority: medium
summary: "Platform epic"
assignee: hierarchy-admin
reporter: hierarchy-admin
updated: 2026-05-12T00:00:00Z
---

# Summary

Platform epic

# Description

Root epic for hierarchy alias verification.
"""
        target_story_content = f"""---
key: {config.target_story_key}
project: {config.project_key}
issueType: story
status: todo
priority: medium
summary: "Target story"
assignee: hierarchy-user
reporter: hierarchy-admin
epic: {config.epic_key}
updated: 2026-05-12T00:05:00Z
---

# Summary

Target story

# Description

Destination story for parent reassignment.
"""
        source_story_content = f"""---
key: {config.source_story_key}
project: {config.project_key}
issueType: story
status: todo
priority: medium
summary: "Source story"
assignee: hierarchy-user
reporter: hierarchy-admin
epic: {config.epic_key}
updated: 2026-05-12T00:10:00Z
---

# Summary

Source story

# Description

Original parent story for the seeded sub-task.
"""
        subtask_content = f"""---
key: {config.subtask_key}
project: {config.project_key}
issueType: subtask
status: todo
priority: medium
summary: "Nested sub-task"
assignee: hierarchy-user
reporter: hierarchy-admin
parent: {config.source_story_key}
epic: {config.epic_key}
updated: 2026-05-12T00:15:00Z
---

# Summary

Nested sub-task

# Description

Sub-task used to verify canonical parent moves.
"""
        self._write_file(
            repository_path / config.project_key / config.epic_key / "main.md",
            epic_content,
        )
        self._write_file(
            repository_path
            / config.project_key
            / config.epic_key
            / config.target_story_key
            / "main.md",
            target_story_content,
        )
        self._write_file(
            repository_path
            / config.project_key
            / config.epic_key
            / config.source_story_key
            / "main.md",
            source_story_content,
        )
        self._write_file(
            repository_path
            / config.project_key
            / config.epic_key
            / config.source_story_key
            / config.subtask_key
            / "main.md",
            subtask_content,
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/tombstones.json",
            '[]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/issues.json",
            json.dumps(
                [
                    self._issue_index_entry(
                        key=config.epic_key,
                        path=f"{config.project_key}/{config.epic_key}/main.md",
                        summary="Platform epic",
                        issue_type="epic",
                        status="in-progress",
                        priority="medium",
                        assignee="hierarchy-admin",
                        updated="2026-05-12T00:00:00Z",
                        revision=self._blob_revision_for_text(epic_content),
                        children=[config.target_story_key, config.source_story_key],
                    ),
                    self._issue_index_entry(
                        key=config.target_story_key,
                        path=(
                            f"{config.project_key}/{config.epic_key}/"
                            f"{config.target_story_key}/main.md"
                        ),
                        summary="Target story",
                        issue_type="story",
                        status="todo",
                        priority="medium",
                        assignee="hierarchy-user",
                        updated="2026-05-12T00:05:00Z",
                        revision=self._blob_revision_for_text(target_story_content),
                        epic=config.epic_key,
                    ),
                    self._issue_index_entry(
                        key=config.source_story_key,
                        path=(
                            f"{config.project_key}/{config.epic_key}/"
                            f"{config.source_story_key}/main.md"
                        ),
                        summary="Source story",
                        issue_type="story",
                        status="todo",
                        priority="medium",
                        assignee="hierarchy-user",
                        updated="2026-05-12T00:10:00Z",
                        revision=self._blob_revision_for_text(source_story_content),
                        epic=config.epic_key,
                        children=[config.subtask_key],
                    ),
                    self._issue_index_entry(
                        key=config.subtask_key,
                        path=(
                            f"{config.project_key}/{config.epic_key}/"
                            f"{config.source_story_key}/{config.subtask_key}/main.md"
                        ),
                        summary="Nested sub-task",
                        issue_type="subtask",
                        status="todo",
                        priority="medium",
                        assignee="hierarchy-user",
                        updated="2026-05-12T00:15:00Z",
                        revision=self._blob_revision_for_text(subtask_content),
                        parent=config.source_story_key,
                        epic=config.epic_key,
                    ),
                ]
            )
            + "\n",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-459 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts459@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-459 fixture")

    @staticmethod
    def _issue_index_entry(
        *,
        key: str,
        path: str,
        summary: str,
        issue_type: str,
        status: str,
        priority: str,
        assignee: str,
        updated: str,
        revision: str,
        parent: str | None = None,
        epic: str | None = None,
        children: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "key": key,
            "path": path,
            "parent": parent,
            "epic": epic,
            "summary": summary,
            "issueType": issue_type,
            "status": status,
            "priority": priority,
            "assignee": assignee,
            "updated": updated,
            "revision": revision,
            "children": children or [],
            "archived": False,
        }

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _git(repository_path: Path, *args: str) -> None:
        completed = subprocess.run(
            ("git", "-C", str(repository_path), *args),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed for {repository_path}.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

    @staticmethod
    def _git_output(repository_path: Path, *args: str) -> str:
        completed = subprocess.run(
            ("git", "-C", str(repository_path), *args),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed for {repository_path}.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        return completed.stdout

    @staticmethod
    def _blob_revision_for_text(content: str) -> str:
        value = 2166136261
        for byte in content.encode("utf-8"):
            value ^= byte
            value = (value * 16777619) & 0xFFFFFFFF
        chunk = f"{value:08x}"
        return (chunk * 5)[:40]
