from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_read_profile_local_config import (
    TrackStateCliReadProfileLocalConfig,
)
from testing.core.interfaces.trackstate_cli_read_profile_local_probe import (
    TrackStateCliReadProfileLocalProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_read_profile_local_result import (
    TrackStateCliReadProfileLocalValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReadProfileLocalFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReadProfileLocalProbe,
):
    def observe_local_profile_response(
        self,
        *,
        config: TrackStateCliReadProfileLocalConfig,
    ) -> TrackStateCliReadProfileLocalValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-377-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-377-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-377 can run the exact read profile command from "
                    "the seeded Local Git repository as the current working directory."
                )
                executed_command = (str(executable_path), *config.requested_command[1:])
                return TrackStateCliReadProfileLocalValidationResult(
                    observation=TrackStateCliCommandObservation(
                        requested_command=config.requested_command,
                        executed_command=executed_command,
                        fallback_reason=fallback_reason,
                        repository_path=str(repository_path),
                        compiled_binary_path=str(executable_path),
                        result=self._run(executed_command, cwd=repository_path),
                    )
                )

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliReadProfileLocalConfig,
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
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(repository_path / ".gitignore", ".dart_tool/\n")
        self._git(repository_path, "init", "-b", config.branch)
        self._git(repository_path, "config", "--local", "user.name", config.user_name)
        self._git(repository_path, "config", "--local", "user.email", config.user_email)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-377 fixture")
