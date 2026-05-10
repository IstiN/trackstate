from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile

from testing.core.config.trackstate_cli_session_contract_config import (
    TrackStateCliSessionContractConfig,
)
from testing.core.interfaces.trackstate_cli_session_contract_probe import (
    TrackStateCliSessionContractProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_session_contract_result import (
    TrackStateCliSessionContractObservation,
)


class PythonTrackStateCliSessionContractFramework(TrackStateCliSessionContractProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_default_json_session(
        self,
        *,
        config: TrackStateCliSessionContractConfig,
    ) -> TrackStateCliSessionContractObservation:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-272-") as temp_dir:
            repository_path = Path(temp_dir)
            self._seed_local_repository(repository_path)
            requested_command = (
                *config.requested_command_prefix,
                "--path",
                str(repository_path),
            )
            fallback_command = (
                *config.fallback_command_prefix,
                "--path",
                str(repository_path),
            )
            return self._run_preferred_command(
                requested_command=requested_command,
                fallback_command=fallback_command,
                repository_path=repository_path,
            )

    def _run_preferred_command(
        self,
        *,
        requested_command: tuple[str, ...],
        fallback_command: tuple[str, ...],
        repository_path: Path,
    ) -> TrackStateCliSessionContractObservation:
        preferred_binary = shutil.which(requested_command[0])
        if preferred_binary:
            executed_command = (preferred_binary, *requested_command[1:])
            fallback_reason = None
        else:
            configured_dart = os.environ.get("TRACKSTATE_DART_BIN")
            if configured_dart:
                fallback_command = (configured_dart, *fallback_command[1:])
            executed_command = fallback_command
            fallback_reason = (
                f'"{requested_command[0]}" was not available on PATH, so the test '
                "used the package executable via `dart run trackstate`."
            )

        return TrackStateCliSessionContractObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=fallback_reason,
            repository_path=str(repository_path),
            result=self._run(executed_command),
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
        payload = None
        stdout = completed.stdout.strip()
        if stdout:
            try:
                payload = json.loads(stdout)
            except json.JSONDecodeError:
                payload = None
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=payload,
        )

    def _seed_local_repository(self, repository_path: Path) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(repository_path / ".gitattributes", "*.png filter=lfs diff=lfs merge=lfs -text\n")
        self._write_file(
            repository_path / "DEMO/project.json",
            '{"key":"DEMO","name":"Local Demo"}\n',
        )
        self._write_file(
            repository_path / "DEMO/config/statuses.json",
            '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / "DEMO/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / "DEMO/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / "DEMO/DEMO-1/main.md",
            """---
key: DEMO-1
project: DEMO
issueType: story
status: todo
summary: "TS-272 local session fixture"
assignee: ts272-user
reporter: ts272-user
updated: 2026-05-10T00:00:00Z
---

# Description

Local repository used to verify the default CLI JSON envelope.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-272 Tester")
        self._git(repository_path, "config", "--local", "user.email", "ts272@example.com")
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-272 local session fixture")

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
