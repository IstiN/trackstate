from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_mixed_attachment_resolution_config import (
    TrackStateCliMixedAttachmentResolutionConfig,
)
from testing.core.interfaces.trackstate_cli_mixed_attachment_resolution_probe import (
    TrackStateCliMixedAttachmentResolutionProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_mixed_attachment_resolution_result import (
    TrackStateCliMixedAttachmentResolutionDownloadObservation,
    TrackStateCliMixedAttachmentResolutionRepositoryState,
    TrackStateCliMixedAttachmentResolutionValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliMixedAttachmentResolutionFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliMixedAttachmentResolutionProbe,
):
    def __init__(
        self,
        repository_root: Path,
        repository_client: LiveSetupRepositoryService,
    ) -> None:
        super().__init__(repository_root)
        self._repository_client = repository_client

    def observe_mixed_attachment_resolution(
        self,
        *,
        config: TrackStateCliMixedAttachmentResolutionConfig,
    ) -> TrackStateCliMixedAttachmentResolutionValidationResult:
        if not self._repository_client.token:
            raise AssertionError(
                "TS-485 requires GH_TOKEN or GITHUB_TOKEN so the local "
                "github-releases upload can authenticate against the live setup repository.",
            )

        release_tag_prefix = f"{config.github_release_tag_prefix}{uuid.uuid4().hex[:8]}-"
        expected_github_release_tag = f"{release_tag_prefix}{config.issue_key}"
        remote_origin_url = f"https://github.com/{self._repository_client.repository}.git"

        with tempfile.TemporaryDirectory(prefix="trackstate-ts-485-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-485-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                try:
                    self._seed_local_repository(
                        repository_path,
                        config=config,
                        release_tag_prefix=release_tag_prefix,
                        remote_origin_url=remote_origin_url,
                    )
                    initial_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    upload_observation = self._observe_command(
                        requested_command=config.requested_upload_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        scenario_name="TS-485 upload",
                        access_token=self._repository_client.token,
                    )
                    post_upload_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    download_command = self._rewrite_download_out_path(
                        requested_command=config.requested_download_command,
                    )
                    download_observation = self._observe_command(
                        requested_command=download_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        scenario_name="TS-485 download",
                        access_token=self._repository_client.token,
                    )
                    saved_file = repository_path / "downloads" / config.legacy_attachment_name
                    return TrackStateCliMixedAttachmentResolutionValidationResult(
                        initial_state=initial_state,
                        post_upload_state=post_upload_state,
                        upload_observation=upload_observation,
                        download_observation=TrackStateCliMixedAttachmentResolutionDownloadObservation(
                            command_observation=download_observation,
                            saved_file_absolute_path=str(saved_file.resolve()),
                            saved_file_exists=saved_file.is_file(),
                            saved_file_bytes=saved_file.read_bytes()
                            if saved_file.is_file()
                            else None,
                        ),
                        expected_github_release_tag=expected_github_release_tag,
                        remote_origin_url=remote_origin_url,
                    )
                finally:
                    self._cleanup_release_if_present(expected_github_release_tag)

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        scenario_name: str,
        access_token: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        return TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=(
                f"Pinned execution to a temporary executable compiled from this checkout "
                f"so {scenario_name} runs against the seeded local repository as the "
                "current working directory with GitHub credentials injected for the "
                "release-backed upload path."
            ),
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=self._run_with_environment(
                executed_command,
                cwd=repository_path,
                access_token=access_token,
            ),
        )

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliMixedAttachmentResolutionConfig,
        release_tag_prefix: str,
        remote_origin_url: str,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / config.project_key / "project.json",
            json.dumps(
                {
                    "key": config.project_key,
                    "name": config.project_name,
                    "attachmentStorage": {
                        "mode": config.expected_new_backend,
                        "githubReleases": {
                            "tagPrefix": release_tag_prefix,
                        },
                    },
                }
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
            repository_path / config.issue_main_relative_path,
            f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
summary: "{config.issue_summary}"
updated: {config.legacy_attachment_created_at}
---

# Description

TS-485 mixed attachment backend fixture.
""",
        )
        self._write_binary_file(
            repository_path / config.legacy_attachment_relative_path,
            config.legacy_attachment_bytes,
        )
        self._write_binary_file(
            repository_path / config.new_attachment_name,
            config.new_attachment_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-485 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts485@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", remote_origin_url)
        legacy_revision = self._git_output(
            repository_path,
            "hash-object",
            config.legacy_attachment_relative_path,
        ).strip()
        self._write_file(
            repository_path / config.manifest_relative_path,
            json.dumps(
                [
                    {
                        "id": config.legacy_attachment_relative_path,
                        "name": config.legacy_attachment_name,
                        "mediaType": "application/pdf",
                        "sizeBytes": len(config.legacy_attachment_bytes),
                        "author": config.legacy_attachment_author,
                        "createdAt": config.legacy_attachment_created_at,
                        "storagePath": config.legacy_attachment_relative_path,
                        "revisionOrOid": legacy_revision,
                        "storageBackend": config.expected_legacy_backend,
                        "repositoryPath": config.legacy_attachment_relative_path,
                    },
                ]
            )
            + "\n",
        )
        self._git(repository_path, "add", ".")
        self._git(
            repository_path,
            "commit",
            "-m",
            "Seed TS-485 mixed attachment backend fixture",
        )

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliMixedAttachmentResolutionConfig,
    ) -> TrackStateCliMixedAttachmentResolutionRepositoryState:
        issue_main = repository_path / config.issue_main_relative_path
        manifest_path = repository_path / config.manifest_relative_path
        legacy_attachment = repository_path / config.legacy_attachment_relative_path
        new_attachment_source = repository_path / config.new_attachment_name
        attachments_dir = repository_path / config.project_key / config.issue_key / "attachments"
        remote_names = tuple(
            line.strip()
            for line in self._git_output(repository_path, "remote").splitlines()
            if line.strip()
        )
        remote_origin_url = (
            self._git_output(repository_path, "remote", "get-url", "origin").strip()
            if "origin" in remote_names
            else None
        )
        attachment_paths = (
            tuple(
                sorted(
                    str(path.relative_to(repository_path))
                    for path in attachments_dir.rglob("*")
                    if path.is_file()
                )
            )
            if attachments_dir.is_dir()
            else ()
        )
        return TrackStateCliMixedAttachmentResolutionRepositoryState(
            issue_main_exists=issue_main.is_file(),
            manifest_exists=manifest_path.is_file(),
            manifest_text=self._read_text_if_exists(manifest_path),
            legacy_attachment_exists=legacy_attachment.is_file(),
            new_attachment_source_exists=new_attachment_source.is_file(),
            project_json_text=self._read_text_if_exists(
                repository_path / config.project_key / "project.json"
            ),
            attachment_file_paths=attachment_paths,
            remote_origin_url=remote_origin_url or None,
            git_status_lines=self._git_status_lines(repository_path),
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    @staticmethod
    def _rewrite_download_out_path(
        *,
        requested_command: tuple[str, ...],
    ) -> tuple[str, ...]:
        return requested_command

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0

    def _run_with_environment(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        access_token: str,
    ) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        env["TRACKSTATE_TOKEN"] = access_token
        env["GH_TOKEN"] = access_token
        env["GITHUB_TOKEN"] = access_token
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return CliCommandResult(
            command=command,
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=self._parse_json(completed.stdout),
        )

    def _cleanup_release_if_present(self, release_tag: str) -> None:
        release = self._repository_client.fetch_release_by_tag_any_state(release_tag)
        if release is None:
            return
        for asset in release.assets:
            self._repository_client.delete_release_asset(asset.id)
        self._repository_client.delete_release(release.id)
