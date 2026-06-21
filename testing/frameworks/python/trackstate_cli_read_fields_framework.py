from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from testing.core.config.trackstate_cli_read_fields_config import (
    TrackStateCliReadFieldsConfig,
)
from testing.core.interfaces.trackstate_cli_read_fields_probe import (
    TrackStateCliReadFieldsProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_read_fields_result import (
    TrackStateCliReadFieldsObservation,
    TrackStateCliReadFieldsValidationResult,
)


class PythonTrackStateCliReadFieldsFramework(TrackStateCliReadFieldsProbe):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_read_fields_response(
        self,
        *,
        config: TrackStateCliReadFieldsConfig,
    ) -> TrackStateCliReadFieldsValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-380-") as temp_dir:
            repository_path = Path(temp_dir)
            self._seed_local_repository(repository_path, config=config)

            dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
            executed_command = (
                dart_bin,
                "run",
                "trackstate",
                "read",
                "fields",
                "--target",
                "local",
                "--path",
                str(repository_path),
            )
            fallback_reason = (
                "Pinned execution to the repository-local CLI via `dart run trackstate` "
                "so the probe cannot execute an unrelated `trackstate` binary from PATH."
            )

            return TrackStateCliReadFieldsValidationResult(
                observation=TrackStateCliReadFieldsObservation(
                    requested_command=config.requested_command,
                    executed_command=executed_command,
                    fallback_reason=fallback_reason,
                    repository_path=str(repository_path),
                    result=self._run(executed_command),
                )
            )

    def _run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path | None = None,
    ) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=cwd or self._repository_root,
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

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliReadFieldsConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        project_key = config.project_key
        self._write_file(
            repository_path / f"{project_key}/project.json",
            json.dumps({"key": project_key, "name": config.project_name}) + "\n",
        )
        self._write_file(
            repository_path / f"{project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / f"{project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        fields = [
            {"id": "summary", "name": "Summary", "custom": False, "schema": {"type": "string", "system": "summary"}},
            {"id": "description", "name": "Description", "custom": False, "schema": {"type": "string", "system": "description"}},
            {"id": "status", "name": "Status", "custom": False, "schema": {"type": "status", "system": "status"}},
            {"id": "priority", "name": "Priority", "custom": False, "schema": {"type": "priority", "system": "priority"}},
            {"id": "assignee", "name": "Assignee", "custom": False, "schema": {"type": "user", "system": "assignee"}},
            {"id": "reporter", "name": "Reporter", "custom": False, "schema": {"type": "user", "system": "reporter"}},
            {"id": "labels", "name": "Labels", "custom": True, "schema": {"type": "array", "system": None}},
        ]
        self._write_file(
            repository_path / f"{project_key}/config/fields.json",
            json.dumps(fields) + "\n",
        )
        self._write_file(
            repository_path / f"{project_key}/config/priorities.json",
            '[{"id":"medium","name":"Medium"},{"id":"high","name":"High"}]\n',
        )
        self._write_file(
            repository_path / f"{project_key}/config/resolutions.json",
            '[{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / f"{project_key}/config/workflows.json",
            '{"default":{"statuses":["To Do","Done"],"transitions":[{"id":"complete","name":"Complete","from":"To Do","to":"Done"}]}}\n',
        )
        self._write_file(
            repository_path / f"{project_key}/.trackstate/index/tombstones.json",
            "[]\n",
        )
        self._write_file(
            repository_path / f"{project_key}/.trackstate/index/issues.json",
            "[]\n",
        )
        (repository_path / f"{project_key}/TS-1").mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{project_key}/TS-1/main.md",
            "---\nkey: TS-1\nproject: TS\nissueType: story\nstatus: todo\npriority: medium\nsummary: Test issue\n---\n\n# Summary\n\nTest issue\n",
        )
        self._git(repository_path, "init", "-b", config.branch)
        self._git(repository_path, "config", "--local", "user.name", config.user_name)
        self._git(repository_path, "config", "--local", "user.email", config.user_email)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-380 fixture")

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
