from __future__ import annotations

import hashlib
import json
import os
import tempfile
import uuid
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_release_replacement_config import (
    TrackStateCliReleaseReplacementConfig,
)
from testing.core.interfaces.trackstate_cli_release_replacement_probe import (
    TrackStateCliReleaseReplacementProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_replacement_result import (
    TrackStateCliReleaseReplacementCleanupResult,
    TrackStateCliReleaseReplacementManifestObservation,
    TrackStateCliReleaseReplacementReleaseObservation,
    TrackStateCliReleaseReplacementRepositoryState,
    TrackStateCliReleaseReplacementSeededRelease,
    TrackStateCliReleaseReplacementValidationResult,
)
from testing.core.utils.polling import poll_until
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseReplacementFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseReplacementProbe,
):
    def __init__(
        self,
        repository_root: Path,
        repository_client: LiveSetupRepositoryService,
    ) -> None:
        super().__init__(repository_root)
        self._repository_client = repository_client

    def observe_release_replacement(
        self,
        *,
        config: TrackStateCliReleaseReplacementConfig,
    ) -> TrackStateCliReleaseReplacementValidationResult:
        if not self._repository_client.token:
            raise AssertionError(
                "Release replacement scenarios require GH_TOKEN or GITHUB_TOKEN so the "
                "live GitHub Release state can be seeded and verified.",
            )

        release_tag_prefix = f"{config.release_tag_prefix_base}{uuid.uuid4().hex[:8]}-"
        expected_release_tag = f"{release_tag_prefix}{config.issue_key}"
        remote_origin_url = f"https://github.com/{self._repository_client.repository}.git"
        cleanup = TrackStateCliReleaseReplacementCleanupResult(
            status="no-release",
            release_tag=expected_release_tag,
            deleted_release_ids=(),
            deleted_asset_ids=(),
        )

        with tempfile.TemporaryDirectory(
            prefix="trackstate-release-replacement-bin-",
        ) as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(
                prefix="trackstate-release-replacement-repo-",
            ) as temp_dir:
                repository_path = Path(temp_dir)
                seeded_release = self._seed_release_container(
                    config=config,
                    expected_release_tag=expected_release_tag,
                )
                self._seed_local_repository(
                    repository_path=repository_path,
                    config=config,
                    remote_origin_url=remote_origin_url,
                    expected_release_tag=expected_release_tag,
                    seeded_asset_id=str(seeded_release.asset_id),
                )
                initial_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                    expected_release_tag=expected_release_tag,
                )
                observation = self._observe_command(
                    config=config,
                    requested_command=config.requested_command,
                    repository_path=repository_path,
                    executable_path=executable_path,
                    access_token=self._repository_client.token,
                )
                final_state = self._capture_repository_state(
                    repository_path=repository_path,
                    config=config,
                    expected_release_tag=expected_release_tag,
                )

                manifest_observation: (
                    TrackStateCliReleaseReplacementManifestObservation | None
                ) = None
                release_observation: (
                    TrackStateCliReleaseReplacementReleaseObservation | None
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
                    else:
                        manifest_observation = self._observe_manifest_state(
                            repository_path=repository_path,
                            config=config,
                            expected_release_tag=expected_release_tag,
                        )
                        release_observation = self._observe_release_state(
                            config=config,
                            expected_release_tag=expected_release_tag,
                        )
                finally:
                    cleanup = self._cleanup_release_if_present(expected_release_tag)

        return TrackStateCliReleaseReplacementValidationResult(
            seeded_release=seeded_release,
            initial_state=initial_state,
            final_state=final_state,
            observation=observation,
            expected_release_tag=expected_release_tag,
            release_tag_prefix=release_tag_prefix,
            remote_origin_url=remote_origin_url,
            manifest_observation=manifest_observation,
            release_observation=release_observation,
            cleanup=cleanup,
        )

    def _seed_release_container(
        self,
        *,
        config: TrackStateCliReleaseReplacementConfig,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseReplacementSeededRelease:
        release = self._repository_client.create_release(
            tag_name=expected_release_tag,
            name=config.expected_release_title,
            body="Release replacement seeded fixture",
            draft=True,
        )
        asset = self._repository_client.upload_release_asset(
            release_id=release.id,
            asset_name=config.expected_attachment_name,
            content_type=config.attachment_media_type,
            content=config.seeded_attachment_bytes,
        )
        return TrackStateCliReleaseReplacementSeededRelease(
            release_id=release.id,
            release_tag=release.tag_name,
            release_name=release.name,
            asset_id=asset.id,
            asset_name=asset.name,
        )

    def _seed_local_repository(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseReplacementConfig,
        remote_origin_url: str,
        expected_release_tag: str,
        seeded_asset_id: str,
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
                        "githubReleases": {
                            "tagPrefix": expected_release_tag[: -len(config.issue_key)],
                        },
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
            repository_path / config.issue_main_path,
            f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
summary: "{config.issue_summary}"
priority: medium
assignee: tester
reporter: tester
updated: {config.seeded_attachment_created_at}
---

# Description

Release replacement fixture.
""",
        )
        self._write_file(
            repository_path / config.manifest_path,
            json.dumps(
                [
                    {
                        "id": config.expected_attachment_relative_path,
                        "name": config.expected_attachment_name,
                        "mediaType": config.attachment_media_type,
                        "sizeBytes": len(config.seeded_attachment_bytes),
                        "author": "tester",
                        "createdAt": config.seeded_attachment_created_at,
                        "storagePath": config.expected_attachment_relative_path,
                        "revisionOrOid": seeded_asset_id,
                        "storageBackend": "github-releases",
                        "githubReleaseTag": expected_release_tag,
                        "githubReleaseAssetName": config.expected_attachment_name,
                    }
                ],
                indent=2,
            )
            + "\n",
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
            "Release Replacement Tester",
        )
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "release-replacement@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", remote_origin_url)
        git_env = {
            "GIT_AUTHOR_NAME": "Release Replacement Tester",
            "GIT_AUTHOR_EMAIL": "release-replacement@example.com",
            "GIT_AUTHOR_DATE": config.seeded_attachment_created_at,
            "GIT_COMMITTER_NAME": "Release Replacement Tester",
            "GIT_COMMITTER_EMAIL": "release-replacement@example.com",
            "GIT_COMMITTER_DATE": config.seeded_attachment_created_at,
        }
        self._git(repository_path, "add", ".", env=git_env)
        self._git(
            repository_path,
            "commit",
            "-m",
            "Seed release replacement fixture",
            env=git_env,
        )

    def _observe_command(
        self,
        *,
        config: TrackStateCliReleaseReplacementConfig,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        access_token: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        for variable in ("GH_TOKEN", "GITHUB_TOKEN", "TRACKSTATE_TOKEN"):
            env.pop(variable, None)
        env["TRACKSTATE_TOKEN"] = access_token
        env["GH_TOKEN"] = access_token
        env["GITHUB_TOKEN"] = access_token
        sandbox_home = repository_path / ".release-replacement-home"
        sandbox_home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(sandbox_home)
        env["XDG_CONFIG_HOME"] = str(sandbox_home / ".config")
        env["GH_CONFIG_DIR"] = str(sandbox_home / ".config" / "gh")
        env["GIT_TERMINAL_PROMPT"] = "0"
        if config.delete_release_asset_override_status_code is not None:
            env["TRACKSTATE_CLI_FAIL_RELEASE_ASSET_DELETE_STATUS"] = str(
                config.delete_release_asset_override_status_code,
            )
            if config.delete_release_asset_override_body is not None:
                env["TRACKSTATE_CLI_FAIL_RELEASE_ASSET_DELETE_BODY"] = (
                    config.delete_release_asset_override_body
                )
        result = self._run(executed_command, cwd=repository_path, env=env)
        return TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this checkout "
                "and executed it from a disposable repository seeded through the dedicated "
                "release replacement framework."
            ),
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=result,
        )

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseReplacementConfig,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseReplacementRepositoryState:
        manifest_path = repository_path / config.manifest_path
        manifest_text = self._read_text_if_exists(manifest_path)
        matching_manifest_entries = self._matching_manifest_entries(
            manifest_text=manifest_text,
            expected_attachment_name=config.expected_attachment_name,
        )
        release = self._repository_client.fetch_release_by_tag_any_state(expected_release_tag)
        release_asset_names = tuple(asset.name for asset in release.assets) if release else ()
        release_asset_ids = tuple(asset.id for asset in release.assets) if release else ()
        downloaded_asset_id: int | None = None
        downloaded_asset_size_bytes: int | None = None
        downloaded_asset_sha256: str | None = None
        downloaded_asset_error: str | None = None
        if release is not None and len(release.assets) == 1:
            downloaded_asset_id = release.assets[0].id
            try:
                asset_bytes = self._repository_client.download_release_asset_bytes(
                    downloaded_asset_id,
                )
            except Exception as error:
                downloaded_asset_error = f"{type(error).__name__}: {error}"
            else:
                downloaded_asset_size_bytes = len(asset_bytes)
                downloaded_asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()
        remote_origin_url = self._git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip()
        return TrackStateCliReleaseReplacementRepositoryState(
            issue_main_exists=(repository_path / config.issue_main_path).is_file(),
            source_file_exists=(repository_path / config.source_file_name).is_file(),
            manifest_exists=manifest_path.is_file(),
            manifest_text=manifest_text,
            matching_manifest_entries=matching_manifest_entries,
            release_present=release is not None,
            release_id=release.id if release else None,
            release_tag=release.tag_name if release else None,
            release_title=release.name if release else None,
            release_asset_names=release_asset_names,
            release_asset_ids=release_asset_ids,
            release_asset_downloaded_id=downloaded_asset_id,
            release_asset_downloaded_size_bytes=downloaded_asset_size_bytes,
            release_asset_downloaded_sha256=downloaded_asset_sha256,
            release_asset_download_error=downloaded_asset_error,
            remote_origin_url=remote_origin_url or None,
            git_status_lines=self._git_status_lines(repository_path),
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _observe_manifest_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseReplacementConfig,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseReplacementManifestObservation:
        manifest_path = repository_path / config.manifest_path
        manifest_text = self._read_text_if_exists(manifest_path)
        matching_entries = self._matching_manifest_entries(
            manifest_text=manifest_text,
            expected_attachment_name=config.expected_attachment_name,
        )
        matching_entry = matching_entries[0] if len(matching_entries) == 1 else None
        matches_expected = False
        if matching_entry is not None:
            revision_or_oid = str(matching_entry.get("revisionOrOid", "")).strip()
            matches_expected = (
                str(matching_entry.get("id", "")) == config.expected_attachment_relative_path
                and str(matching_entry.get("storagePath", ""))
                == config.expected_attachment_relative_path
                and str(matching_entry.get("storageBackend", "")) == "github-releases"
                and str(matching_entry.get("githubReleaseTag", "")) == expected_release_tag
                and str(matching_entry.get("githubReleaseAssetName", ""))
                == config.expected_attachment_name
                and bool(revision_or_oid)
            )
        return TrackStateCliReleaseReplacementManifestObservation(
            manifest_exists=manifest_path.is_file(),
            manifest_text=manifest_text,
            matching_entry=matching_entry,
            entry_count=len(matching_entries),
            matches_expected=matches_expected,
        )

    def _observe_release_state(
        self,
        *,
        config: TrackStateCliReleaseReplacementConfig,
        expected_release_tag: str,
    ) -> TrackStateCliReleaseReplacementReleaseObservation:
        release = self._repository_client.fetch_release_by_tag_any_state(expected_release_tag)
        asset_names = tuple(asset.name for asset in release.assets) if release else ()
        asset_ids = tuple(asset.id for asset in release.assets) if release else ()
        downloaded_asset_sha256: str | None = None
        downloaded_asset_size_bytes: int | None = None
        download_error: str | None = None
        matches_expected = False
        if release is not None and len(release.assets) == 1:
            try:
                asset_bytes = self._repository_client.download_release_asset_bytes(
                    release.assets[0].id,
                )
            except Exception as error:
                download_error = f"{type(error).__name__}: {error}"
            else:
                downloaded_asset_size_bytes = len(asset_bytes)
                downloaded_asset_sha256 = hashlib.sha256(asset_bytes).hexdigest()
                matches_expected = (
                    asset_names == (config.expected_attachment_name,)
                    and downloaded_asset_size_bytes == len(config.source_file_bytes)
                    and downloaded_asset_sha256
                    == hashlib.sha256(config.source_file_bytes).hexdigest()
                )
        return TrackStateCliReleaseReplacementReleaseObservation(
            release_present=release is not None,
            release_id=release.id if release else None,
            release_tag=release.tag_name if release else None,
            release_name=release.name if release else None,
            asset_names=asset_names,
            asset_ids=asset_ids,
            downloaded_asset_sha256=downloaded_asset_sha256,
            downloaded_asset_size_bytes=downloaded_asset_size_bytes,
            download_error=download_error,
            matches_expected=matches_expected,
        )

    def _cleanup_release_if_present(
        self,
        release_tag: str,
    ) -> TrackStateCliReleaseReplacementCleanupResult:
        deleted_release_ids: list[int] = []
        deleted_asset_ids: list[int] = []
        try:
            releases = self._repository_client.fetch_releases_by_tag_any_state(release_tag)
            if not releases:
                return TrackStateCliReleaseReplacementCleanupResult(
                    status="no-release",
                    release_tag=release_tag,
                    deleted_release_ids=(),
                    deleted_asset_ids=(),
                )
            for release in releases:
                for asset in release.assets:
                    self._repository_client.delete_release_asset(asset.id)
                    deleted_asset_ids.append(asset.id)
                self._repository_client.delete_release(release.id)
                deleted_release_ids.append(release.id)
            matched, remaining = poll_until(
                probe=lambda: self._repository_client.fetch_releases_by_tag_any_state(
                    release_tag,
                ),
                is_satisfied=lambda value: len(value) == 0,
                timeout_seconds=120,
                interval_seconds=5,
            )
            if not matched:
                return TrackStateCliReleaseReplacementCleanupResult(
                    status="failed",
                    release_tag=release_tag,
                    deleted_release_ids=tuple(deleted_release_ids),
                    deleted_asset_ids=tuple(deleted_asset_ids),
                    error=(
                        "Release cleanup did not converge. Remaining releases: "
                        f"{[release.id for release in remaining]}"
                    ),
                )
            return TrackStateCliReleaseReplacementCleanupResult(
                status="deleted-release",
                release_tag=release_tag,
                deleted_release_ids=tuple(deleted_release_ids),
                deleted_asset_ids=tuple(deleted_asset_ids),
            )
        except Exception as error:
            return TrackStateCliReleaseReplacementCleanupResult(
                status="failed",
                release_tag=release_tag,
                deleted_release_ids=tuple(deleted_release_ids),
                deleted_asset_ids=tuple(deleted_asset_ids),
                error=f"{type(error).__name__}: {error}",
            )

    @staticmethod
    def _matching_manifest_entries(
        *,
        manifest_text: str | None,
        expected_attachment_name: str,
    ) -> tuple[dict[str, object], ...]:
        if manifest_text is None:
            return ()
        try:
            payload = json.loads(manifest_text)
        except json.JSONDecodeError:
            return ()
        if not isinstance(payload, list):
            return ()
        matches: list[dict[str, object]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            if str(entry.get("name", "")) == expected_attachment_name:
                matches.append(dict(entry))
        return tuple(matches)

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0
