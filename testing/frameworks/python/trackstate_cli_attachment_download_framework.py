from __future__ import annotations

import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_attachment_download_config import (
    TrackStateCliAttachmentDownloadConfig,
)
from testing.core.interfaces.trackstate_cli_attachment_download_probe import (
    TrackStateCliAttachmentDownloadProbe,
)
from testing.core.models.trackstate_cli_attachment_download_result import (
    TrackStateCliAttachmentDownloadObservation,
    TrackStateCliAttachmentDownloadValidationResult,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliAttachmentDownloadFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliAttachmentDownloadProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_attachment_download(
        self,
        *,
        config: TrackStateCliAttachmentDownloadConfig,
    ) -> TrackStateCliAttachmentDownloadValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-382-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-382-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                requested_command = config.requested_command
                executed_command = (
                    str(executable_path),
                    *requested_command[1:],
                )
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    "checkout so TS-382 runs the exact attachment-download command "
                    "against the seeded Local Git repository from the repository "
                    "working directory."
                )
                observation = TrackStateCliCommandObservation(
                    requested_command=requested_command,
                    executed_command=executed_command,
                    fallback_reason=fallback_reason,
                    repository_path=str(repository_path),
                    compiled_binary_path=str(executable_path),
                    result=self._run(executed_command, cwd=repository_path),
                )
                saved_file = repository_path / "downloads" / "downloaded_file.png"
                saved_file_bytes = saved_file.read_bytes() if saved_file.is_file() else None
                attachment_blob_sha = self._git_output(
                    repository_path,
                    "rev-parse",
                    f"HEAD:{config.attachment_relative_path}",
                ).strip()
                git_status_lines = tuple(
                    line
                    for line in self._git_output(
                        repository_path,
                        "status",
                        "--short",
                    ).splitlines()
                    if line.strip()
                )
                return TrackStateCliAttachmentDownloadValidationResult(
                    observation=TrackStateCliAttachmentDownloadObservation(
                        command_observation=observation,
                        attachment_id=config.attachment_relative_path,
                        attachment_name=config.attachment_name,
                        attachment_media_type=config.attachment_media_type,
                        attachment_relative_path=config.attachment_relative_path,
                        attachment_created_at=config.attachment_created_at,
                        attachment_blob_sha=attachment_blob_sha,
                        attachment_bytes=config.attachment_bytes,
                        attachment_base64=config.attachment_base64,
                        output_file_argument=config.output_file_argument,
                        saved_file_absolute_path=str(saved_file.resolve()),
                        saved_file_exists=saved_file.is_file(),
                        saved_file_bytes=saved_file_bytes,
                        git_status_lines=git_status_lines,
                    )
                )

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliAttachmentDownloadConfig,
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
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/{config.issue_key}/main.md",
            f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
summary: "{config.issue_summary}"
assignee: ts382@example.com
reporter: ts382@example.com
updated: {config.attachment_created_at}
---

# Summary

{config.issue_summary}

# Description

TS-382 seeded attachment download fixture.
""",
        )
        self._write_binary_file(
            repository_path / config.attachment_relative_path,
            config.attachment_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-382 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts382@example.com",
        )
        git_environment = {
            "GIT_AUTHOR_NAME": "TS-382 Tester",
            "GIT_AUTHOR_EMAIL": "ts382@example.com",
            "GIT_AUTHOR_DATE": config.attachment_created_at,
            "GIT_COMMITTER_NAME": "TS-382 Tester",
            "GIT_COMMITTER_EMAIL": "ts382@example.com",
            "GIT_COMMITTER_DATE": config.attachment_created_at,
        }
        self._git(repository_path, "add", ".", env=git_environment)
        self._git(
            repository_path,
            "commit",
            "-m",
            "Seed TS-382 attachment download fixture",
            env=git_environment,
        )
