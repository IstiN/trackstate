from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_release_existing_tag_config import (
    TrackStateCliReleaseExistingTagConfig,
)
from testing.core.interfaces.trackstate_cli_release_existing_tag_probe import (
    TrackStateCliReleaseExistingTagProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_existing_tag_result import (
    TrackStateCliReleaseExistingTagRepositoryState,
    TrackStateCliReleaseExistingTagStoredFile,
    TrackStateCliReleaseExistingTagValidationResult,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliReleaseExistingTagFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliReleaseExistingTagProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_release_existing_tag(
        self,
        *,
        config: TrackStateCliReleaseExistingTagConfig,
        remote_origin_url: str,
        token: str,
    ) -> TrackStateCliReleaseExistingTagValidationResult:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-555-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-555-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(
                    repository_path=repository_path,
                    config=config,
                    remote_origin_url=remote_origin_url,
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
                return TrackStateCliReleaseExistingTagValidationResult(
                    initial_state=initial_state,
                    final_state=final_state,
                    observation=observation,
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
        sandbox_home = repository_path / ".ts555-home"
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
                "and injected the GitHub credential through TRACKSTATE_TOKEN so TS-555 "
                "runs the exact local release-backed upload command against a disposable "
                "repository with a live GitHub origin."
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
        config: TrackStateCliReleaseExistingTagConfig,
        remote_origin_url: str,
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
updated: 2026-05-13T00:00:00Z
---

# Description

TS-555 local github-releases existing-tag fixture.
""",
        )
        self._write_binary_file(
            repository_path / config.source_file_name,
            config.source_file_bytes,
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-555 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts555@example.com",
        )
        self._git(repository_path, "remote", "add", "origin", remote_origin_url)
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-555 fixture")

    def _capture_repository_state(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliReleaseExistingTagConfig,
    ) -> TrackStateCliReleaseExistingTagRepositoryState:
        issue_main = repository_path / config.issue_path / "main.md"
        metadata_path = repository_path / config.manifest_path
        attachment_directory = repository_path / config.issue_path / "attachments"
        expected_attachment = repository_path / config.expected_attachment_relative_path
        metadata_summary = self._metadata_summary(
            metadata_path=metadata_path,
            expected_attachment_name=config.expected_attachment_name,
        )
        stored_files = (
            tuple(
                sorted(
                    (
                        TrackStateCliReleaseExistingTagStoredFile(
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
        remote_origin_url = self._git_output(
            repository_path,
            "remote",
            "get-url",
            "origin",
        ).strip()
        return TrackStateCliReleaseExistingTagRepositoryState(
            issue_main_exists=issue_main.is_file(),
            attachments_metadata_exists=metadata_path.is_file(),
            attachments_metadata_text=metadata_summary["metadata_text"],
            matching_attachment_entries=metadata_summary["matching_attachment_entries"],
            metadata_attachment_ids=metadata_summary["attachment_ids"],
            metadata_storage_backends=metadata_summary["storage_backends"],
            metadata_release_tags=metadata_summary["release_tags"],
            metadata_release_asset_names=metadata_summary["release_asset_names"],
            attachment_directory_exists=attachment_directory.is_dir(),
            expected_attachment_exists=expected_attachment.is_file(),
            stored_files=stored_files,
            git_status_lines=self._git_status_lines(repository_path),
            remote_origin_url=remote_origin_url or None,
            head_commit_subject=self._git_head_subject(repository_path),
            head_commit_count=self._git_head_count(repository_path),
        )

    def _metadata_summary(
        self,
        *,
        metadata_path: Path,
        expected_attachment_name: str,
    ) -> dict[str, object]:
        empty_strings: tuple[str, ...] = ()
        empty_entries: tuple[dict[str, object], ...] = ()
        if not metadata_path.is_file():
            return {
                "metadata_text": None,
                "matching_attachment_entries": empty_entries,
                "attachment_ids": empty_strings,
                "storage_backends": empty_strings,
                "release_tags": empty_strings,
                "release_asset_names": empty_strings,
            }
        metadata_text = metadata_path.read_text(encoding="utf-8")
        try:
            payload = json.loads(metadata_text)
        except json.JSONDecodeError:
            return {
                "metadata_text": metadata_text,
                "matching_attachment_entries": empty_entries,
                "attachment_ids": empty_strings,
                "storage_backends": empty_strings,
                "release_tags": empty_strings,
                "release_asset_names": empty_strings,
            }
        if not isinstance(payload, list):
            return {
                "metadata_text": metadata_text,
                "matching_attachment_entries": empty_entries,
                "attachment_ids": empty_strings,
                "storage_backends": empty_strings,
                "release_tags": empty_strings,
                "release_asset_names": empty_strings,
            }
        attachment_ids: list[str] = []
        storage_backends: list[str] = []
        release_tags: list[str] = []
        release_asset_names: list[str] = []
        matching_attachment_entries: list[dict[str, object]] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            attachment_ids.append(str(entry.get("id", "")))
            storage_backends.append(str(entry.get("storageBackend", "")))
            release_tags.append(str(entry.get("githubReleaseTag", "")))
            release_asset_names.append(str(entry.get("githubReleaseAssetName", "")))
            if str(entry.get("name", "")) == expected_attachment_name:
                matching_attachment_entries.append(dict(entry))
        return {
            "metadata_text": metadata_text,
            "matching_attachment_entries": tuple(matching_attachment_entries),
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
