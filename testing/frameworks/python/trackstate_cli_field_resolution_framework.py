from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile

from testing.core.config.trackstate_cli_field_resolution_config import (
    TrackStateCliFieldResolutionConfig,
)
from testing.core.interfaces.trackstate_cli_field_resolution_probe import (
    TrackStateCliFieldResolutionProbe,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_field_resolution_result import (
    TrackStateCliFieldCommandObservation,
    TrackStateCliFieldResolutionObservation,
)


class PythonTrackStateCliFieldResolutionFramework(
    TrackStateCliFieldResolutionProbe
):
    def __init__(self, repository_root: Path) -> None:
        self._repository_root = Path(repository_root)

    def observe_field_resolution(
        self,
        *,
        config: TrackStateCliFieldResolutionConfig,
    ) -> TrackStateCliFieldResolutionObservation:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-458-") as temp_dir:
            repository_path = Path(temp_dir)
            self._seed_local_repository(repository_path, config=config)
            issue_path = repository_path / config.project_key / config.issue_key / "main.md"

            exact_requested_command = self._requested_command(
                config=config,
                repository_path=repository_path,
                field=config.exact_field_identifier,
                value=config.exact_field_value,
            )
            exact_executed_command = self._executed_command(
                config=config,
                repository_path=repository_path,
                field=config.exact_field_identifier,
                value=config.exact_field_value,
            )
            display_requested_command = self._requested_command(
                config=config,
                repository_path=repository_path,
                field=config.display_name_identifier,
                value=config.display_name_value,
            )
            display_executed_command = self._executed_command(
                config=config,
                repository_path=repository_path,
                field=config.display_name_identifier,
                value=config.display_name_value,
            )
            ambiguous_requested_command = self._requested_command(
                config=config,
                repository_path=repository_path,
                field=config.ambiguous_field_identifier,
                value=config.ambiguous_field_value,
            )
            ambiguous_executed_command = self._executed_command(
                config=config,
                repository_path=repository_path,
                field=config.ambiguous_field_identifier,
                value=config.ambiguous_field_value,
            )
            fallback_reason = (
                "Pinned execution to the repository-local CLI via `dart run trackstate` "
                "so TS-458 exercises this checkout against a disposable Local Git "
                "repository instead of any unrelated `trackstate` binary on PATH."
            )

            initial_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            initial_commit_count = int(
                self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
            )

            exact_result = self._run(exact_executed_command)
            after_exact_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            after_exact_commit_count = int(
                self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
            )

            display_result = self._run(display_executed_command)
            after_display_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            after_display_commit_count = int(
                self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
            )
            after_display_latest_commit_subject = self._git_output(
                repository_path,
                "log",
                "-1",
                "--pretty=%s",
            ).strip()

            self._introduce_field_name_conflict(
                repository_path=repository_path,
                config=config,
            )
            self._git(repository_path, "add", f"{config.project_key}/config/fields.json")
            self._git(
                repository_path,
                "commit",
                "-m",
                "Seed TS-458 ambiguous field names",
            )
            before_ambiguous_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            before_ambiguous_commit_count = int(
                self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
            )
            ambiguous_result = self._run(ambiguous_executed_command)

            final_head_revision = self._git_output(
                repository_path,
                "rev-parse",
                "HEAD",
            ).strip()
            final_commit_count = int(
                self._git_output(repository_path, "rev-list", "--count", "HEAD").strip()
            )
            latest_commit_subject = self._git_output(
                repository_path,
                "log",
                "-1",
                "--pretty=%s",
            ).strip()
            git_status = self._git_output(repository_path, "status", "--short")
            main_file_content = issue_path.read_text(encoding="utf-8")

            return TrackStateCliFieldResolutionObservation(
                fallback_reason=fallback_reason,
                repository_path=str(repository_path),
                initial_head_revision=initial_head_revision,
                after_exact_head_revision=after_exact_head_revision,
                after_display_head_revision=after_display_head_revision,
                before_ambiguous_head_revision=before_ambiguous_head_revision,
                final_head_revision=final_head_revision,
                initial_commit_count=initial_commit_count,
                after_exact_commit_count=after_exact_commit_count,
                after_display_commit_count=after_display_commit_count,
                before_ambiguous_commit_count=before_ambiguous_commit_count,
                final_commit_count=final_commit_count,
                after_display_latest_commit_subject=after_display_latest_commit_subject,
                latest_commit_subject=latest_commit_subject,
                git_status=git_status,
                main_file_relative_path=str(issue_path.relative_to(repository_path)),
                main_file_content=main_file_content,
                exact_id=TrackStateCliFieldCommandObservation(
                    requested_command=exact_requested_command,
                    executed_command=exact_executed_command,
                    result=exact_result,
                ),
                display_name=TrackStateCliFieldCommandObservation(
                    requested_command=display_requested_command,
                    executed_command=display_executed_command,
                    result=display_result,
                ),
                ambiguous_name=TrackStateCliFieldCommandObservation(
                    requested_command=ambiguous_requested_command,
                    executed_command=ambiguous_executed_command,
                    result=ambiguous_result,
                ),
            )

    def _run(self, command: tuple[str, ...]) -> CliCommandResult:
        env = os.environ.copy()
        env.setdefault("CI", "true")
        env.setdefault("PUB_CACHE", str(Path.home() / ".pub-cache"))
        completed = subprocess.run(
            command,
            cwd=self._repository_root,
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

    @staticmethod
    def _parse_json(stdout: str) -> object | None:
        payload = stdout.strip()
        if not payload:
            return None
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            return None

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliFieldResolutionConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/project.json",
            json.dumps({"key": config.project_key, "name": config.project_name}) + "\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        fields_content = json.dumps(
            [
                {
                    "id": "summary",
                    "name": "Summary",
                    "type": "string",
                    "required": True,
                },
                {
                    "id": "description",
                    "name": "Description",
                    "type": "markdown",
                    "required": False,
                },
                *[
                    {
                        "id": field_id,
                        "name": field_name,
                        "type": field_type,
                        "required": False,
                    }
                    for field_id, field_name, field_type in config.custom_field_definitions
                ],
            ]
        ) + "\n"
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            fields_content,
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/priorities.json",
            '[{"id":"medium","name":"Medium"},{"id":"high","name":"High"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/resolutions.json",
            '[{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/workflows.json",
            (
                '{"default":{"statuses":["To Do","Done"],"transitions":'
                '[{"id":"complete","name":"Complete","from":"To Do","to":"Done"}]}}\n'
            ),
        )
        main_file_content = f"""---
key: {config.issue_key}
project: {config.project_key}
issueType: story
status: todo
priority: {config.initial_priority_id}
summary: "{config.initial_summary}"
assignee: {config.initial_assignee}
reporter: {config.initial_assignee}
customFields: {json.dumps(dict(config.initial_custom_fields), separators=(",", ":"))}
updated: 2026-05-12T00:00:00Z
---

# Summary

{config.initial_summary}

# Description

Seeded issue for TS-458.
"""
        self._write_file(
            repository_path / config.project_key / config.issue_key / "main.md",
            main_file_content,
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/tombstones.json",
            '[]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/.trackstate/index/issues.json",
            json.dumps(
                [
                    {
                        "key": config.issue_key,
                        "path": f"{config.project_key}/{config.issue_key}/main.md",
                        "parent": None,
                        "epic": None,
                        "summary": config.initial_summary,
                        "issueType": "story",
                        "status": "todo",
                        "priority": config.initial_priority_id,
                        "assignee": config.initial_assignee,
                        "labels": [],
                        "updated": "2026-05-12T00:00:00Z",
                        "revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                        "children": [],
                        "archived": False,
                    }
                ]
            )
            + "\n",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-458 Tester")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            "ts458@example.com",
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-458 fixture")
        return None

    def _introduce_field_name_conflict(
        self,
        *,
        repository_path: Path,
        config: TrackStateCliFieldResolutionConfig,
    ) -> None:
        fields_path = repository_path / config.project_key / "config" / "fields.json"
        definitions = json.loads(fields_path.read_text(encoding="utf-8"))
        assert isinstance(definitions, list)
        conflicted = []
        for entry in definitions:
            assert isinstance(entry, dict)
            normalized = dict(entry)
            if normalized.get("id") in config.ambiguous_field_ids:
                normalized["name"] = config.conflict_display_name
            conflicted.append(normalized)
        self._write_file(fields_path, json.dumps(conflicted) + "\n")

    @staticmethod
    def _requested_command(
        *,
        config: TrackStateCliFieldResolutionConfig,
        repository_path: Path,
        field: str,
        value: int,
    ) -> tuple[str, ...]:
        return (
            *config.requested_command_prefix,
            "--path",
            str(repository_path),
            "--key",
            config.issue_key,
            "--field",
            field,
            "--value",
            str(value),
        )

    @staticmethod
    def _executed_command(
        *,
        config: TrackStateCliFieldResolutionConfig,
        repository_path: Path,
        field: str,
        value: int,
    ) -> tuple[str, ...]:
        return (
            *config.fallback_command_prefix,
            "--path",
            str(repository_path),
            "--key",
            config.issue_key,
            "--field",
            field,
            "--value",
            str(value),
        )

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _git(repository_path: Path, *args: str) -> None:
        completed = subprocess.run(
            ("git", "-C", str(repository_path), *args),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed for {repository_path}.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )

    @staticmethod
    def _git_output(repository_path: Path, *args: str) -> str:
        completed = subprocess.run(
            ("git", "-C", str(repository_path), *args),
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed for {repository_path}.\n"
                f"stdout:\n{completed.stdout}\n"
                f"stderr:\n{completed.stderr}"
            )
        return completed.stdout
