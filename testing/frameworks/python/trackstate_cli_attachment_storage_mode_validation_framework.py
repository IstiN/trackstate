from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_attachment_storage_mode_validation_config import (
    TrackStateCliAttachmentStorageModeValidationConfig,
)
from testing.core.interfaces.trackstate_cli_attachment_storage_mode_validation_probe import (
    TrackStateCliAttachmentStorageModeValidationProbe,
)
from testing.core.models.trackstate_cli_attachment_storage_mode_validation_result import (
    TrackStateCliAttachmentStorageModeValidationRepositoryState,
    TrackStateCliAttachmentStorageModeValidationResult,
    TrackStateCliAttachmentStorageModeValidationStoredFile,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliAttachmentStorageModeValidationFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliAttachmentStorageModeValidationProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_invalid_attachment_storage_mode(
        self,
        *,
        config: TrackStateCliAttachmentStorageModeValidationConfig,
    ) -> TrackStateCliAttachmentStorageModeValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-603-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-603-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                observation = self._observe_command(
                    requested_command=config.requested_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                )
                final_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                return TrackStateCliAttachmentStorageModeValidationResult(
                    initial_state=initial_state,
                    final_state=final_state,
                    observation=observation,
                )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        return TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this checkout "
                "so TS-603 validates the live local attachment command from the seeded "
                "repository instead of any PATH-installed binary."
            ),
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=self._run(executed_command, cwd=repository_path),
        )

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliAttachmentStorageModeValidationConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / config.project_key / "project.json",
            json.dumps(
                {
                    "key": config.project_key,
                    "name": config.project_name,
                    "attachmentStorage": {
                        "mode": config.unsupported_attachment_mode,
                    },
                },
                indent=2,
            )
            + "\n",
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
updated: 2026-05-13T00:00:00Z
---

# Description

TS-603 invalid attachment storage mode fixture.
""",
        )
        self._write_file(
            repository_path / config.source_file_name,
            config.source_file_text,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-603 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts603@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-603 fixture")

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliAttachmentStorageModeValidationConfig,
    ) -> TrackStateCliAttachmentStorageModeValidationRepositoryState:
        issue_main = repository_path / config.project_key / config.issue_key / "main.md"
        source_file = repository_path / config.source_file_name
        attachments_directory = (
            repository_path / config.project_key / config.issue_key / "attachments"
        )
        attachments_metadata = (
            repository_path / config.project_key / config.issue_key / "attachments.json"
        )
        stored_files = (
            tuple(
                sorted(
                    (
                        TrackStateCliAttachmentStorageModeValidationStoredFile(
                            relative_path=str(path.relative_to(repository_path)),
                            size_bytes=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        )
                        for path in attachments_directory.rglob("*")
                        if path.is_file()
                    ),
                    key=lambda observation: observation.relative_path,
                )
            )
            if attachments_directory.is_dir()
            else ()
        )
        return TrackStateCliAttachmentStorageModeValidationRepositoryState(
            issue_main_exists=issue_main.is_file(),
            source_file_exists=source_file.is_file(),
            attachment_directory_exists=attachments_directory.is_dir(),
            attachments_metadata_exists=attachments_metadata.is_file(),
            stored_files=stored_files,
            git_status_lines=self._git_status_lines(repository_path),
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
            project_json_text=self._read_text_if_exists(
                repository_path / config.project_key / "project.json"
            ),
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
