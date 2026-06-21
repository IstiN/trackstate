from __future__ import annotations

import os
from pathlib import Path
import tempfile

from testing.core.config.trackstate_cli_read_fields_local_config import (
    TrackStateCliReadFieldsLocalConfig,
)
from testing.core.interfaces.trackstate_cli_read_fields_local_probe import (
    TrackStateCliReadFieldsLocalProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_read_fields_local_result import (
    TrackStateCliReadFieldsLocalValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReadFieldsLocalFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReadFieldsLocalProbe,
):
    def observe_local_fields_response(
        self,
        *,
        config: TrackStateCliReadFieldsLocalConfig,
    ) -> TrackStateCliReadFieldsLocalValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-380-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-380-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-380 can run the exact read fields command from "
                    "the seeded Local Git repository as the current working directory."
                )
                executed_command = (
                    str(executable_path),
                    *config.requested_command[1:],
                    "--path",
                    str(repository_path),
                )
                result = self._run(executed_command, cwd=repository_path)
                fields: tuple[dict[str, object], ...] = ()
                payload = result.json_payload
                if isinstance(payload, list):
                    fields = tuple(entry for entry in payload if isinstance(entry, dict))
                return TrackStateCliReadFieldsLocalValidationResult(
                    observation=TrackStateCliCommandObservation(
                        requested_command=config.requested_command,
                        executed_command=executed_command,
                        fallback_reason=fallback_reason,
                        repository_path=str(repository_path),
                        compiled_binary_path=str(executable_path),
                        result=result,
                    ),
                    fields=fields,
                )

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliReadFieldsLocalConfig,
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
        fields = [
            {
                "id": "summary",
                "name": "Summary",
                "custom": False,
                "orderable": True,
                "navigable": True,
                "searchable": True,
                "clauseNames": ["summary"],
                "schema": {"type": "string", "system": "summary"},
            },
            {
                "id": "description",
                "name": "Description",
                "custom": False,
                "orderable": True,
                "navigable": True,
                "searchable": True,
                "clauseNames": ["description"],
                "schema": {"type": "string", "system": "description"},
            },
            {
                "id": "status",
                "name": "Status",
                "custom": False,
                "orderable": False,
                "navigable": True,
                "searchable": True,
                "clauseNames": ["status"],
                "schema": {"type": "status", "system": "status"},
            },
            {
                "id": "priority",
                "name": "Priority",
                "custom": False,
                "orderable": True,
                "navigable": True,
                "searchable": True,
                "clauseNames": ["priority"],
                "schema": {"type": "priority", "system": "priority"},
            },
            {
                "id": "assignee",
                "name": "Assignee",
                "custom": False,
                "orderable": True,
                "navigable": True,
                "searchable": True,
                "clauseNames": ["assignee"],
                "schema": {"type": "user", "system": "assignee"},
            },
            {
                "id": "reporter",
                "name": "Reporter",
                "custom": False,
                "orderable": True,
                "navigable": True,
                "searchable": True,
                "clauseNames": ["reporter"],
                "schema": {"type": "user", "system": "reporter"},
            },
            {
                "id": "labels",
                "name": "Labels",
                "custom": True,
                "orderable": True,
                "navigable": True,
                "searchable": True,
                "clauseNames": ["labels"],
                "schema": {"type": "array", "custom": "com.atlassian.jira.plugin.system.customfieldtypes:labels"},
            },
        ]
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            self._json(fields) + "\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/priorities.json",
            '[{"id":"medium","name":"Medium"},{"id":"high","name":"High"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/resolutions.json",
            '[{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/workflows.json",
            (
                '{"default":{"statuses":["To Do","Done"],'
                '"transitions":[{"id":"complete","name":"Complete",'
                '"from":"To Do","to":"Done"}]}}\n'
            ),
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/tombstones.json",
            "[]\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/issues.json",
            "[]\n",
        )
        self._write_file(repository_path / ".gitignore", ".dart_tool/\n")
        (repository_path / f"{config.project_key}/TS-1").mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/TS-1/main.md",
            "---\nkey: TS-1\nproject: TS\nissueType: story\nstatus: todo\npriority: medium\nsummary: Test issue\n---\n\n# Summary\n\nTest issue\n",
        )
        self._git(repository_path, "init", "-b", config.branch)
        self._git(
            repository_path,
            "config",
            "--local",
            "user.name",
            config.user_name,
        )
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            config.user_email,
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-380 fixture")

    @staticmethod
    def _json(value: object) -> str:
        import json

        return json.dumps(value)
