from __future__ import annotations

import os
import subprocess
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveHostedRelease,
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_release_identity_local_conflict_config import (
    TrackStateCliReleaseIdentityLocalConflictConfig,
)
from testing.core.interfaces.trackstate_cli_release_identity_local_conflict_probe import (
    TrackStateCliReleaseIdentityLocalConflictProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_identity_local_conflict_result import (
    TrackStateCliReleaseIdentityLocalConflictRemoteState,
    TrackStateCliReleaseIdentityLocalConflictRepositoryState,
    TrackStateCliReleaseIdentityLocalConflictStoredFile,
    TrackStateCliReleaseIdentityLocalConflictValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


@dataclass(frozen=True)
class _ReleaseCleanupPlan:
    created_release_id: int | None
    restore_release_id: int | None
    restore_name: str | None


class PythonTrackStateCliReleaseIdentityLocalConflictFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseIdentityLocalConflictProbe,
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
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
    ) -> TrackStateCliReleaseIdentityLocalConflictValidationResult:
        if not self._repository_client.token:
            raise AssertionError(
                "TS-551 requires GH_TOKEN or GITHUB_TOKEN so the live GitHub release "
                "identity conflict can be exercised against the local CLI flow.",
            )

        setup_actions: list[str] = []
        cleanup_actions: list[str] = []
        cleanup_error: str | None = None
        original_release = self._repository_client.fetch_release_by_tag_any_state(
            config.expected_release_tag,
        )
        release_cleanup = self._ensure_conflicting_release(
            config=config,
            original_release=original_release,
            setup_actions=setup_actions,
        )

        initial_repository_state: (
            TrackStateCliReleaseIdentityLocalConflictRepositoryState | None
        ) = None
        final_repository_state: (
            TrackStateCliReleaseIdentityLocalConflictRepositoryState | None
        ) = None
        initial_remote_state: TrackStateCliReleaseIdentityLocalConflictRemoteState | None = None
        final_remote_state: TrackStateCliReleaseIdentityLocalConflictRemoteState | None = None
        observation: TrackStateCliCommandObservation | None = None
        local_attachment_path = ""

        try:
            initial_remote_state = self._capture_remote_state(config=config)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-551-bin-") as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                with tempfile.TemporaryDirectory(prefix="trackstate-ts-551-repo-") as temp_dir:
                    repository_path = Path(temp_dir)
                    local_attachment_path = self._seed_local_repository(
                        repository_path=repository_path,
                        config=config,
                    )
                    setup_actions.append(
                        f"seeded disposable local repository at {repository_path}",
                    )
                    initial_repository_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    observation = self._observe_command(
                        config=config,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        access_token=self._repository_client.token,
                    )
                    final_repository_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
            final_remote_state = self._capture_remote_state(config=config)
        finally:
            try:
                self._restore_release(
                    config=config,
                    cleanup=release_cleanup,
                    cleanup_actions=cleanup_actions,
                )
            except Exception:
                cleanup_error = traceback.format_exc()

        if (
            initial_repository_state is None
            or final_repository_state is None
            or initial_remote_state is None
            or final_remote_state is None
            or observation is None
        ):
            raise AssertionError(
                "TS-551 did not complete the local release identity conflict observation.\n"
                f"Cleanup error: {cleanup_error or '<none>'}",
            )

        return TrackStateCliReleaseIdentityLocalConflictValidationResult(
            initial_repository_state=initial_repository_state,
            final_repository_state=final_repository_state,
            initial_remote_state=initial_remote_state,
            final_remote_state=final_remote_state,
            observation=observation,
            setup_actions=tuple(setup_actions),
            cleanup_actions=tuple(cleanup_actions),
            cleanup_error=cleanup_error,
            local_attachment_path=local_attachment_path,
        )

    def _ensure_conflicting_release(
        self,
        *,
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
        original_release: LiveHostedRelease | None,
        setup_actions: list[str],
    ) -> _ReleaseCleanupPlan:
        if original_release is None:
            created = self._repository_client.create_release(
                tag_name=config.expected_release_tag,
                name=config.conflicting_release_title,
                body="TS-551 mismatched local release fixture",
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

    def _seed_local_repository(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
    ) -> str:
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
                f'      "tagPrefix": "{config.release_tag_prefix}"\n'
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
updated: 2026-05-13T00:00:00Z
---

# Description

TS-551 local github-releases release identity conflict fixture.
""",
        )
        local_attachment_path = repository_path / config.source_file_name
        self._write_binary_file(local_attachment_path, config.source_file_bytes)
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-551 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts551@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", config.remote_origin_url)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-551 fixture")
        return str(local_attachment_path)

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
    ) -> TrackStateCliReleaseIdentityLocalConflictRepositoryState:
        issue_main = repository_path / config.project_key / config.issue_key / "main.md"
        source_file = repository_path / config.source_file_name
        attachment_directory = (
            repository_path / config.project_key / config.issue_key / "attachments"
        )
        manifest_path = repository_path / config.project_key / config.issue_key / "attachments.json"
        expected_attachment = repository_path / config.expected_attachment_relative_path
        stored_files = (
            tuple(
                sorted(
                    (
                        TrackStateCliReleaseIdentityLocalConflictStoredFile(
                            relative_path=str(path.relative_to(repository_path)),
                            size_bytes=path.stat().st_size,
                        )
                        for path in attachment_directory.rglob("*")
                        if path.is_file()
                    ),
                    key=lambda observation: observation.relative_path,
                ),
            )
            if attachment_directory.is_dir()
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
        return TrackStateCliReleaseIdentityLocalConflictRepositoryState(
            issue_main_exists=issue_main.is_file(),
            source_file_exists=source_file.is_file(),
            attachment_directory_exists=attachment_directory.is_dir(),
            expected_attachment_exists=expected_attachment.is_file(),
            stored_files=stored_files,
            manifest_exists=manifest_path.is_file(),
            manifest_text=self._read_text_if_exists(manifest_path),
            git_status_lines=self._git_status_lines(repository_path),
            remote_names=remote_names,
            remote_origin_url=remote_origin_url or None,
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _capture_remote_state(
        self,
        *,
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
    ) -> TrackStateCliReleaseIdentityLocalConflictRemoteState:
        release = self._repository_client.fetch_release_by_tag_any_state(
            config.expected_release_tag,
        )
        return TrackStateCliReleaseIdentityLocalConflictRemoteState(
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
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
        repository_path: Path,
        executable_path: Path,
        access_token: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *config.requested_command[1:])
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        env["TRACKSTATE_TOKEN"] = access_token
        sandbox_home = repository_path / ".ts551-home"
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
        return TrackStateCliCommandObservation(
            requested_command=config.requested_command,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this checkout "
                "and injected TRACKSTATE_TOKEN so TS-551 runs the exact local CLI upload "
                "against a live GitHub release identity conflict."
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

    def _restore_release(
        self,
        *,
        config: TrackStateCliReleaseIdentityLocalConflictConfig,
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
            release = self._repository_client.fetch_release_by_tag_any_state(
                config.expected_release_tag,
            )
            if release is not None:
                for asset in release.assets:
                    self._repository_client.delete_release_asset(asset.id)
                    cleanup_actions.append(
                        f"deleted release asset {asset.name} ({asset.id})",
                    )
            self._repository_client.delete_release(cleanup.created_release_id)
            cleanup_actions.append(f"deleted release {cleanup.created_release_id}")

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0
