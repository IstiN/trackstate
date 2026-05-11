from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_read_fields_config import (
    TrackStateCliReadFieldsConfig,
)
from testing.core.interfaces.trackstate_cli_read_fields_probe import (
    TrackStateCliReadFieldsProbe,
)
from testing.core.models.trackstate_cli_read_fields_result import (
    TrackStateCliReadFieldsObservation,
    TrackStateCliReadFieldsValidationResult,
)
from testing.frameworks.python.trackstate_cli_jira_search_framework import (
    PythonTrackStateCliJiraSearchFramework,
)


class PythonTrackStateCliReadFieldsFramework(
    PythonTrackStateCliJiraSearchFramework,
    TrackStateCliReadFieldsProbe,
):
    def observe_fields_response_shape(
        self,
        *,
        config: TrackStateCliReadFieldsConfig,
    ) -> TrackStateCliReadFieldsValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-380-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-380-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                executed_command = (str(executable_path), *config.requested_command[1:])
                return TrackStateCliReadFieldsValidationResult(
                    observation=TrackStateCliReadFieldsObservation(
                        requested_command=config.requested_command,
                        executed_command=executed_command,
                        fallback_reason=(
                            "Pinned execution to a temporary executable compiled from "
                            "this checkout so TS-380 can run the exact ticket command "
                            "from the seeded repository as the current working "
                            "directory."
                        ),
                        repository_path=str(repository_path),
                        compiled_binary_path=str(executable_path),
                        result=self._run(executed_command, cwd=repository_path),
                    )
                )

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliReadFieldsConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
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
            (
                "["
                f'{{"id":"{config.summary_field_id}","name":"{config.summary_field_name}",'
                f'"type":"{config.summary_schema_type}","required":true}},'
                f'{{"id":"{config.custom_field_id}","name":"{config.custom_field_name}",'
                f'"type":"{config.custom_schema_type}","required":false}}'
                "]\n"
            ),
        )
        self._write_file(
            repository_path / "DEMO/DEMO-1/main.md",
            """---
key: DEMO-1
project: DEMO
issueType: story
status: todo
summary: "TS-380 local read fields fixture"
assignee: ts380-user
reporter: ts380-user
updated: 2026-05-11T00:00:00Z
---

# Description

Local repository used to verify the `trackstate read fields` response shape.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-380 Tester")
        self._git(repository_path, "config", "--local", "user.email", "ts380@example.com")
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-380 read fields fixture")
