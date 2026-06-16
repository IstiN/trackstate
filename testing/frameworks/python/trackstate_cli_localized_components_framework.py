from __future__ import annotations

import json
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_localized_components_config import (
    TrackStateCliLocalizedComponentsConfig,
)
from testing.core.interfaces.trackstate_cli_localized_components_probe import (
    TrackStateCliLocalizedComponentsProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_localized_components_result import (
    TrackStateCliLocalizedComponentsValidationResult,
)
from testing.frameworks.python.trackstate_cli_jira_search_framework import (
    PythonTrackStateCliJiraSearchFramework,
)


class PythonTrackStateCliLocalizedComponentsFramework(
    PythonTrackStateCliJiraSearchFramework,
    TrackStateCliLocalizedComponentsProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_localized_component_metadata(
        self,
        *,
        config: TrackStateCliLocalizedComponentsConfig,
    ) -> TrackStateCliLocalizedComponentsValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-468-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(
                prefix="trackstate-ts-468-repo-"
            ) as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-468 can run the exact component-read commands from "
                    "the seeded repository as the current working directory."
                )
                return TrackStateCliLocalizedComponentsValidationResult(
                    default_observation=self._observe_command(
                        requested_command=config.default_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
                    ),
                    french_observation=self._observe_command(
                        requested_command=config.french_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        fallback_reason=fallback_reason,
                    ),
                    german_observation=self._observe_command(
                        requested_command=config.german_command,
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
        config: TrackStateCliLocalizedComponentsConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/project.json",
            json.dumps(
                {
                    "key": config.project_key,
                    "name": config.project_name,
                    "defaultLocale": "en",
                    "supportedLocales": ["en", "fr", "de"],
                }
            )
            + "\n",
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
            repository_path / f"{config.project_key}/config/components.json",
            json.dumps(
                [
                    {"id": fixture.id, "name": fixture.name}
                    for fixture in config.fixtures
                ]
            )
            + "\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/i18n/fr.json",
            json.dumps(
                {
                    "components": {
                        fixture.id: fixture.french_display_name
                        for fixture in config.fixtures
                    }
                }
            )
            + "\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/i18n/de.json",
            json.dumps(
                {
                    "components": {
                        fixture.id: fixture.german_display_name
                        for fixture in config.fixtures
                        if fixture.german_display_name is not None
                    }
                }
            )
            + "\n",
        )
        self._write_file(
            repository_path / config.project_key / "TRACK-1" / "main.md",
            f"""---
key: TRACK-1
project: {config.project_key}
issueType: story
status: todo
summary: "TS-468 localization fixture"
assignee: cli-user
reporter: cli-user
updated: 2026-05-12T00:00:00Z
components:
  - tracker-cli
---

# Description

Seeded issue that keeps the Local Git repository readable for TS-468.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-468 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts468@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-468 fixture")
