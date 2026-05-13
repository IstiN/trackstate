from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_release_foreign_asset_conflict_config import (
    TrackStateCliReleaseForeignAssetConflictConfig,
)
from testing.core.interfaces.trackstate_cli_release_foreign_asset_conflict_probe import (
    TrackStateCliReleaseForeignAssetConflictProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_foreign_asset_conflict_result import (
    TrackStateCliReleaseForeignAssetConflictCleanupResult,
    TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation,
    TrackStateCliReleaseForeignAssetConflictReleaseState,
    TrackStateCliReleaseForeignAssetConflictRepositoryState,
    TrackStateCliReleaseForeignAssetConflictValidationResult,
)
from testing.core.utils.polling import poll_until
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseForeignAssetConflictFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseForeignAssetConflictProbe,
):
    def __init__(
        self,
        repository_root: Path,
        repository_client: LiveSetupRepositoryService,
    ) -> None:
        super().__init__(repository_root)
        self._repository_client = repository_client

    def observe_release_foreign_asset_conflict(
        self,
        *,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
    ) -> TrackStateCliReleaseForeignAssetConflictValidationResult:
        if not self._repository_client.token:
            raise AssertionError(
                "TS-552 requires GH_TOKEN or GITHUB_TOKEN to seed and inspect the live "
                "GitHub Release fixture.",
            )

        remote_origin_url = f"https://github.com/{config.repository}.git"
        release_tag_prefix = f"{config.release_tag_prefix_base}{uuid.uuid4().hex[:8]}-"
        release_tag = f"{release_tag_prefix}{config.issue_key}"
        cleanup = TrackStateCliReleaseForeignAssetConflictCleanupResult(
            status="not-started",
            release_tag=release_tag,
            deleted_assets=(),
        )

        self._seed_release_fixture(config=config, release_tag=release_tag)
        try:
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-552-bin-") as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                with tempfile.TemporaryDirectory(prefix="trackstate-ts-552-repo-") as temp_dir:
                    repository_path = Path(temp_dir)
                    self._seed_local_repository(
                        repository_path=repository_path,
                        config=config,
                        release_tag_prefix=release_tag_prefix,
                        remote_origin_url=remote_origin_url,
                    )
                    initial_state = self._capture_local_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    fixture_release_state = self._observe_release_state(
                        config=config,
                        release_tag=release_tag,
                    )
                    preflight_gh_release_view = self._observe_gh_release_view(
                        config=config,
                        release_tag=release_tag,
                    )
                    observation = self._observe_command(
                        requested_command=config.requested_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        access_token=self._repository_client.token,
                    )
                    final_state = self._capture_local_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    remote_state_after_command = self._observe_release_state(
                        config=config,
                        release_tag=release_tag,
                    )
                    gh_release_view = self._observe_gh_release_view(
                        config=config,
                        release_tag=release_tag,
                    )
        finally:
            try:
                cleanup = self._cleanup_release(
                    config=config,
                    release_tag=release_tag,
                )
            except Exception as error:
                cleanup = TrackStateCliReleaseForeignAssetConflictCleanupResult(
                    status="failed",
                    release_tag=release_tag,
                    deleted_assets=(),
                    error=f"{type(error).__name__}: {error}",
                )

        return TrackStateCliReleaseForeignAssetConflictValidationResult(
            initial_state=initial_state,
            fixture_release_state=fixture_release_state,
            preflight_gh_release_view=preflight_gh_release_view,
            observation=observation,
            final_state=final_state,
            remote_state_after_command=remote_state_after_command,
            gh_release_view=gh_release_view,
            cleanup=cleanup,
            release_tag_prefix=release_tag_prefix,
            release_tag=release_tag,
            remote_origin_url=remote_origin_url,
        )

    def _seed_release_fixture(
        self,
        *,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
        release_tag: str,
    ) -> None:
        existing_release = self._repository_client.fetch_release_by_tag(release_tag)
        if existing_release is not None:
            raise AssertionError(
                f"Precondition failed: release tag {release_tag} already exists.",
            )

        self._repository_client.create_release(
            tag_name=release_tag,
            name=config.expected_release_title,
            body=f"TS-552 foreign asset conflict fixture for {config.issue_key}.",
            draft=False,
            prerelease=False,
            target_commitish=config.branch,
        )

        matched_release, release = poll_until(
            probe=lambda: self._repository_client.fetch_release_by_tag(release_tag),
            is_satisfied=lambda value: value is not None
            and value.name == config.expected_release_title,
            timeout_seconds=config.release_poll_timeout_seconds,
            interval_seconds=config.release_poll_interval_seconds,
        )
        if not matched_release or release is None:
            raise AssertionError(
                "Precondition failed: the GitHub release fixture was not created with the "
                "expected tag/title.\n"
                f"Observed release: {release}",
            )

        self._repository_client.upload_release_asset(
            release_id=release.id,
            asset_name=config.foreign_asset_name,
            content_type="application/zip",
            content=_foreign_asset_bytes(),
        )

        matched_asset, observed_release = poll_until(
            probe=lambda: self._repository_client.fetch_release_by_tag(release_tag),
            is_satisfied=lambda value: value is not None
            and value.name == config.expected_release_title
            and config.foreign_asset_name in [asset.name for asset in value.assets],
            timeout_seconds=config.release_poll_timeout_seconds,
            interval_seconds=config.release_poll_interval_seconds,
        )
        if not matched_asset or observed_release is None:
            raise AssertionError(
                "Precondition failed: the GitHub release fixture never exposed the seeded "
                f"{config.foreign_asset_name} asset.\n"
                f"Observed release: {observed_release}",
            )

    def _seed_local_repository(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
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
                        "githubReleases": {
                            "tagPrefix": release_tag_prefix,
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
            repository_path / config.project_key / config.issue_key / "main.md",
            (
                "---\n"
                f"key: {config.issue_key}\n"
                f"project: {config.project_key}\n"
                "issueType: story\n"
                "status: todo\n"
                f'summary: "{config.issue_summary}"\n'
                "priority: medium\n"
                "assignee: tester\n"
                "reporter: tester\n"
                "updated: 2026-05-13T00:00:00Z\n"
                "---\n\n"
                "# Description\n\n"
                "TS-552 local foreign asset conflict fixture.\n"
            ),
        )
        self._write_file(
            repository_path / config.manifest_path,
            config.seeded_manifest_text,
        )
        self._write_binary_file(
            repository_path / config.source_file_name,
            config.source_file_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-552 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts552@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", remote_origin_url)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-552 fixture")

    def _capture_local_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
    ) -> TrackStateCliReleaseForeignAssetConflictRepositoryState:
        issue_main_path = repository_path / config.project_key / config.issue_key / "main.md"
        manifest_path = repository_path / config.manifest_path
        attachments_directory = (
            repository_path / config.project_key / config.issue_key / "attachments"
        )
        source_file_path = repository_path / config.source_file_name
        stored_files = (
            tuple(
                sorted(
                    str(path.relative_to(repository_path))
                    for path in attachments_directory.rglob("*")
                    if path.is_file()
                ),
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
        return TrackStateCliReleaseForeignAssetConflictRepositoryState(
            issue_main_exists=issue_main_path.is_file(),
            manifest_exists=manifest_path.is_file(),
            manifest_text=self._read_text_if_exists(manifest_path),
            attachments_directory_exists=attachments_directory.is_dir(),
            stored_files=stored_files,
            source_file_exists=source_file_path.is_file(),
            git_status_lines=self._git_status_lines(repository_path),
            remote_names=remote_names,
            remote_origin_url=remote_origin_url or None,
        )

    def _observe_release_state(
        self,
        *,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
        release_tag: str,
    ) -> TrackStateCliReleaseForeignAssetConflictReleaseState:
        matched, release = poll_until(
            probe=lambda: self._repository_client.fetch_release_by_tag(release_tag),
            is_satisfied=lambda value: value is not None,
            timeout_seconds=config.release_poll_timeout_seconds,
            interval_seconds=config.release_poll_interval_seconds,
        )
        if not matched or release is None:
            raise AssertionError(
                f"Step 4 failed: the release {release_tag} was not observable.",
            )
        return TrackStateCliReleaseForeignAssetConflictReleaseState(
            release_tag=release.tag_name,
            release_title=release.name,
            release_asset_names=tuple(asset.name for asset in release.assets),
        )

    def _observe_gh_release_view(
        self,
        *,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
        release_tag: str,
    ) -> TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation:
        matched, observation = poll_until(
            probe=lambda: self._gh_release_view_once(
                release_tag=release_tag,
                repository=config.repository,
            ),
            is_satisfied=lambda value: value.exit_code == 0,
            timeout_seconds=config.gh_poll_timeout_seconds,
            interval_seconds=config.gh_poll_interval_seconds,
        )
        if not matched:
            raise AssertionError(
                "Step 4 failed: `gh release view` did not become available for the seeded "
                "release fixture.\n"
                f"Observed output: {observation}",
            )
        return observation

    def _gh_release_view_once(
        self,
        *,
        release_tag: str,
        repository: str,
    ) -> TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env["GH_TOKEN"] = self._repository_client.token or ""
        env["GITHUB_TOKEN"] = self._repository_client.token or ""
        completed = subprocess.run(
            (
                "gh",
                "release",
                "view",
                release_tag,
                "--repo",
                repository,
                "--json",
                "assets,name,tagName",
            ),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        payload = _parse_json(completed.stdout)
        assets = payload.get("assets") if isinstance(payload, dict) else None
        asset_names = (
            tuple(
                str(asset.get("name", ""))
                for asset in assets
                if isinstance(asset, dict) and str(asset.get("name", "")).strip()
            )
            if isinstance(assets, list)
            else ()
        )
        return TrackStateCliReleaseForeignAssetConflictGhReleaseViewObservation(
            exit_code=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            payload=payload,
            asset_names=asset_names,
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
                "and injected GitHub credentials so TS-552 can run the exact local "
                "github-releases upload command from a disposable repository."
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
        sandbox_home = cwd / ".ts552-home"
        sandbox_home.mkdir(parents=True, exist_ok=True)
        env["HOME"] = str(sandbox_home)
        env["XDG_CONFIG_HOME"] = str(sandbox_home / ".config")
        env["GH_CONFIG_DIR"] = str(sandbox_home / ".config" / "gh")
        env["GIT_TERMINAL_PROMPT"] = "0"
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
            json_payload=_parse_json(completed.stdout),
        )

    def _cleanup_release(
        self,
        *,
        config: TrackStateCliReleaseForeignAssetConflictConfig,
        release_tag: str,
    ) -> TrackStateCliReleaseForeignAssetConflictCleanupResult:
        release = self._repository_client.fetch_release_by_tag(release_tag)
        if release is None:
            return TrackStateCliReleaseForeignAssetConflictCleanupResult(
                status="already-absent",
                release_tag=release_tag,
                deleted_assets=(),
            )
        deleted_assets: list[str] = []
        for asset in release.assets:
            self._repository_client.delete_release_asset(asset.id)
            deleted_assets.append(asset.name)
        self._repository_client.delete_release(release.id)
        matched, _ = poll_until(
            probe=lambda: self._repository_client.fetch_release_by_tag(release_tag),
            is_satisfied=lambda value: value is None,
            timeout_seconds=config.release_poll_timeout_seconds,
            interval_seconds=config.release_poll_interval_seconds,
        )
        if not matched:
            raise AssertionError(
                f"Cleanup failed: the seeded release {release_tag} still exists.",
            )
        return TrackStateCliReleaseForeignAssetConflictCleanupResult(
            status="deleted-seeded-release",
            release_tag=release_tag,
            deleted_assets=tuple(deleted_assets),
        )

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _read_text_if_exists(self, path: Path) -> str | None:
        return path.read_text(encoding="utf-8") if path.is_file() else None


def _foreign_asset_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "README.txt",
            "TS-552 foreign release asset that must remain outside attachments.json.\n",
        )
    return buffer.getvalue()


def _parse_json(text: str) -> object | None:
    payload = text.strip()
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None
