from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_attachment_upload_boundary_config import (
    TrackStateCliAttachmentUploadBoundaryConfig,
)
from testing.core.interfaces.trackstate_cli_attachment_upload_boundary_probe import (
    TrackStateCliAttachmentUploadBoundaryProbe,
)
from testing.core.models.trackstate_cli_attachment_upload_boundary_result import (
    TrackStateCliAttachmentUploadBoundaryRepositoryState,
    TrackStateCliAttachmentUploadBoundaryValidationResult,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliAttachmentUploadBoundaryFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliAttachmentUploadBoundaryProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_duplicate_file_boundary(
        self,
        *,
        config: TrackStateCliAttachmentUploadBoundaryConfig,
    ) -> TrackStateCliAttachmentUploadBoundaryValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-387-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(
                prefix="trackstate-ts-387-repo-"
            ) as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-387 can run the exact ticket command from the "
                    "seeded repository as the current working directory."
                )
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                observation = self._observe_command(
                    requested_command=config.requested_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                final_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                return TrackStateCliAttachmentUploadBoundaryValidationResult(
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
        config: TrackStateCliAttachmentUploadBoundaryConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / config.project_key / "project.json",
            (
                "{"
                f'"key":"{config.project_key}",'
                f'"name":"{config.project_name}"'
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

TS-387 duplicate file upload boundary fixture.
""",
        )
        self._write_binary_file(repository_path / config.source_file_paths[0], b"a")
        self._write_binary_file(repository_path / config.source_file_paths[1], b"b")
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-387 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts387@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-387 fixture")

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliAttachmentUploadBoundaryConfig,
    ) -> TrackStateCliAttachmentUploadBoundaryRepositoryState:
        issue_main = repository_path / config.project_key / config.issue_key / "main.md"
        attachment_directory = (
            repository_path / config.project_key / config.issue_key / "attachments"
        )
        uploaded_attachment_paths = (
            tuple(
                sorted(
                    str(path.relative_to(repository_path))
                    for path in attachment_directory.rglob("*")
                    if path.is_file()
                )
            )
            if attachment_directory.is_dir()
            else ()
        )
        return TrackStateCliAttachmentUploadBoundaryRepositoryState(
            issue_main_exists=issue_main.is_file(),
            attachment_directory_exists=attachment_directory.is_dir(),
            uploaded_attachment_paths=uploaded_attachment_paths,
            issue_main_content=self._read_text_if_exists(issue_main),
            git_status_lines=self._git_status_lines(repository_path),
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        lines = [line for line in output.splitlines() if line.strip()]
        return tuple(lines)

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0
