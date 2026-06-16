from __future__ import annotations

import json
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_issue_link_types_config import (
    TrackStateCliIssueLinkTypesConfig,
)
from testing.core.interfaces.trackstate_cli_issue_link_types_probe import (
    TrackStateCliIssueLinkTypesProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_issue_link_types_result import (
    TrackStateCliIssueLinkTypesValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliIssueLinkTypesFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliIssueLinkTypesProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_issue_link_types(
        self,
        *,
        config: TrackStateCliIssueLinkTypesConfig,
    ) -> TrackStateCliIssueLinkTypesValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-376-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-376-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-376 can run the exact metadata-read commands from "
                    "a seeded Local Git repository."
                )
                return TrackStateCliIssueLinkTypesValidationResult(
                    ticket_observation=self._observe_command(
                        requested_command=config.ticket_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
                    ),
                    canonical_observation=self._observe_command(
                        requested_command=config.canonical_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
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

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliIssueLinkTypesConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/project.json",
            json.dumps({"key": config.project_key, "name": config.project_name}) + "\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do","category":"new"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story","workflowId":"delivery","hierarchyLevel":0}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/workflows.json",
            '{"delivery":{"name":"Delivery","statuses":["To Do"],"transitions":[]}}\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / config.project_key / "TRACK-1" / "main.md",
            f"""---
key: TRACK-1
project: {config.project_key}
issueType: story
status: todo
summary: "TS-376 issue link type fixture"
assignee: cli-user
reporter: cli-user
updated: 2026-05-12T00:00:00Z
---

# Description

Seeded issue to keep the repository recognizable as a valid TrackState project.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-376 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts376@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-376 fixture")
