from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveHostedRelease,
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_release_asset_filename_sanitization_config import (
    TrackStateCliReleaseAssetFilenameSanitizationConfig,
)
from testing.core.interfaces.trackstate_cli_release_asset_filename_sanitization_probe import (
    TrackStateCliReleaseAssetFilenameSanitizationProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_asset_filename_sanitization_result import (
    TrackStateCliReleaseAssetFilenameSanitizationCleanupResult,
    TrackStateCliReleaseAssetFilenameSanitizationGhReleaseViewObservation,
    TrackStateCliReleaseAssetFilenameSanitizationManifestObservation,
    TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation,
    TrackStateCliReleaseAssetFilenameSanitizationRepositoryState,
    TrackStateCliReleaseAssetFilenameSanitizationStoredFile,
    TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
)
from testing.core.utils.polling import poll_until
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseAssetFilenameSanitizationFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseAssetFilenameSanitizationProbe,
):
    def __init__(
        self,
        repository_root: Path,
        repository_client: LiveSetupRepositoryService,
    ) -> None:
        super().__init__(repository_root)
        self._repository_client = repository_client

    def observe_release_asset_filename_sanitization(
        self,
        *,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationValidationResult:
        if not self._repository_client.token:
            raise AssertionError(
                "Release asset sanitization scenarios require GH_TOKEN or "
                "GITHUB_TOKEN so the live GitHub Release asset state can be verified.",
            )

        release_tag_prefix = f"{config.release_tag_prefix_base}{uuid.uuid4().hex[:8]}-"
        expected_release_tag = f"{release_tag_prefix}{config.issue_key}"
        remote_origin_url = f"https://github.com/{self._repository_client.repository}.git"

        cleanup = TrackStateCliReleaseAssetFilenameSanitizationCleanupResult(
            status="no-release",
            release_tag=expected_release_tag,
            deleted_asset_names=(),
        )

        with tempfile.TemporaryDirectory(
            prefix="trackstate-release-sanitization-bin-",
        ) as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(
                prefix="trackstate-release-sanitization-repo-",
            ) as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(
                    repository_path=repository_path,
                    config=config,
                    release_tag_prefix=release_tag_prefix,
                    remote_origin_url=remote_origin_url,
                )
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )
                observation = self._observe_command(
                    requested_command=config.requested_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    access_token=self._repository_client.token,
                )
                final_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                )

                manifest_observation: (
                    TrackStateCliReleaseAssetFilenameSanitizationManifestObservation | None
                ) = None
                release_observation: (
                    TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation | None
                ) = None
                gh_release_view: (
                    TrackStateCliReleaseAssetFilenameSanitizationGhReleaseViewObservation | None
                ) = None

                try:
                    if observation.result.succeeded:
                        _, manifest_observation = poll_until(
                            probe=lambda: self._observe_manifest_state(
                                repository_path=repository_path,
                                config=config,
                                expected_release_tag=expected_release_tag,
                            ),
                            is_satisfied=lambda value: value.matches_expected,
                            timeout_seconds=config.manifest_poll_timeout_seconds,
                            interval_seconds=config.manifest_poll_interval_seconds,
                        )
                        _, release_observation = poll_until(
                            probe=lambda: self._observe_release_state(
                                config=config,
                                expected_release_tag=expected_release_tag,
                            ),
                            is_satisfied=lambda value: value.matches_expected,
                            timeout_seconds=config.release_poll_timeout_seconds,
                            interval_seconds=config.release_poll_interval_seconds,
                        )
                        if release_observation.release_present:
                            gh_release_view = self._observe_gh_release_view(
                                release_tag=expected_release_tag,
                                expected_asset_name=config.expected_sanitized_asset_name,
                            )
                    else:
                        release_observation = self._observe_release_state(
                            config=config,
                            expected_release_tag=expected_release_tag,
                        )
                finally:
                    cleanup = self._cleanup_release_if_present(expected_release_tag)

        return TrackStateCliReleaseAssetFilenameSanitizationValidationResult(
            initial_state=initial_state,
            final_state=final_state,
            observation=observation,
            expected_release_tag=expected_release_tag,
            release_tag_prefix=release_tag_prefix,
            remote_origin_url=remote_origin_url,
            manifest_observation=manifest_observation,
            release_observation=release_observation,
            gh_release_view=gh_release_view,
            cleanup=cleanup,
        )

    def _seed_local_repository(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
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
                        "mode": "github-releases",
                        "githubReleases": {"tagPrefix": release_tag_prefix},
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
priority: medium
assignee: tester
reporter: tester
updated: 2026-05-13T00:00:00Z
---

# Description

Release asset sanitization fixture.
""",
        )
        self._write_binary_file(
            repository_path / config.source_file_name,
            config.source_file_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.name",
            "TrackState Release Sanitization Tester",
        )
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "release-sanitization@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", remote_origin_url)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed release asset sanitization fixture")

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationRepositoryState:
        issue_main = repository_path / config.project_key / config.issue_key / "main.md"
        manifest_path = repository_path / config.manifest_path
        attachments_directory = (
            repository_path / config.project_key / config.issue_key / "attachments"
        )
        source_path = repository_path / config.source_file_name
        stored_files = (
            tuple(
                sorted(
                    (
                        TrackStateCliReleaseAssetFilenameSanitizationStoredFile(
                            relative_path=str(path.relative_to(repository_path)),
                            size_bytes=path.stat().st_size,
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                        )
                        for path in attachments_directory.rglob("*")
                        if path.is_file()
                    ),
                    key=lambda entry: entry.relative_path,
                )
            )
            if attachments_directory.is_dir()
            else ()
        )
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
        return TrackStateCliReleaseAssetFilenameSanitizationRepositoryState(
            issue_main_exists=issue_main.is_file(),
            source_file_exists=source_path.is_file(),
            manifest_exists=manifest_path.is_file(),
            manifest_text=self._read_text_if_exists(manifest_path),
            attachments_directory_exists=attachments_directory.is_dir(),
            stored_files=stored_files,
            git_status_lines=self._git_status_lines(repository_path),
            remote_origin_url=remote_origin_url or None,
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        access_token: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        return TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this checkout "
                "and injected GitHub credentials so the release asset sanitization "
                "scenario can run the exact local github-releases upload command "
                "from a disposable repository."
            ),
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=self._run_with_environment(
                executed_command,
                cwd=repository_path,
                access_token=access_token,
            ),
        )

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

    def _observe_manifest_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationManifestObservation:
        manifest_path = repository_path / config.manifest_path
        if not manifest_path.is_file():
            return TrackStateCliReleaseAssetFilenameSanitizationManifestObservation(
                manifest_exists=False,
                manifest_text=None,
                matching_entry=None,
                raw_asset_names=(),
                matches_expected=False,
            )

        manifest_text = manifest_path.read_text(encoding="utf-8")
        entries = json.loads(manifest_text)
        if not isinstance(entries, list):
            raise AssertionError(
                "Release asset sanitization expected "
                f"{config.manifest_path} to deserialize to a JSON array.",
            )

        matching_entries = [
            entry
            for entry in entries
            if isinstance(entry, dict)
            and str(entry.get("name", "")) == config.source_file_name
        ]
        matching_entry = matching_entries[0] if len(matching_entries) == 1 else None
        raw_asset_names = tuple(
            str(entry.get("githubReleaseAssetName", ""))
            for entry in entries
            if isinstance(entry, dict)
        )
        matches_expected = (
            matching_entry is not None
            and str(matching_entry.get("storageBackend", "")) == "github-releases"
            and str(matching_entry.get("githubReleaseTag", "")) == expected_release_tag
            and str(matching_entry.get("githubReleaseAssetName", ""))
            == config.expected_sanitized_asset_name
            and config.source_file_name not in raw_asset_names
        )
        return TrackStateCliReleaseAssetFilenameSanitizationManifestObservation(
            manifest_exists=True,
            manifest_text=manifest_text,
            matching_entry=matching_entry,
            raw_asset_names=raw_asset_names,
            matches_expected=matches_expected,
        )

    def _observe_release_state(
        self,
        *,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation:
        release = self._repository_client.fetch_release_by_tag_any_state(expected_release_tag)
        if release is None:
            return TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation(
                release_present=False,
                release_id=None,
                release_tag=expected_release_tag,
                release_name=None,
                release_draft=None,
                asset_names=(),
                asset_ids=(),
                downloaded_asset_sha256=None,
                downloaded_asset_size_bytes=None,
                download_error=None,
                matches_expected=False,
            )

        asset_names = tuple(asset.name for asset in release.assets)
        asset_ids = tuple(asset.id for asset in release.assets)
        downloaded_asset_sha256: str | None = None
        downloaded_asset_size_bytes: int | None = None
        download_error: str | None = None
        if len(release.assets) == 1:
            try:
                asset_bytes = self._repository_client.download_release_asset_bytes(
                    release.assets[0].id,
                )
            except Exception as error:
                download_error = f"{type(error).__name__}: {error}"
            else:
                downloaded_asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()
                downloaded_asset_size_bytes = len(asset_bytes)

        expected_sha256 = hashlib.sha256(config.source_file_bytes).hexdigest()
        matches_expected = (
            release.tag_name == expected_release_tag
            and asset_names == (config.expected_sanitized_asset_name,)
            and config.source_file_name not in asset_names
            and downloaded_asset_sha256 == expected_sha256
            and downloaded_asset_size_bytes == len(config.source_file_bytes)
            and not download_error
        )
        return TrackStateCliReleaseAssetFilenameSanitizationReleaseObservation(
            release_present=True,
            release_id=release.id,
            release_tag=release.tag_name,
            release_name=release.name,
            release_draft=release.draft,
            asset_names=asset_names,
            asset_ids=asset_ids,
            downloaded_asset_sha256=downloaded_asset_sha256,
            downloaded_asset_size_bytes=downloaded_asset_size_bytes,
            download_error=download_error,
            matches_expected=matches_expected,
        )

    def _observe_gh_release_view(
        self,
        *,
        release_tag: str,
        expected_asset_name: str,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationGhReleaseViewObservation:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        if self._repository_client.token:
            env["GH_TOKEN"] = self._repository_client.token
            env["GITHUB_TOKEN"] = self._repository_client.token
        completed = subprocess.run(
            (
                "gh",
                "release",
                "view",
                release_tag,
                "--repo",
                self._repository_client.repository,
                "--json",
                "tagName,name,isDraft,assets",
            ),
            cwd=self._repository_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        payload = self._parse_json(completed.stdout)
        assets = payload.get("assets") if isinstance(payload, dict) else None
        asset_names = tuple(
            str(asset.get("name", "")).strip()
            for asset in assets
            if isinstance(asset, dict) and str(asset.get("name", "")).strip()
        ) if isinstance(assets, list) else ()
        return TrackStateCliReleaseAssetFilenameSanitizationGhReleaseViewObservation(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            json_payload=payload,
            asset_names=asset_names,
            matches_expected=(
                completed.returncode == 0 and asset_names == (expected_asset_name,)
            ),
        )

    def _cleanup_release_if_present(
        self,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationCleanupResult:
        try:
            release = self._repository_client.fetch_release_by_tag_any_state(
                expected_release_tag,
            )
            if release is None:
                return TrackStateCliReleaseAssetFilenameSanitizationCleanupResult(
                    status="no-release",
                    release_tag=expected_release_tag,
                    deleted_asset_names=(),
                )
            for asset in release.assets:
                self._repository_client.delete_release_asset(asset.id)
            self._repository_client.delete_release(release.id)
            matched, _ = poll_until(
                probe=lambda: self._repository_client.fetch_release_by_tag_any_state(
                    expected_release_tag,
                ),
                is_satisfied=lambda value: value is None,
                timeout_seconds=60,
                interval_seconds=3,
            )
            if not matched:
                raise AssertionError(
                    f"Cleanup failed: release tag {expected_release_tag} still exists after delete.",
                )
            return TrackStateCliReleaseAssetFilenameSanitizationCleanupResult(
                status="deleted-release",
                release_tag=expected_release_tag,
                deleted_asset_names=tuple(asset.name for asset in release.assets),
            )
        except Exception as error:
            return TrackStateCliReleaseAssetFilenameSanitizationCleanupResult(
                status="cleanup-failed",
                release_tag=expected_release_tag,
                deleted_asset_names=(),
                error=f"{type(error).__name__}: {error}",
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
