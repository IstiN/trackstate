from __future__ import annotations

import os
import subprocess
import tempfile
import traceback
from pathlib import Path

from testing.components.services.live_setup_repository_git_ref_service import (
    LiveSetupRepositoryGitRefService,
)
from testing.components.services.live_setup_repository_service import (
    LiveHostedRelease,
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_release_unpushed_branch_config import (
    TrackStateCliReleaseUnpushedBranchConfig,
)
from testing.core.interfaces.trackstate_cli_release_unpushed_branch_probe import (
    TrackStateCliReleaseUnpushedBranchProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_unpushed_branch_result import (
    TrackStateCliReleaseUnpushedBranchRemoteState,
    TrackStateCliReleaseUnpushedBranchRepositoryState,
    TrackStateCliReleaseUnpushedBranchStoredFile,
    TrackStateCliReleaseUnpushedBranchValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseUnpushedBranchFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseUnpushedBranchProbe,
):
    def __init__(
        self,
        repository_root: Path,
        repository_client: LiveSetupRepositoryService,
        git_ref_service: LiveSetupRepositoryGitRefService,
    ) -> None:
        super().__init__(repository_root)
        self._repository_client = repository_client
        self._git_ref_service = git_ref_service

    def observe(
        self,
        *,
        config: TrackStateCliReleaseUnpushedBranchConfig,
    ) -> TrackStateCliReleaseUnpushedBranchValidationResult:
        access_token = self._repository_client.token
        if not access_token:
            raise AssertionError(
                "A GitHub token is required so TS-593 can exercise the live release "
                "creation failure for an unpushed local branch.",
            )

        setup_actions: list[str] = []
        pre_run_cleanup_actions: list[str] = []
        cleanup_actions: list[str] = []
        cleanup_error: str | None = None

        self._cleanup_release_artifacts(
            config=config,
            actions=pre_run_cleanup_actions,
        )
        initial_remote_state = self._capture_remote_state(config=config)
        if initial_remote_state.branch_exists_on_remote:
            raise AssertionError(
                "Precondition failed: the remote repository already contains the branch "
                f"{config.unpushed_branch!r}, so TS-593 cannot reproduce the unpushed-"
                "branch failure.\n"
                f"Observed remote state: {initial_remote_state}"
            )

        initial_repository_state: TrackStateCliReleaseUnpushedBranchRepositoryState | None = None
        final_repository_state: TrackStateCliReleaseUnpushedBranchRepositoryState | None = None
        final_remote_state: TrackStateCliReleaseUnpushedBranchRemoteState | None = None
        observation: TrackStateCliCommandObservation | None = None

        try:
            with tempfile.TemporaryDirectory(
                prefix="trackstate-release-unpushed-bin-",
            ) as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                with tempfile.TemporaryDirectory(
                    prefix="trackstate-release-unpushed-repo-",
                ) as temp_dir:
                    repository_path = Path(temp_dir)
                    self._seed_local_repository(
                        repository_path=repository_path,
                        config=config,
                    )
                    setup_actions.append(
                        f"seeded disposable repository at {repository_path}",
                    )
                    initial_repository_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    observation = self._observe_command(
                        config=config,
                        repository_path=repository_path,
                        executable_path=executable_path,
                        access_token=access_token,
                    )
                    final_repository_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
            final_remote_state = self._capture_remote_state(config=config)
        finally:
            try:
                self._cleanup_release_artifacts(config=config, actions=cleanup_actions)
            except Exception:
                cleanup_error = traceback.format_exc()

        if (
            initial_repository_state is None
            or final_repository_state is None
            or final_remote_state is None
            or observation is None
        ):
            raise AssertionError(
                "The TS-593 unpushed-branch observation did not complete.\n"
                f"Cleanup error: {cleanup_error or '<none>'}",
            )

        return TrackStateCliReleaseUnpushedBranchValidationResult(
            initial_repository_state=initial_repository_state,
            final_repository_state=final_repository_state,
            initial_remote_state=initial_remote_state,
            final_remote_state=final_remote_state,
            observation=observation,
            setup_actions=tuple(setup_actions),
            pre_run_cleanup_actions=tuple(pre_run_cleanup_actions),
            cleanup_actions=tuple(cleanup_actions),
            cleanup_error=cleanup_error,
        )

    def _cleanup_release_artifacts(
        self,
        *,
        config: TrackStateCliReleaseUnpushedBranchConfig,
        actions: list[str],
    ) -> None:
        releases = self._repository_client.fetch_releases_by_tag_any_state(
            config.expected_release_tag,
        )
        for release in releases:
            for asset in release.assets:
                self._repository_client.delete_release_asset(asset.id)
                actions.append(f"deleted release asset {asset.name} ({asset.id})")
            self._repository_client.delete_release(release.id)
            actions.append(f"deleted release {release.id} for {config.expected_release_tag}")

        for ref in self._repository_client.list_matching_tag_refs(config.expected_release_tag):
            self._repository_client.delete_tag_ref(config.expected_release_tag)
            actions.append(f"deleted tag ref {ref}")

    def _seed_local_repository(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseUnpushedBranchConfig,
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

TS-593 unpushed local branch fixture.
""",
        )
        self._write_binary_file(
            repository_path / config.source_file_name,
            config.source_file_bytes,
        )
        self._git(repository_path, "init", "-b", config.base_branch)
        self._git(
            repository_path,
            "config",
            "--local",
            "user.name",
            "TS-593 Tester",
        )
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts-593@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", config.remote_origin_url)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed unpushed branch fixture")
        self._git(repository_path, "checkout", "-b", config.unpushed_branch)

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseUnpushedBranchConfig,
    ) -> TrackStateCliReleaseUnpushedBranchRepositoryState:
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
                        TrackStateCliReleaseUnpushedBranchStoredFile(
                            relative_path=str(path.relative_to(repository_path)),
                            size_bytes=path.stat().st_size,
                        )
                        for path in attachment_directory.rglob("*")
                        if path.is_file()
                    ),
                    key=lambda observation: observation.relative_path,
                )
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
        current_branch = self._git_output(
            repository_path,
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ).strip()
        return TrackStateCliReleaseUnpushedBranchRepositoryState(
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
            current_branch=current_branch or None,
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _capture_remote_state(
        self,
        *,
        config: TrackStateCliReleaseUnpushedBranchConfig,
    ) -> TrackStateCliReleaseUnpushedBranchRemoteState:
        releases = self._repository_client.fetch_releases_by_tag_any_state(
            config.expected_release_tag,
        )
        asset_names = sorted(
            {
                asset.name
                for release in releases
                for asset in release.assets
                if asset.name
            }
        )
        return TrackStateCliReleaseUnpushedBranchRemoteState(
            branch_exists_on_remote=self._remote_branch_exists(config.unpushed_branch),
            release_count=len(releases),
            release_ids=tuple(release.id for release in releases),
            release_names=tuple(release.name for release in releases if release.name),
            release_asset_names=tuple(asset_names),
            matching_tag_refs=self._repository_client.list_matching_tag_refs(
                config.expected_release_tag,
            ),
        )

    def _remote_branch_exists(self, branch_name: str) -> bool:
        try:
            self._git_ref_service.fetch_branch_head_sha(branch_name)
        except RuntimeError:
            return False
        return True

    def _observe_command(
        self,
        *,
        config: TrackStateCliReleaseUnpushedBranchConfig,
        repository_path: Path,
        executable_path: Path,
        access_token: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *config.requested_command[1:])
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        env["TRACKSTATE_TOKEN"] = access_token
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
        env["GIT_TERMINAL_PROMPT"] = "0"
        with tempfile.TemporaryDirectory(
            prefix="trackstate-release-unpushed-home-",
        ) as sandbox_home_dir:
            sandbox_home = Path(sandbox_home_dir)
            env["HOME"] = str(sandbox_home)
            env["XDG_CONFIG_HOME"] = str(sandbox_home / ".config")
            env["GH_CONFIG_DIR"] = str(sandbox_home / ".config" / "gh")
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
                "and injected TRACKSTATE_TOKEN so the exact local CLI upload runs from "
                "a disposable repository checked out on an unpushed local branch."
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

    def _git_status_lines(self, repository_path: Path) -> tuple[str, ...]:
        output = self._git_output(repository_path, "status", "--short")
        return tuple(line for line in output.splitlines() if line.strip())

    def _git_head_subject(self, repository_path: Path) -> str | None:
        output = self._git_output(repository_path, "log", "-1", "--pretty=%s").strip()
        return output or None

    def _git_head_count(self, repository_path: Path) -> int:
        output = self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
        return int(output) if output else 0
