from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_release_download_success_config import (
    TrackStateCliReleaseDownloadSuccessConfig,
)
from testing.core.interfaces.trackstate_cli_release_download_success_probe import (
    TrackStateCliReleaseDownloadSuccessProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_download_success_result import (
    TrackStateCliReleaseDownloadSuccessFixture,
    TrackStateCliReleaseDownloadSuccessRepositoryState,
    TrackStateCliReleaseDownloadSuccessValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseDownloadSuccessFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseDownloadSuccessProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_release_download_success(
        self,
        *,
        config: TrackStateCliReleaseDownloadSuccessConfig,
        fixture: TrackStateCliReleaseDownloadSuccessFixture,
        token: str,
    ) -> TrackStateCliReleaseDownloadSuccessValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-540-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-540-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(
                    repository_path=repository_path,
                    config=config,
                    fixture=fixture,
                )
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                observation, stripped_environment_variables = self._observe_command(
                    requested_command=config.requested_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    token=token,
                )
                final_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                saved_file = repository_path / config.expected_output_relative_path
                return TrackStateCliReleaseDownloadSuccessValidationResult(
                    initial_state=initial_state,
                    final_state=final_state,
                    observation=observation,
                    saved_file_absolute_path=str(saved_file.resolve()),
                    saved_file_bytes=saved_file.read_bytes() if saved_file.is_file() else None,
                    stripped_environment_variables=stripped_environment_variables,
                )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        token: str,
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
        env["TRACKSTATE_TOKEN"] = token
        sandbox_home = repository_path / ".ts540-home"
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
                "and injected the GitHub credential through TRACKSTATE_TOKEN so TS-540 "
                "runs the release-backed local download path deterministically."
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
        *,
        repository_path: Path,
        config: TrackStateCliReleaseDownloadSuccessConfig,
        fixture: TrackStateCliReleaseDownloadSuccessFixture,
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
            repository_path / config.issue_path / "main.md",
            f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
summary: "{config.issue_summary}"
assignee: tester
reporter: tester
updated: {config.attachment_created_at}
---

# Description

TS-540 local github-releases attachment download success fixture.
""",
        )
        self._write_file(
            repository_path / config.manifest_path,
            json.dumps(
                [
                    {
                        "id": config.attachment_relative_path,
                        "name": config.attachment_name,
                        "mediaType": config.attachment_media_type,
                        "sizeBytes": len(fixture.asset_bytes),
                        "author": config.attachment_author,
                        "createdAt": config.attachment_created_at,
                        "storagePath": config.attachment_relative_path,
                        "revisionOrOid": config.attachment_revision_or_oid,
                        "storageBackend": "github-releases",
                        "githubReleaseTag": fixture.tag_name,
                        "githubReleaseAssetName": fixture.asset_name,
                    }
                ],
                indent=2,
            )
            + "\n",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-540 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts540@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", fixture.remote_origin_url)
        git_environment = {
            "GIT_AUTHOR_NAME": "TS-540 Tester",
            "GIT_AUTHOR_EMAIL": "ts540@example.com",
            "GIT_AUTHOR_DATE": config.attachment_created_at,
            "GIT_COMMITTER_NAME": "TS-540 Tester",
            "GIT_COMMITTER_EMAIL": "ts540@example.com",
            "GIT_COMMITTER_DATE": config.attachment_created_at,
        }
        self._git(repository_path, "add", ".", env=git_environment)
        self._git(
            repository_path,
            "commit",
            "-m",
            "Seed TS-540 release-backed local download fixture",
            env=git_environment,
        )

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseDownloadSuccessConfig,
    ) -> TrackStateCliReleaseDownloadSuccessRepositoryState:
        issue_main = repository_path / config.issue_path / "main.md"
        attachments_metadata_path = repository_path / config.manifest_path
        metadata = self._metadata_summary(attachments_metadata_path)
        expected_output = repository_path / config.expected_output_relative_path
        downloads_directory = expected_output.parent
        remote_origin_url = self._git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip()
        return TrackStateCliReleaseDownloadSuccessRepositoryState(
            issue_main_exists=issue_main.is_file(),
            attachments_metadata_exists=attachments_metadata_path.is_file(),
            metadata_attachment_ids=metadata["attachment_ids"],
            metadata_storage_backends=metadata["storage_backends"],
            metadata_release_tags=metadata["release_tags"],
            metadata_release_asset_names=metadata["release_asset_names"],
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

    def _metadata_summary(self, metadata_path: Path) -> dict[str, tuple[str, ...]]:
        empty: tuple[str, ...] = ()
        if not metadata_path.is_file():
            return {
                "attachment_ids": empty,
                "storage_backends": empty,
                "release_tags": empty,
                "release_asset_names": empty,
            }
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {
                "attachment_ids": empty,
                "storage_backends": empty,
                "release_tags": empty,
                "release_asset_names": empty,
            }
        if not isinstance(payload, list):
            return {
                "attachment_ids": empty,
                "storage_backends": empty,
                "release_tags": empty,
                "release_asset_names": empty,
            }
        attachment_ids: list[str] = []
        storage_backends: list[str] = []
        release_tags: list[str] = []
        release_asset_names: list[str] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            attachment_id = entry.get("id")
            storage_backend = entry.get("storageBackend")
            release_tag = entry.get("githubReleaseTag")
            release_asset_name = entry.get("githubReleaseAssetName")
            if isinstance(attachment_id, str) and attachment_id:
                attachment_ids.append(attachment_id)
            if isinstance(storage_backend, str) and storage_backend:
                storage_backends.append(storage_backend)
            if isinstance(release_tag, str) and release_tag:
                release_tags.append(release_tag)
            if isinstance(release_asset_name, str) and release_asset_name:
                release_asset_names.append(release_asset_name)
        return {
            "attachment_ids": tuple(attachment_ids),
            "storage_backends": tuple(storage_backends),
            "release_tags": tuple(release_tags),
            "release_asset_names": tuple(release_asset_names),
        }

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0
