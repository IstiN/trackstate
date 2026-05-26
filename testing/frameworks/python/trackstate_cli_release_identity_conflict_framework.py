from __future__ import annotations

import json
import os
import subprocess
import tempfile
import traceback
import urllib.error
from dataclasses import dataclass
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveHostedRelease,
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_release_identity_conflict_config import (
    TrackStateCliReleaseIdentityConflictConfig,
)
from testing.core.interfaces.trackstate_cli_release_identity_conflict_probe import (
    TrackStateCliReleaseIdentityConflictProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.hosted_repository_file import HostedRepositoryFile
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_identity_conflict_result import (
    TrackStateCliReleaseIdentityConflictRemoteState,
    TrackStateCliReleaseIdentityConflictValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


@dataclass(frozen=True)
class _RemoteFileSnapshot:
    path: str
    original_file: HostedRepositoryFile | None


@dataclass(frozen=True)
class _ReleaseCleanupPlan:
    created_release_id: int | None
    restore_release_id: int | None
    restore_name: str | None


class PythonTrackStateCliReleaseIdentityConflictFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseIdentityConflictProbe,
):
    def __init__(
        self,
        repository_root: Path,
        repository_client: LiveSetupRepositoryService,
    ) -> None:
        super().__init__(repository_root)
        self._repository_client = repository_client

    def observe(
        self,
        *,
        config: TrackStateCliReleaseIdentityConflictConfig,
    ) -> TrackStateCliReleaseIdentityConflictValidationResult:
        if not self._repository_client.token:
            raise AssertionError(
                "TS-503 requires GH_TOKEN or GITHUB_TOKEN so the hosted GitHub "
                "release-backed upload flow can be exercised against the live repository.",
            )

        snapshots = tuple(
            _RemoteFileSnapshot(
                path=path,
                original_file=self._fetch_repo_file_if_exists(path),
            )
            for path in config.cleanup_repo_paths
        )
        original_release = self._repository_client.fetch_release_by_tag(
            config.expected_release_tag,
        )
        setup_actions: list[str] = []
        cleanup_actions: list[str] = []
        cleanup_error: str | None = None

        release_cleanup = self._ensure_conflicting_release(
            config=config,
            original_release=original_release,
            setup_actions=setup_actions,
        )
        self._seed_fixture(config=config, setup_actions=setup_actions)

        initial_state: TrackStateCliReleaseIdentityConflictRemoteState | None = None
        final_state: TrackStateCliReleaseIdentityConflictRemoteState | None = None
        observation: TrackStateCliCommandObservation | None = None
        local_attachment_path = ""
        try:
            initial_state = self._capture_remote_state(config=config)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-503-bin-") as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                with tempfile.TemporaryDirectory(
                    prefix="trackstate-ts-503-workdir-",
                ) as work_dir:
                    working_directory = Path(work_dir)
                    attachment_path = working_directory / config.local_attachment_name
                    attachment_path.write_text(
                        config.local_attachment_content,
                        encoding="utf-8",
                    )
                    local_attachment_path = str(attachment_path)
                    observation = self._observe_command(
                        config=config,
                        repository_path=working_directory,
                        executable_path=executable_path,
                        access_token=self._repository_client.token,
                    )
            final_state = self._capture_remote_state(config=config)
        finally:
            try:
                self._restore_fixture(
                    snapshots=snapshots,
                    cleanup_actions=cleanup_actions,
                )
                self._restore_release(
                    config=config,
                    cleanup=release_cleanup,
                    cleanup_actions=cleanup_actions,
                )
            except Exception:
                cleanup_error = traceback.format_exc()

        if initial_state is None or final_state is None or observation is None:
            raise AssertionError(
                "TS-503 did not complete the hosted release identity conflict observation.\n"
                f"Cleanup error: {cleanup_error or '<none>'}",
            )

        return TrackStateCliReleaseIdentityConflictValidationResult(
            initial_state=initial_state,
            final_state=final_state,
            observation=observation,
            setup_actions=tuple(setup_actions),
            cleanup_actions=tuple(cleanup_actions),
            cleanup_error=cleanup_error,
            local_attachment_path=local_attachment_path,
        )

    def _ensure_conflicting_release(
        self,
        *,
        config: TrackStateCliReleaseIdentityConflictConfig,
        original_release: LiveHostedRelease | None,
        setup_actions: list[str],
    ) -> _ReleaseCleanupPlan:
        if original_release is None:
            created = self._repository_client.create_release(
                tag_name=config.expected_release_tag,
                name=config.conflicting_release_title,
                body="TS-503 mismatched release fixture",
                target_commitish=config.branch,
                draft=False,
            )
            setup_actions.append(
                f"created release {created.tag_name} titled {created.name!r}",
            )
            return _ReleaseCleanupPlan(
                created_release_id=created.id,
                restore_release_id=None,
                restore_name=None,
            )

        if original_release.name != config.conflicting_release_title:
            updated = self._repository_client.update_release_name(
                original_release.id,
                name=config.conflicting_release_title,
            )
            setup_actions.append(
                f"renamed release {updated.tag_name} from {original_release.name!r} "
                f"to {updated.name!r}",
            )
            return _ReleaseCleanupPlan(
                created_release_id=None,
                restore_release_id=original_release.id,
                restore_name=original_release.name,
            )

        setup_actions.append(
            f"reused existing conflicting release {original_release.tag_name} "
            f"titled {original_release.name!r}",
        )
        return _ReleaseCleanupPlan(
            created_release_id=None,
            restore_release_id=None,
            restore_name=None,
        )

    def _seed_fixture(
        self,
        *,
        config: TrackStateCliReleaseIdentityConflictConfig,
        setup_actions: list[str],
    ) -> None:
        seed_message = "Seed TS-503 release identity conflict fixture"

        project_json = json.loads(
            self._repository_client.fetch_repo_text(config.project_json_path),
        )
        if not isinstance(project_json, dict):
            raise AssertionError(
                f"Expected {config.project_json_path} to decode to an object.",
            )
        project_json["attachmentStorage"] = {
            "mode": "github-releases",
            "githubReleases": {
                "tagPrefix": config.release_tag_prefix,
            },
        }
        self._repository_client.write_repo_text(
            config.project_json_path,
            content=json.dumps(project_json, indent=2) + "\n",
            message=seed_message,
        )
        setup_actions.append(
            f"updated {config.project_json_path} for github-releases mode",
        )

        repository_index = json.loads(
            self._repository_client.fetch_repo_text(config.repository_index_path),
        )
        if not isinstance(repository_index, list):
            raise AssertionError(
                f"Expected {config.repository_index_path} to decode to a list.",
            )
        filtered_entries = [
            entry
            for entry in repository_index
            if not isinstance(entry, dict) or str(entry.get("key", "")) != config.issue_key
        ]
        filtered_entries.append(
            {
                "key": config.issue_key,
                "path": config.issue_main_path,
                "parent": None,
                "epic": None,
                "parentPath": None,
                "epicPath": None,
                "summary": config.issue_summary,
                "issueType": "story",
                "status": "todo",
                "priority": "medium",
                "assignee": "demo-user",
                "labels": ["ts-503", "release-conflict"],
                "updated": "2026-05-12T00:00:00Z",
                "progress": 0.0,
                "children": [],
                "archived": False,
            },
        )
        self._repository_client.write_repo_text(
            config.repository_index_path,
            content=json.dumps(filtered_entries, indent=2) + "\n",
            message=seed_message,
        )
        setup_actions.append(f"seeded {config.repository_index_path}")

        self._repository_client.write_repo_text(
            config.issue_main_path,
            content=(
                f"---\n"
                f"key: {config.issue_key}\n"
                f"project: {config.project_key}\n"
                "issueType: story\n"
                "status: todo\n"
                f'summary: "{config.issue_summary}"\n'
                "priority: medium\n"
                "assignee: demo-user\n"
                "reporter: demo-admin\n"
                "updated: 2026-05-12T00:00:00Z\n"
                "---\n\n"
                "# Description\n\n"
                "TS-503 release identity conflict fixture.\n"
            ),
            message=seed_message,
        )
        setup_actions.append(f"seeded {config.issue_main_path}")

        try:
            self._repository_client.delete_repo_file(
                config.manifest_path,
                message=seed_message,
            )
            setup_actions.append(f"removed stale {config.manifest_path}")
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise

    def _restore_fixture(
        self,
        *,
        snapshots: tuple[_RemoteFileSnapshot, ...],
        cleanup_actions: list[str],
    ) -> None:
        for snapshot in reversed(snapshots):
            if snapshot.original_file is None:
                try:
                    self._repository_client.delete_repo_file(
                        snapshot.path,
                        message="Clean up TS-503 release identity conflict fixture",
                    )
                    cleanup_actions.append(f"deleted {snapshot.path}")
                except urllib.error.HTTPError as error:
                    if error.code != 404:
                        raise
            else:
                self._repository_client.write_repo_text(
                    snapshot.path,
                    content=snapshot.original_file.content,
                    message="Restore TS-503 release identity conflict fixture",
                )
                cleanup_actions.append(f"restored {snapshot.path}")

    def _restore_release(
        self,
        *,
        config: TrackStateCliReleaseIdentityConflictConfig,
        cleanup: _ReleaseCleanupPlan,
        cleanup_actions: list[str],
    ) -> None:
        if cleanup.restore_release_id is not None and cleanup.restore_name is not None:
            restored = self._repository_client.update_release_name(
                cleanup.restore_release_id,
                name=cleanup.restore_name,
            )
            cleanup_actions.append(
                f"restored release {restored.tag_name} title to {restored.name!r}",
            )
        if cleanup.created_release_id is not None:
            release = self._repository_client.fetch_release_by_tag(config.expected_release_tag)
            if release is not None:
                for asset in release.assets:
                    self._repository_client.delete_release_asset(asset.id)
                    cleanup_actions.append(
                        f"deleted release asset {asset.name} ({asset.id})",
                    )
            self._repository_client.delete_release(cleanup.created_release_id)
            cleanup_actions.append(f"deleted release {cleanup.created_release_id}")

    def _capture_remote_state(
        self,
        *,
        config: TrackStateCliReleaseIdentityConflictConfig,
    ) -> TrackStateCliReleaseIdentityConflictRemoteState:
        issue_main = self._fetch_repo_file_if_exists(config.issue_main_path)
        manifest = self._fetch_repo_file_if_exists(config.manifest_path)
        release = self._repository_client.fetch_release_by_tag(config.expected_release_tag)
        return TrackStateCliReleaseIdentityConflictRemoteState(
            project_json_text=self._repository_client.fetch_repo_text(config.project_json_path),
            issue_main_exists=issue_main is not None,
            issue_main_content=issue_main.content if issue_main is not None else None,
            manifest_exists=manifest is not None,
            manifest_text=manifest.content if manifest is not None else None,
            manifest_sha=manifest.sha if manifest is not None else None,
            release_present=release is not None,
            release_id=release.id if release is not None else None,
            release_name=release.name if release is not None else None,
            release_asset_names=(
                tuple(asset.name for asset in release.assets)
                if release is not None
                else ()
            ),
        )

    def _observe_command(
        self,
        *,
        config: TrackStateCliReleaseIdentityConflictConfig,
        repository_path: Path,
        executable_path: Path,
        access_token: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *config.requested_command[1:])
        return TrackStateCliCommandObservation(
            requested_command=config.requested_command,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this checkout "
                "and injected TRACKSTATE_TOKEN so TS-503 could exercise the live hosted "
                "GitHub release-backed upload flow from a clean working directory."
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

    def _fetch_repo_file_if_exists(self, path: str) -> HostedRepositoryFile | None:
        try:
            return self._repository_client.fetch_repo_file(path)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise
