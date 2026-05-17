from __future__ import annotations

import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import asdict, is_dataclass
from pathlib import Path

from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.trackstate_cli_release_body_normalization_config import (
    TrackStateCliReleaseBodyNormalizationConfig,
)
from testing.core.interfaces.trackstate_cli_release_body_normalization_probe import (
    TrackStateCliReleaseBodyNormalizationProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_body_normalization_result import (
    TrackStateCliReleaseBodyNormalizationRepositoryState,
    TrackStateCliReleaseBodyNormalizationSeededRelease,
    TrackStateCliReleaseBodyNormalizationValidationResult,
)
from testing.core.utils.polling import poll_until
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseBodyNormalizationFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseBodyNormalizationProbe,
):
    def __init__(
        self,
        repository_root: Path,
        service: LiveSetupRepositoryService,
    ) -> None:
        super().__init__(repository_root)
        self._service = service

    def observe_release_body_normalization(
        self,
        *,
        config: TrackStateCliReleaseBodyNormalizationConfig,
    ) -> TrackStateCliReleaseBodyNormalizationValidationResult:
        if not self._service.token:
            raise RuntimeError(
                "TS-590 requires GH_TOKEN or GITHUB_TOKEN to seed and verify live GitHub Releases."
            )

        release_tag_prefix = f"{config.release_tag_prefix_base}{uuid.uuid4().hex[:8]}-"
        release_tag = f"{release_tag_prefix}{config.issue_key}"
        remote_origin_url = f"https://github.com/{self._service.repository}.git"

        with tempfile.TemporaryDirectory(prefix="trackstate-ts-590-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            seeded_release = self._service.create_release(
                tag_name=release_tag,
                name=config.expected_release_title,
                body=config.seeded_release_body,
                target_commitish=self._service.ref,
                draft=True,
                prerelease=False,
            )
            try:
                with tempfile.TemporaryDirectory(prefix="trackstate-ts-590-repo-") as temp_dir:
                    repository_path = Path(temp_dir)
                    self._seed_local_repository(
                        repository_path=repository_path,
                        config=config,
                        remote_origin_url=remote_origin_url,
                        release_tag_prefix=release_tag_prefix,
                    )
                    initial_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    observation = self._observe_command(
                        requested_command=config.requested_command,
                        repository_path=repository_path,
                        executable_path=executable_path,
                    )
                    final_state = self._capture_repository_state(
                        repository_path=repository_path,
                        config=config,
                    )
                    manifest_observation = self._poll_manifest(
                        repository_path=repository_path,
                        config=config,
                        release_tag=release_tag,
                    )
                    release_observation = self._poll_release(
                        config=config,
                        seeded_release_id=seeded_release.id,
                        release_tag=release_tag,
                    )
                    gh_release_view = self._poll_gh_view(
                        config=config,
                        release_tag=release_tag,
                    )
            finally:
                cleanup = self._cleanup_release(release_tag)

        return TrackStateCliReleaseBodyNormalizationValidationResult(
            release_tag_prefix=release_tag_prefix,
            release_tag=release_tag,
            remote_origin_url=remote_origin_url,
            compiled_binary_path=str(executable_path),
            seeded_release=TrackStateCliReleaseBodyNormalizationSeededRelease(
                id=seeded_release.id,
                tag_name=seeded_release.tag_name,
                name=seeded_release.name,
                body=seeded_release.body,
                draft=seeded_release.draft,
                prerelease=seeded_release.prerelease,
            ),
            initial_state=initial_state,
            observation=observation,
            final_state=final_state,
            manifest_observation=manifest_observation,
            release_observation=release_observation,
            gh_release_view=gh_release_view,
            cleanup=cleanup,
        )

    def _seed_local_repository(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseBodyNormalizationConfig,
        remote_origin_url: str,
        release_tag_prefix: str,
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
            repository_path / config.issue_main_path,
            (
                "---\n"
                f"key: {config.issue_key}\n"
                f"project: {config.project_key}\n"
                "issueType: story\n"
                "status: todo\n"
                f"summary: {config.issue_summary}\n"
                "priority: medium\n"
                "assignee: tester\n"
                "reporter: tester\n"
                "updated: 2026-05-13T00:00:00Z\n"
                "---\n\n"
                "# Description\n\n"
                "TS-590 release body normalization fixture.\n"
            ),
        )
        self._write_file(repository_path / config.manifest_path, "[]\n")
        self._write_binary_file(
            repository_path / config.source_file_name,
            config.source_file_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-590 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts590@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", remote_origin_url)
        git_environment = {
            "GIT_AUTHOR_NAME": "TS-590 Tester",
            "GIT_AUTHOR_EMAIL": "ts590@example.com",
            "GIT_AUTHOR_DATE": "2026-05-13T00:00:00Z",
            "GIT_COMMITTER_NAME": "TS-590 Tester",
            "GIT_COMMITTER_EMAIL": "ts590@example.com",
            "GIT_COMMITTER_DATE": "2026-05-13T00:00:00Z",
        }
        self._git(repository_path, "add", ".", env=git_environment)
        self._git(
            repository_path,
            "commit",
            "-m",
            "Seed TS-590 release body normalization fixture",
            env=git_environment,
        )

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseBodyNormalizationConfig,
    ) -> TrackStateCliReleaseBodyNormalizationRepositoryState:
        manifest_path = repository_path / config.manifest_path
        manifest_text = self._read_text_if_exists(manifest_path)
        remote_origin_url = self._git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip()
        return TrackStateCliReleaseBodyNormalizationRepositoryState(
            issue_main_exists=(repository_path / config.issue_main_path).is_file(),
            source_file_exists=(repository_path / config.source_file_name).is_file(),
            manifest_exists=manifest_path.is_file(),
            manifest_text=manifest_text,
            git_status_lines=tuple(
                line
                for line in self._git_output(repository_path, "status", "--short").splitlines()
                if line.strip()
            ),
            remote_origin_url=remote_origin_url or None,
        )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        for variable in ("GH_TOKEN", "GITHUB_TOKEN", "TRACKSTATE_TOKEN"):
            env.pop(variable, None)
        env["TRACKSTATE_TOKEN"] = self._service.token or ""
        env["GH_TOKEN"] = self._service.token or ""
        env["GITHUB_TOKEN"] = self._service.token or ""
        sandbox_home = repository_path / ".ts590-home"
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
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=(
                "Pinned execution to a temporary executable compiled from this checkout "
                "and injected GitHub credentials through the local test environment so "
                "TS-590 exercises the release-backed local upload path deterministically."
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

    def _poll_manifest(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseBodyNormalizationConfig,
        release_tag: str,
    ) -> dict[str, object]:
        _, observation = poll_until(
            probe=lambda: self._observe_manifest_state(
                repository_path=repository_path,
                config=config,
                release_tag=release_tag,
            ),
            is_satisfied=lambda value: value["matches_expected"] is True,
            timeout_seconds=config.manifest_poll_timeout_seconds,
            interval_seconds=config.manifest_poll_interval_seconds,
        )
        return observation

    def _observe_manifest_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseBodyNormalizationConfig,
        release_tag: str,
    ) -> dict[str, object]:
        manifest_path = repository_path / config.manifest_path
        manifest_text = self._read_text_if_exists(manifest_path) or ""
        matching_entries: list[dict[str, object]] = []
        try:
            payload = json.loads(manifest_text)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, list):
            matching_entries = [
                entry
                for entry in payload
                if isinstance(entry, dict) and entry.get("name") == config.source_file_name
            ]
        matching_entry = matching_entries[0] if len(matching_entries) == 1 else None
        return {
            "manifest_text": manifest_text,
            "matching_entries": matching_entries,
            "matching_entry": matching_entry,
            "entry_count": len(matching_entries),
            "matches_expected": matching_entry is not None
            and str(matching_entry.get("id", "")) == config.expected_attachment_relative_path
            and str(matching_entry.get("storagePath", ""))
            == config.expected_attachment_relative_path
            and str(matching_entry.get("storageBackend", "")) == "github-releases"
            and str(matching_entry.get("githubReleaseTag", "")) == release_tag
            and str(matching_entry.get("githubReleaseAssetName", "")) == config.source_file_name
            and str(matching_entry.get("revisionOrOid", "")).strip() != "",
        }

    def _poll_release(
        self,
        *,
        config: TrackStateCliReleaseBodyNormalizationConfig,
        seeded_release_id: int,
        release_tag: str,
    ) -> dict[str, object]:
        _, observation = poll_until(
            probe=lambda: self._observe_release_state(
                config=config,
                seeded_release_id=seeded_release_id,
                release_tag=release_tag,
            ),
            is_satisfied=lambda value: value["matches_expected"] is True,
            timeout_seconds=config.release_poll_timeout_seconds,
            interval_seconds=config.release_poll_interval_seconds,
        )
        return observation

    def _observe_release_state(
        self,
        *,
        config: TrackStateCliReleaseBodyNormalizationConfig,
        seeded_release_id: int,
        release_tag: str,
    ) -> dict[str, object]:
        release = self._service.fetch_release_by_tag_any_state(release_tag)
        asset_names = tuple(asset.name for asset in release.assets) if release else ()
        asset_ids = tuple(asset.id for asset in release.assets) if release else ()
        return {
            "release_present": release is not None,
            "release_id": release.id if release else None,
            "release_tag": release.tag_name if release else None,
            "release_name": release.name if release else None,
            "release_body": release.body if release else None,
            "release_draft": release.draft if release else None,
            "release_prerelease": release.prerelease if release else None,
            "asset_names": asset_names,
            "asset_ids": asset_ids,
            "matches_expected": release is not None
            and release.id == seeded_release_id
            and release.tag_name == release_tag
            and release.name == config.expected_release_title
            and release.body == config.expected_release_body
            and release.draft is True
            and release.prerelease is False
            and asset_names == (config.source_file_name,),
        }

    def _poll_gh_view(
        self,
        *,
        config: TrackStateCliReleaseBodyNormalizationConfig,
        release_tag: str,
    ) -> dict[str, object]:
        _, observation = poll_until(
            probe=lambda: self._observe_gh_release_view(
                config=config,
                release_tag=release_tag,
            ),
            is_satisfied=lambda value: value["matches_expected"] is True,
            timeout_seconds=config.gh_poll_timeout_seconds,
            interval_seconds=config.gh_poll_interval_seconds,
        )
        return observation

    def _observe_gh_release_view(
        self,
        *,
        config: TrackStateCliReleaseBodyNormalizationConfig,
        release_tag: str,
    ) -> dict[str, object]:
        env = os.environ.copy()
        env["GH_TOKEN"] = self._service.token or ""
        env["GITHUB_TOKEN"] = self._service.token or ""
        completed = subprocess.run(
            (
                "gh",
                "release",
                "view",
                release_tag,
                "--repo",
                self._service.repository,
                "--json",
                "tagName,name,isDraft,body,assets",
            ),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        json_payload: dict[str, object] | None = None
        try:
            raw_payload = json.loads(completed.stdout) if completed.stdout.strip() else None
        except json.JSONDecodeError:
            raw_payload = None
        if isinstance(raw_payload, dict):
            json_payload = raw_payload
        assets = json_payload.get("assets") if isinstance(json_payload, dict) else None
        asset_names = (
            tuple(
                str(asset.get("name", "")).strip()
                for asset in assets
                if isinstance(asset, dict) and str(asset.get("name", "")).strip()
            )
            if isinstance(assets, list)
            else ()
        )
        return {
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "json_payload": json_payload,
            "asset_names": asset_names,
            "matches_expected": completed.returncode == 0
            and isinstance(json_payload, dict)
            and str(json_payload.get("tagName", "")) == release_tag
            and str(json_payload.get("name", "")) == config.expected_release_title
            and json_payload.get("isDraft") is True
            and str(json_payload.get("body", "")) == config.expected_release_body
            and asset_names == (config.source_file_name,),
        }

    def _cleanup_release(self, release_tag: str) -> dict[str, object]:
        deleted_release_ids: list[int] = []
        deleted_asset_ids: list[int] = []
        releases = self._service.fetch_releases_by_tag_any_state(release_tag)
        for release in releases:
            for asset in release.assets:
                self._service.delete_release_asset(asset.id)
                deleted_asset_ids.append(asset.id)
            self._service.delete_release(release.id)
            deleted_release_ids.append(release.id)
        for ref in self._service.list_matching_tag_refs(release_tag):
            if ref.endswith(f"/{release_tag}"):
                self._service.delete_tag_ref(release_tag)
                break
        _, remaining = poll_until(
            probe=lambda: {
                "releases": serialize(self._service.fetch_releases_by_tag_any_state(release_tag)),
                "tag_refs": self._service.list_matching_tag_refs(release_tag),
            },
            is_satisfied=lambda value: len(value["releases"]) == 0 and len(value["tag_refs"]) == 0,
            timeout_seconds=120,
            interval_seconds=5,
        )
        return {
            "status": "deleted"
            if len(remaining["releases"]) == 0 and len(remaining["tag_refs"]) == 0
            else "failed",
            "release_tag": release_tag,
            "deleted_release_ids": tuple(deleted_release_ids),
            "deleted_asset_ids": tuple(deleted_asset_ids),
            "remaining": remaining,
        }


def serialize(value: object) -> object:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return [serialize(item) for item in value]
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value
