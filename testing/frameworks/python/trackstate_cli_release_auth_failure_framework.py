from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_release_auth_failure_config import (
    TrackStateCliReleaseAuthFailureConfig,
)
from testing.core.interfaces.trackstate_cli_release_auth_failure_probe import (
    TrackStateCliReleaseAuthFailureProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_auth_failure_result import (
    TrackStateCliReleaseAuthFailureRepositoryState,
    TrackStateCliReleaseAuthFailureStoredFile,
    TrackStateCliReleaseAuthFailureValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseAuthFailureFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseAuthFailureProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_release_auth_failure(
        self,
        *,
        config: TrackStateCliReleaseAuthFailureConfig,
    ) -> TrackStateCliReleaseAuthFailureValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-500-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-500-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                observation, stripped_environment_variables = self._observe_command(
                    requested_command=config.requested_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                )
                final_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                return TrackStateCliReleaseAuthFailureValidationResult(
                    initial_state=initial_state,
                    final_state=final_state,
                    observation=observation,
                    stripped_environment_variables=stripped_environment_variables,
                )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
    ) -> tuple[TrackStateCliCommandObservation, tuple[str, ...]]:
        executed_command = (str(executable_path), *requested_command[1:])
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        stripped = tuple(
            variable
            for variable in ("GH_TOKEN", "GITHUB_TOKEN", "TRACKSTATE_TOKEN")
            if env.pop(variable, None) is not None
        )
        sandbox_home = repository_path / ".ts500-home"
        sandbox_home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(sandbox_home)
        env["XDG_CONFIG_HOME"] = str(sandbox_home / ".config")
        env["GH_CONFIG_DIR"] = str(sandbox_home / ".config" / "gh")
        env["GIT_TERMINAL_PROMPT"] = "0"
        completed = subprocess.run(
            executed_command,
            cwd=repository_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        observation = TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this checkout "
                "and stripped GitHub credentials from the environment so TS-500 runs "
                "the exact local command without ambient auth. The current local "
                "provider path may still fail before GitHub auth is consulted."
            ),
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=CliCommandResult(
                command=executed_command,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                json_payload=self._parse_json(completed.stdout),
            ),
        )
        return observation, stripped

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliReleaseAuthFailureConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / config.project_key / "project.json",
            (
                "{\n"
                f'  "key": "{config.project_key}",\n'
                f'  "name": "{config.project_name}",\n'
                '  "attachmentStorage": {\n'
                '    "mode": "github-releases",\n'
                '    "githubReleases": {\n'
                f'      "tagPrefix": "{config.attachment_tag_prefix}"\n'
                "    }\n"
                "  }\n"
                "}\n"
            ),
        )
        self._write_file(
            repository_path / config.project_key / "config" / "statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / config.project_key / "config" / "issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / config.project_key / "config" / "fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / config.project_key / config.issue_key / "main.md",
            f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
summary: "{config.issue_summary}"
assignee: tester
reporter: tester
updated: 2026-05-12T00:00:00Z
---

# Description

TS-500 local github-releases attachment fixture.
""",
        )
        self._write_binary_file(
            repository_path / config.source_file_name,
            config.source_file_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-500 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts500@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", config.remote_origin_url)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-500 fixture")

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseAuthFailureConfig,
    ) -> TrackStateCliReleaseAuthFailureRepositoryState:
        issue_main = repository_path / config.project_key / config.issue_key / "main.md"
        attachment_directory = (
            repository_path / config.project_key / config.issue_key / "attachments"
        )
        expected_attachment = repository_path / config.expected_attachment_relative_path
        stored_files = (
            tuple(
                sorted(
                    (
                        TrackStateCliReleaseAuthFailureStoredFile(
                            relative_path=str(path.relative_to(repository_path)),
                            size_bytes=path.stat().st_size,
                        )
                        for path in attachment_directory.rglob("*")
                        if path.is_file()
                    ),
                    key=lambda observation: observation.relative_path,
                )
            )
            if attachment_directory.is_dir()
            else ()
        )
        remote_origin_url = self._git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip()
        return TrackStateCliReleaseAuthFailureRepositoryState(
            issue_main_exists=issue_main.is_file(),
            attachment_directory_exists=attachment_directory.is_dir(),
            expected_attachment_exists=expected_attachment.is_file(),
            stored_files=stored_files,
            git_status_lines=self._git_status_lines(repository_path),
            remote_origin_url=remote_origin_url or None,
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0
