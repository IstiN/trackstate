from __future__ import annotations

from pathlib import Path
import tempfile

from testing.core.config.account_by_email_unsupported_cli_config import (
    AccountByEmailUnsupportedCliConfig,
)
from testing.core.models.account_by_email_unsupported_cli_result import (
    AccountByEmailUnsupportedCliObservation,
)
from testing.frameworks.python.trackstate_cli_compiled_local_framework import (
    PythonTrackStateCliCompiledLocalFramework,
)


class PythonAccountByEmailUnsupportedCliFramework(
    PythonTrackStateCliCompiledLocalFramework
):
    def account_by_email_unsupported(
        self,
        *,
        config: AccountByEmailUnsupportedCliConfig,
    ) -> AccountByEmailUnsupportedCliObservation:
        with tempfile.TemporaryDirectory(prefix="trackstate-ts-378-bin-") as bin_dir:
            executable_path = Path(bin_dir) / "trackstate"
            self._compile_executable(executable_path)
            with tempfile.TemporaryDirectory(prefix="trackstate-ts-378-repo-") as temp_dir:
                repository_path = Path(temp_dir)
                self._seed_local_repository(repository_path)
                executed_command = (str(executable_path), *config.requested_command[1:])
                return AccountByEmailUnsupportedCliObservation(
                    requested_command=config.requested_command,
                    executed_command=executed_command,
                    fallback_reason=(
                        "Pinned execution to a temporary executable compiled from this "
                        "checkout so the exact ticket command runs from a seeded Local "
                        "Git repository instead of the detached-HEAD checkout root."
                    ),
                    repository_path=str(repository_path),
                    result=self._run(executed_command, cwd=repository_path),
                )

    def _seed_local_repository(self, repository_path: Path) -> None:
        repository_path.mkdir(parents=True, exist_ok=True)
        self._write_file(
            repository_path / ".gitattributes",
            "*.png filter=lfs diff=lfs merge=lfs -text\n",
        )
        self._write_file(
            repository_path / "DEMO/project.json",
            '{"key":"DEMO","name":"Local Demo"}\n',
        )
        self._write_file(
            repository_path / "DEMO/config/statuses.json",
            '[{"id":"todo","name":"To Do"},{"id":"done","name":"Done"}]\n',
        )
        self._write_file(
            repository_path / "DEMO/config/issue-types.json",
            '[{"id":"story","name":"Story"}]\n',
        )
        self._write_file(
            repository_path / "DEMO/config/fields.json",
            '[{"id":"summary","name":"Summary","type":"string","required":true}]\n',
        )
        self._write_file(
            repository_path / "DEMO/DEMO-1/main.md",
            """---
key: DEMO-1
project: DEMO
issueType: story
status: todo
summary: "TS-378 local account-by-email fixture"
assignee: ts378-user
reporter: ts378-user
updated: 2026-05-10T00:00:00Z
---

# Description

Local repository used to verify the unsupported account-by-email CLI contract.
""",
        )
        self._git(repository_path, "init", "-b", "main")
        self._git(repository_path, "config", "--local", "user.name", "TS-378 Tester")
        self._git(repository_path, "config", "--local", "user.email", "ts378@example.com")
        self._git(repository_path, "add", ".")
        self._git(repository_path, "commit", "-m", "Seed TS-378 local fixture")
