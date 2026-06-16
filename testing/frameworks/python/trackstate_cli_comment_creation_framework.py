from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from testing.core.config.trackstate_cli_comment_creation_config import (
    TrackStateCliCommentCreationConfig,
)
from testing.core.interfaces.trackstate_cli_comment_creation_probe import (
    TrackStateCliCommentCreationProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_comment_creation_result import (
    CommentFileObservation,
    TrackStateCliCommentCreationObservation,
)


class PythonTrackStateCliCommentCreationFramework(
    TrackStateCliCommentCreationProbe
):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_non_idempotent_comment_creation(
        self,
        *,
        config: TrackStateCliCommentCreationConfig,
    ) -> TrackStateCliCommentCreationObservation:
        with tempfile.TemporaryDirectory(
            prefix="trackstate-cli-comment-creation-"
        ) as temp_dir:
            repository_path = Path(temp_dir)
            self._seed_local_repository(repository_path, config=config)
            initial_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            requested_commands = tuple(
                (
                    *config.requested_command_prefix,
                    "--path",
                    str(repository_path),
                    "--key",
                    config.issue_key,
                    "--body",
                    comment_body,
                )
                for comment_body in config.comment_bodies
            )
            executed_commands = tuple(
                (
                    *config.fallback_command_prefix,
                    "--path",
                    str(repository_path),
                    "--key",
                    config.issue_key,
                    "--body",
                    comment_body,
                )
                for comment_body in config.comment_bodies
            )
            fallback_reason = (
                "Pinned execution to the repository-local CLI via `dart run trackstate` "
                "so this regression exercises the current checkout against a "
                "disposable Local Git "
                "repository instead of any unrelated `trackstate` binary on PATH."
            )
            first_result = self._run(executed_commands[0])
            first_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            second_result = self._run(executed_commands[1])
            second_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            comment_directory = repository_path / config.project_key / config.issue_key / "comments"
            comment_files = tuple(
                CommentFileObservation(
                    relative_path=str(path.relative_to(repository_path)),
                    content=path.read_text(encoding="utf-8"),
                )
                for path in sorted(comment_directory.glob("*.md"))
            )
            return TrackStateCliCommentCreationObservation(
                requested_commands=requested_commands,  # type: ignore[arg-type]
                executed_commands=executed_commands,  # type: ignore[arg-type]
                fallback_reason=fallback_reason,
                repository_path=str(repository_path),
                initial_head_revision=initial_head_revision,
                first_head_revision=first_head_revision,
                second_head_revision=second_head_revision,
                git_status=self._git_output(repository_path, "status", "--short"),
                first_result=first_result,
                second_result=second_result,
                comment_files=comment_files,
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
        config: TrackStateCliCommentCreationConfig,
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
            repository_path / f"{config.project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / config.project_key / config.issue_key / "main.md",
            f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
summary: "CLI comment fixture"
assignee: ts462-user
reporter: ts462-user
updated: 2026-05-12T00:00:00Z
---

# Description

Seeded issue for CLI comment regression coverage.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-462 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts462@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-462 fixture")

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
