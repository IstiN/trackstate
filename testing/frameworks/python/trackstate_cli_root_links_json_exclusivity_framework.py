from __future__ import annotations

import json
import tempfile
from pathlib import Path

from testing.core.config.trackstate_cli_root_links_json_exclusivity_config import (
    TrackStateCliRootLinksJsonExclusivityConfig,
)
from testing.core.interfaces.trackstate_cli_root_links_json_exclusivity_probe import (
    TrackStateCliRootLinksJsonExclusivityProbe,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_root_links_json_exclusivity_result import (
    TrackStateCliRootLinksJsonExclusivityObservation,
    TrackStateCliRootLinksJsonExclusivityValidationResult,
    TrackStateCliRootLinksJsonSnapshot,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonTrackStateCliRootLinksJsonExclusivityFramework(
    PythonTrackStateCliCompiledLocalFramework,
    TrackStateCliRootLinksJsonExclusivityProbe,
):
    def __init__(self, repository_root: Path) -> None:
        super().__init__(repository_root)

    def observe_root_links_json_exclusivity(
        self,
        *,
        config: TrackStateCliRootLinksJsonExclusivityConfig,
    ) -> TrackStateCliRootLinksJsonExclusivityValidationResult:
        test_prefix = config.test_id.lower()
        with tempfile.TemporaryDirectory(
            prefix=f"trackstate-{test_prefix}-bin-"
        ) as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(
                prefix=f"trackstate-{test_prefix}-repo-"
            ) as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path, config=config)
                fallback_reason = (
                    "Pinned execution to a temporary executable compiled from this "
                    f"checkout so {config.test_id} exercises the live local CLI against "
                    "a seeded disposable repository."
                )
                issue_a_create_observation = self._observe_command(
                    requested_command=config.issue_a_create_command(str(repository_path)),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                issue_b_create_observation = self._observe_command(
                    requested_command=config.issue_b_create_command(str(repository_path)),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )
                link_observation = self._observe_command(
                    requested_command=config.link_command(str(repository_path)),
                    repository_path=repository_path,
                    executable_path=executable_path,
                    fallback_reason=fallback_reason,
                )

                discovered_snapshots = tuple(
                    TrackStateCliRootLinksJsonSnapshot(
                        relative_path=str(path.relative_to(repository_path)),
                        content=self._read_text_if_exists(path),
                        payload=self._read_json_if_exists(path),
                    )
                    for path in sorted(repository_path.rglob("links.json"))
                )
                issue_a_directory = repository_path / config.issue_a_directory_relative_path
                issue_b_directory = repository_path / config.issue_b_directory_relative_path
                issue_a_main_path = repository_path / config.issue_a_main_relative_path
                issue_b_main_path = repository_path / config.issue_b_main_relative_path
                root_links_json_path = repository_path / config.root_links_json_relative_path

                return TrackStateCliRootLinksJsonExclusivityValidationResult(
                    observation=TrackStateCliRootLinksJsonExclusivityObservation(
                        issue_a_create_observation=issue_a_create_observation,
                        issue_b_create_observation=issue_b_create_observation,
                        link_observation=link_observation,
                        root_links_json_relative_path=config.root_links_json_relative_path,
                        root_links_json_content=self._read_text_if_exists(
                            root_links_json_path
                        ),
                        root_links_json_payload=self._read_json_if_exists(
                            root_links_json_path
                        ),
                        discovered_links_json_files=tuple(
                            snapshot.relative_path
                            for snapshot in discovered_snapshots
                        ),
                        discovered_links_json_snapshots=discovered_snapshots,
                        issue_a_directory_relative_path=(
                            config.issue_a_directory_relative_path
                        ),
                        issue_a_directory_entries=self._directory_entries(
                            issue_a_directory
                        ),
                        issue_a_main_relative_path=config.issue_a_main_relative_path,
                        issue_a_main_content=self._read_text_if_exists(issue_a_main_path),
                        issue_b_directory_relative_path=(
                            config.issue_b_directory_relative_path
                        ),
                        issue_b_directory_entries=self._directory_entries(
                            issue_b_directory
                        ),
                        issue_b_main_relative_path=config.issue_b_main_relative_path,
                        issue_b_main_content=self._read_text_if_exists(issue_b_main_path),
                    )
                )

    def _observe_command(
        self,
        *,
        requested_command: tuple[str, ...],
        repository_path: Path,
        executable_path: Path,
        fallback_reason: str,
    ) -> TrackStateCliCommandObservation:
        executed_command = (str(executable_path), *requested_command[1:])
        return TrackStateCliCommandObservation(
            requested_command=requested_command,
            executed_command=executed_command,
            fallback_reason=fallback_reason,
            repository_path=str(repository_path),
            compiled_binary_path=str(executable_path),
            result=self._run(executed_command, cwd=repository_path),
        )

    def _seed_local_repository(
        self,
        repository_path: Path,
        *,
        config: TrackStateCliRootLinksJsonExclusivityConfig,
    ) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / f"{config.project_key}/project.json",
            json.dumps({"key": config.project_key, "name": config.project_name}) + "\n",
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/statuses.json",
            '[{"id":"todo","name":"To Do"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/priorities.json",
            '[{"id":"medium","name":"Medium"}]\n',
        )
        self._write_file(
            repository_path / f"{config.project_key}/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / config.project_key / config.seed_issue_key / "main.md",
            f"""---
key: {config.seed_issue_key}
project: {config.project_key}
issueType: story
status: todo
priority: medium
summary: "Seed Issue"
assignee: seed-user
reporter: seed-user
updated: 2026-05-25T00:00:00Z
---

# Summary

Seed Issue

# Description

Initial issue so the local mutation service can open the repository.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(
            repository_path,
            "config",
            "--local",
            "user.name",
            f"{config.test_id} Tester",
        )
        self._git(
            repository_path,
            "config",
            "--local",
            "user.email",
            config.expected_author_email,
        )
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", f"Seed {config.test_id} fixture")

    @staticmethod
    def _directory_entries(path: Path) -> tuple[str, ...]:
        if not path.is_dir():
            return ()
        return tuple(sorted(entry.name for entry in path.iterdir()))

    @staticmethod
    def _read_json_if_exists(path: Path) -> object | None:
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None
