from __future__ import annotations

import json
import os
import subprocess
import tempfile
import traceback
import urllib.error
import zipfile
from dataclasses import dataclass
from pathlib import Path

from testing.core.config.trackstate_cli_hosted_lfs_restriction_config import (
    TrackStateCliHostedLfsRestrictionConfig,
)
from testing.core.interfaces.hosted_repository_client import HostedRepositoryClient
from testing.core.interfaces.trackstate_cli_hosted_lfs_restriction_probe import (
    TrackStateCliHostedLfsRestrictionProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.hosted_repository_file import HostedRepositoryFile
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_hosted_lfs_restriction_result import (
    TrackStateCliHostedLfsRestrictionRemoteState,
    TrackStateCliHostedLfsRestrictionValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


@dataclass(frozen=True)
class _RemoteFileSnapshot:
    path: str
    original_file: HostedRepositoryFile | None


class PythonTrackStateCliHostedLfsRestrictionFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliHostedLfsRestrictionProbe,
):
    def __init__(
        self,
        repository_root: Path,
        repository_client: HostedRepositoryClient,
    ) -> None:
        super().__init__(repository_root)
        self._repository_client = repository_client

    def observe(
        self,
        *,
        config: TrackStateCliHostedLfsRestrictionConfig,
    ) -> TrackStateCliHostedLfsRestrictionValidationResult:
        if not self._repository_client.token:
            raise AssertionError(
                "TS-383 requires GH_TOKEN or GITHUB_TOKEN so the hosted GitHub target "
                "can be exercised against the live repository."
            )

        snapshots = tuple(
            _RemoteFileSnapshot(
                path=path,
                original_file=self._fetch_repo_file_if_exists(self._repository_client, path),
            )
            for path in config.cleanup_repo_paths
        )
        setup_actions: list[str] = []
        cleanup_actions: list[str] = []
        cleanup_error: str | None = None

        self._seed_fixture(
            service=self._repository_client,
            config=config,
            setup_actions=setup_actions,
        )

        initial_state: TrackStateCliHostedLfsRestrictionRemoteState | None = None
        final_state: TrackStateCliHostedLfsRestrictionRemoteState | None = None
        observation: TrackStateCliCommandObservation | None = None
        local_attachment_path = ""
        try:
            initial_state = self._capture_remote_state(
                service=self._repository_client,
                config=config,
            )
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-383-bin-") as bin_dir:
                executable_path = Path(bin_dir) / "trackstate"
                self._compile_executable(executable_path)
                with tempfile.TemporaryDirectory(
                    prefix="trackstate-ts-383-workdir-"
                ) as work_dir:
                    working_directory = Path(work_dir)
                    local_attachment_path = str(
                        self._create_zip_attachment(
                            working_directory,
                            file_name=config.local_attachment_name,
                        )
                    )
                    observation = self._observe_command(
                        config=config,
                        repository_path=working_directory,
                        executable_path=executable_path,
                        access_token=self._repository_client.token,
                    )
            final_state = self._capture_remote_state(
                service=self._repository_client,
                config=config,
            )
        finally:
            try:
                self._restore_fixture(
                    service=self._repository_client,
                    snapshots=snapshots,
                    cleanup_actions=cleanup_actions,
                )
            except Exception:
                cleanup_error = traceback.format_exc()

        if initial_state is None or final_state is None or observation is None:
            raise AssertionError(
                "TS-383 did not complete the hosted LFS upload observation.\n"
                f"Cleanup error: {cleanup_error or '<none>'}"
            )

        return TrackStateCliHostedLfsRestrictionValidationResult(
            initial_state=initial_state,
            final_state=final_state,
            observation=observation,
            setup_actions=tuple(setup_actions),
            cleanup_actions=tuple(cleanup_actions),
            cleanup_error=cleanup_error,
            local_attachment_path=local_attachment_path,
        )

    def _seed_fixture(
        self,
        *,
        service: HostedRepositoryClient,
        config: TrackStateCliHostedLfsRestrictionConfig,
        setup_actions: list[str],
    ) -> None:
        seed_message = "Seed TS-383 hosted LFS upload fixture"
        repository_index_file = service.fetch_repo_file(config.repository_index_path)
        repository_index = json.loads(repository_index_file.content)
        if not isinstance(repository_index, list):
            raise AssertionError(
                f"Expected {config.repository_index_path} to decode to a list."
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
                "labels": ["ts-383", "lfs"],
                "updated": "2026-05-12T00:00:00Z",
                "progress": 0.0,
                "children": [],
                "archived": False,
            }
        )
        service.write_repo_text(
            config.repository_index_path,
            content=json.dumps(filtered_entries, indent=2) + "\n",
            message=seed_message,
        )
        setup_actions.append(f"seeded {config.repository_index_path}")
        service.write_repo_text(
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
                "TS-383 hosted Git LFS upload fixture.\n"
            ),
            message=seed_message,
        )
        setup_actions.append(f"seeded {config.issue_main_path}")

    def _restore_fixture(
        self,
        *,
        service: HostedRepositoryClient,
        snapshots: tuple[_RemoteFileSnapshot, ...],
        cleanup_actions: list[str],
    ) -> None:
        for snapshot in reversed(snapshots):
            if snapshot.original_file is None:
                try:
                    service.delete_repo_file(
                        snapshot.path,
                        message="Clean up TS-383 hosted LFS upload fixture",
                    )
                    cleanup_actions.append(f"deleted {snapshot.path}")
                except urllib.error.HTTPError as error:
                    if error.code != 404:
                        raise
            else:
                service.write_repo_text(
                    snapshot.path,
                    content=snapshot.original_file.content,
                    message="Restore TS-383 hosted LFS upload fixture",
                )
                cleanup_actions.append(f"restored {snapshot.path}")

    def _capture_remote_state(
        self,
        *,
        service: HostedRepositoryClient,
        config: TrackStateCliHostedLfsRestrictionConfig,
    ) -> TrackStateCliHostedLfsRestrictionRemoteState:
        gitattributes_text = service.fetch_repo_text(".gitattributes")
        zip_lfs_rule_line = next(
            (
                line.strip()
                for line in gitattributes_text.splitlines()
                if config.required_gitattributes_fragment in line
            ),
            None,
        )
        present_fixture_paths = tuple(
            path
            for path in config.fixture_repo_paths
            if self._fetch_repo_file_if_exists(service, path) is not None
        )
        issue_main = self._fetch_repo_file_if_exists(service, config.issue_main_path)
        attachment = self._fetch_repo_file_if_exists(service, config.attachment_repo_path)
        return TrackStateCliHostedLfsRestrictionRemoteState(
            zip_lfs_rule_present=zip_lfs_rule_line is not None,
            zip_lfs_rule_line=zip_lfs_rule_line,
            present_fixture_paths=present_fixture_paths,
            issue_main_exists=issue_main is not None,
            issue_main_content=issue_main.content if issue_main is not None else None,
            attachment_exists=attachment is not None,
            attachment_sha=attachment.sha if attachment is not None else None,
        )

    def _observe_command(
        self,
        *,
        config: TrackStateCliHostedLfsRestrictionConfig,
        repository_path: Path,
        executable_path: Path,
        access_token: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *config.requested_command[1:])
        fallback_reason = (
            "Pinned execution to a temporary executable compiled from this checkout "
            "and injected TRACKSTATE_TOKEN so TS-383 could exercise the live hosted "
            "GitHub upload flow from a clean working directory containing assets.zip."
        )
        return TrackStateCliCommandObservation(
            requested_command=config.requested_command,
            executed_command=executed_command,
            fallback_reason=fallback_reason,
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

    def _create_zip_attachment(self, directory: Path, *, file_name: str) -> Path:
        attachment_path = directory / file_name
        with zipfile.ZipFile(attachment_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(
                "fixture.txt",
                "TS-383 hosted LFS upload fixture.\n",
            )
        return attachment_path

    @staticmethod
    def _fetch_repo_file_if_exists(
        service: HostedRepositoryClient,
        path: str,
    ) -> HostedRepositoryFile | None:
        try:
            return service.fetch_repo_file(path)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise
