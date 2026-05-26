from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from testing.core.config.trackstate_cli_multi_field_update_config import (
    TrackStateCliMultiFieldUpdateConfig,
)
from testing.core.interfaces.trackstate_cli_multi_field_update_probe import (
    TrackStateCliMultiFieldUpdateProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_multi_field_update_result import (
    TrackStateCliMultiFieldUpdateObservation,
)


class PythonTrackStateCliMultiFieldUpdateFramework(
    TrackStateCliMultiFieldUpdateProbe
):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_multi_field_update(
        self,
        *,
        config: TrackStateCliMultiFieldUpdateConfig,
    ) -> TrackStateCliMultiFieldUpdateObservation:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-460-") as temp_dir:
            repository_path = Path(temp_dir)
            self._seed_local_repository(repository_path, config=config)

            issue_path = repository_path / config.project_key / config.issue_key / "main.md"
            field_arguments = self._field_arguments(config)
            requested_command = (
                *config.requested_command_prefix,
                "--path",
                str(repository_path),
                "--key",
                config.issue_key,
                *field_arguments,
            )
            executed_command = (
                *config.fallback_command_prefix,
                "--path",
                str(repository_path),
                "--key",
                config.issue_key,
                *field_arguments,
            )
            fallback_reason = (
                "Pinned execution to the repository-local CLI via `dart run trackstate` "
                "so TS-460 exercises this checkout against a disposable Local Git "
                "repository instead of any unrelated `trackstate` binary on PATH."
            )
            initial_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            initial_commit_count = int(
                self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
            )
            result = self._run(executed_command)
            final_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            final_commit_count = int(
                self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
            )
            latest_commit_subject = self._git_output(
                repository_path,
                "log",
                "-1",
                "--pretty=%s",
            ).strip()
            git_status = self._git_output(repository_path, "status", "--short")
            main_file_content = issue_path.read_text(encoding="utf-8")

            return TrackStateCliMultiFieldUpdateObservation(
                requested_command=requested_command,
                executed_command=executed_command,
                fallback_reason=fallback_reason,
                repository_path=str(repository_path),
                initial_head_revision=initial_head_revision,
                final_head_revision=final_head_revision,
                initial_commit_count=initial_commit_count,
                final_commit_count=final_commit_count,
                latest_commit_subject=latest_commit_subject,
                git_status=git_status,
                main_file_relative_path=str(issue_path.relative_to(repository_path)),
                main_file_content=main_file_content,
                result=result,
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

    @staticmethod
    def _field_arguments(
        config: TrackStateCliMultiFieldUpdateConfig,
    ) -> tuple[str, ...]:
        arguments: list[str] = []
        for assignment in config.field_assignments:
            arguments.extend(("--field", assignment))
        return tuple(arguments)

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliMultiFieldUpdateConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/project.json",
            json.dumps({"key": config.project_key, "name": config.project_name}) + "\n",
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
            repository_path / f"{config.project_key}/config/priorities.json",
            '[{"id":"low","name":"Low"},{"id":"high","name":"High"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            (
                '[{"id":"summary","name":"Summary","type":"string","required":true},'
                '{"id":"description","name":"Description","type":"markdown","required":false}]\n'
            ),
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/resolutions.json",
            '[{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/workflows.json",
            (
                '{"default":{"statuses":["To Do","Done"],"transitions":'
                '[{"id":"complete","name":"Complete","from":"To Do","to":"Done"},'
                '{"id":"reopen","name":"Reopen","from":"Done","to":"To Do"}]}}\n'
            ),
        )
        main_file_content = f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
priority: {config.initial_priority_id}
summary: "{config.initial_summary}"
assignee: {config.initial_assignee}
reporter: seed-user
labels: ["{config.initial_labels[0]}"]
updated: 2026-05-12T00:00:00Z
---

# Summary

{config.initial_summary}

# Description

Seeded issue for TS-460.
"""
        self._write_file(
            repository_path / config.project_key / config.issue_key / "main.md",
            main_file_content,
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/tombstones.json",
            '[]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/issues.json",
            json.dumps(
                [
                    {
                        "key": config.issue_key,
                        "path": f"{config.project_key}/{config.issue_key}/main.md",
                        "parent": None,
                        "epic": None,
                        "summary": config.initial_summary,
                        "issueType": "story",
                        "status": "todo",
                        "priority": config.initial_priority_id,
                        "assignee": config.initial_assignee,
                        "labels": list(config.initial_labels),
                        "updated": "2026-05-12T00:00:00Z",
                        "revision": self._blob_revision_for_text(main_file_content),
                        "children": [],
                        "archived": False,
                    }
                ]
            )
            + "\n",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-460 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts460@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-460 fixture")

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
