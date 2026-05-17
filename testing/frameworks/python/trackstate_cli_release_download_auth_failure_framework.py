from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_release_download_auth_failure_config import (
    TrackStateCliReleaseDownloadAuthFailureConfig,
)
from testing.core.interfaces.trackstate_cli_release_download_auth_failure_probe import (
    TrackStateCliReleaseDownloadAuthFailureProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_download_auth_failure_result import (
    TrackStateCliReleaseDownloadAuthFailureRepositoryState,
    TrackStateCliReleaseDownloadAuthFailureValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseDownloadAuthFailureFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseDownloadAuthFailureProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_release_download_auth_failure(
        self,
        *,
        config: TrackStateCliReleaseDownloadAuthFailureConfig,
    ) -> TrackStateCliReleaseDownloadAuthFailureValidationResult:
        with self._materialize_source_tree(config.compiled_source_ref) as source_root:
            with tempfile.TemporaryDirectory(
                prefix="trackstate-release-download-auth-bin-"
            ) as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path, source_root=source_root)
                with tempfile.TemporaryDirectory(
                    prefix="trackstate-release-download-auth-repo-"
                ) as temp_dir:
                    repository_path = Path(temp_dir)
                    self._seed_local_repository(repository_path, config=config)
                    initial_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    observation, stripped_environment_variables = self._observe_command(
                        compiled_source_ref=config.compiled_source_ref,
                        requested_command=config.requested_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                    )
                    final_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    return TrackStateCliReleaseDownloadAuthFailureValidationResult(
                        initial_state=initial_state,
                        final_state=final_state,
                        observation=observation,
                        stripped_environment_variables=stripped_environment_variables,
                    )

    def _observe_command(
        self,
        *,
        compiled_source_ref: str,
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
        with tempfile.TemporaryDirectory(
            prefix="trackstate-release-download-auth-home-"
        ) as home_dir:
            sandbox_home = Path(home_dir)
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
                "Pinned execution to a temporary executable compiled from the configured "
                "source ref "
                f"({compiled_source_ref}) "
                "and stripped GitHub credentials from the environment so the "
                "release-backed local download scenario runs without ambient auth."
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
        config: TrackStateCliReleaseDownloadAuthFailureConfig,
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

{config.project_name} local github-releases attachment download fixture.
""",
        )
        self._write_file(
            repository_path / config.project_key / config.issue_key / "attachments.json",
            json.dumps(
                [
                    {
                        "id": config.attachment_relative_path,
                        "name": config.attachment_name,
                        "mediaType": config.attachment_media_type,
                        "sizeBytes": config.attachment_size_bytes,
                        "author": config.attachment_author,
                        "createdAt": config.attachment_created_at,
                        "storagePath": config.attachment_relative_path,
                        "revisionOrOid": config.attachment_revision_or_oid,
                        "storageBackend": "github-releases",
                        "githubReleaseTag": config.attachment_release_tag,
                        "githubReleaseAssetName": config.attachment_release_asset_name,
                    }
                ],
                indent=2,
            )
            + "\n",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.name",
            "Release Download Auth Tester",
        )
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "release-download-auth@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", config.remote_origin_url)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", f"Seed {config.project_key} fixture")

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseDownloadAuthFailureConfig,
    ) -> TrackStateCliReleaseDownloadAuthFailureRepositoryState:
        issue_main = repository_path / config.project_key / config.issue_key / "main.md"
        attachments_metadata_path = (
            repository_path / config.project_key / config.issue_key / "attachments.json"
        )
        metadata_attachment_ids = self._metadata_attachment_ids(attachments_metadata_path)
        expected_output = repository_path / config.expected_output_relative_path
        downloads_directory = expected_output.parent
        remote_origin_url = self._git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip()
        return TrackStateCliReleaseDownloadAuthFailureRepositoryState(
            issue_main_exists=issue_main.is_file(),
            attachments_metadata_exists=attachments_metadata_path.is_file(),
            metadata_attachment_ids=metadata_attachment_ids,
            expected_output_exists=expected_output.is_file(),
            expected_output_size_bytes=(
                expected_output.stat().st_size if expected_output.is_file() else None
            ),
            downloads_directory_exists=downloads_directory.is_dir(),
            git_status_lines=self._git_status_lines(repository_path),
            remote_origin_url=remote_origin_url or None,
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _metadata_attachment_ids(self, metadata_path: Path) -> tuple[str, ...]:
        if not metadata_path.is_file():
            return ()
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return ()
        if not isinstance(payload, list):
            return ()
        attachment_ids: list[str] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            attachment_id = entry.get("id")
            if isinstance(attachment_id, str) and attachment_id:
                attachment_ids.append(attachment_id)
        return tuple(attachment_ids)

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0
