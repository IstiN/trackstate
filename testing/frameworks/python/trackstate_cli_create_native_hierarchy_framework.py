from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from testing.core.config.trackstate_cli_create_native_hierarchy_config import (
    TrackStateCliCreateNativeHierarchyConfig,
)
from testing.core.interfaces.trackstate_cli_create_native_hierarchy_probe import (
    TrackStateCliCreateNativeHierarchyProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_create_native_hierarchy_result import (
    TrackStateCliCreateNativeHierarchyObservation,
)


class PythonTrackStateCliCreateNativeHierarchyFramework(
    TrackStateCliCreateNativeHierarchyProbe
):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_create_with_native_hierarchy(
        self,
        *,
        config: TrackStateCliCreateNativeHierarchyConfig,
    ) -> TrackStateCliCreateNativeHierarchyObservation:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-457-") as temp_dir:
            repository_path = Path(temp_dir)
            self._seed_local_repository(repository_path, config=config)
            requested_command = (
                *config.requested_command_prefix,
                "--path",
                str(repository_path),
            )
            executed_command = (
                *config.fallback_command_prefix,
                "--path",
                str(repository_path),
            )
            fallback_reason = (
                "Pinned execution to the repository-local CLI via `dart run "
                "trackstate` so TS-457 exercises this checkout against a disposable "
                "Local Git repository instead of any unrelated `trackstate` binary "
                "on PATH."
            )
            result = self._run(executed_command)
            created_issue_main = repository_path / config.expected_storage_path
            epic_root = repository_path / config.project_key / config.epic_key
            epic_directory_entries = tuple(
                str(path.relative_to(repository_path))
                for path in sorted(epic_root.rglob("*"))
            )
            issue_index = (
                repository_path
                / config.project_key
                / ".trackstate"
                / "index"
                / "issues.json"
            )
            return TrackStateCliCreateNativeHierarchyObservation(
                requested_command=requested_command,
                executed_command=executed_command,
                fallback_reason=fallback_reason,
                repository_path=str(repository_path),
                result=result,
                git_status=self._git_output(repository_path, "status", "--short"),
                epic_directory_entries=epic_directory_entries,
                created_issue_main_relative_path=config.expected_storage_path,
                created_issue_main_exists=created_issue_main.is_file(),
                created_issue_main_content=self._read_text_if_exists(created_issue_main),
                issue_index_relative_path=str(issue_index.relative_to(repository_path)),
                issue_index_content=self._read_text_if_exists(issue_index),
                issue_index_payload=self._read_json_if_exists(issue_index),
            )

    def _run(self, command: tuple[str, ...]) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
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

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliCreateNativeHierarchyConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/project.json",
            json.dumps({"key": config.project_key, "name": config.project_name}) + "\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"},{"id":"epic","name":"Epic"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/priorities.json",
            '[{"id":"medium","name":"Medium"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/issues.json",
            (
                '[{"key":"EPIC-101","path":"TS/EPIC-101/main.md","parent":null,'
                '"epic":null,"parentPath":null,"epicPath":null,'
                '"summary":"Seed Epic","issueType":"epic","status":"todo",'
                '"priority":"medium","assignee":"cli-user","labels":[],'
                '"updated":"2026-05-12T00:00:00Z","resolution":null,'
                '"children":[],"archived":false}]\n'
            ),
        )
        self._write_file(
            repository_path / config.project_key / config.epic_key / "main.md",
            f"""---
key: {config.epic_key}
project: {config.project_key}
issueType: epic
status: todo
priority: medium
summary: "Seed Epic"
assignee: cli-user
reporter: cli-user
updated: 2026-05-12T00:00:00Z
---

# Description

Seed epic for TS-457.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-457 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            config.expected_author_email,
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-457 fixture")

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

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
