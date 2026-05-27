from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from testing.core.models.cli_command_result import CliCommandResult
from testing.frameworks.python.trackstate_cli_session_contract_framework import (
    PythonTrackStateCliSessionContractFramework,
)


class TrackStateCliSessionContractFrameworkRegressionTest(unittest.TestCase):
    def test_run_preferred_command_uses_repo_local_dart_command(self) -> None:
        framework = PythonTrackStateCliSessionContractFramework(Path.cwd())
        repository_path = Path("/tmp/ts-272-repo")
        requested_command = (
            "trackstate",
            "session",
            "--target",
            "local",
            "--path",
            str(repository_path),
        )
        fallback_command = (
            "dart",
            "run",
            "trackstate",
            "session",
            "--target",
            "local",
            "--path",
            str(repository_path),
        )
        expected_result = CliCommandResult(
            command=(),
            exit_code=0,
            stdout="{}",
            stderr="",
            json_payload={},
        )

        with (
            patch.dict(os.environ, {"TRACKSTATE_DART_BIN": "/custom/dart"}, clear=False),
            patch.object(framework, "_run", return_value=expected_result) as run_mock,
        ):
            observation = framework._run_preferred_command(
                requested_command=requested_command,
                fallback_command=fallback_command,
                repository_path=repository_path,
            )

        self.assertEqual(
            observation.executed_command,
            (
                "/custom/dart",
                "run",
                "trackstate",
                "session",
                "--target",
                "local",
                "--path",
                str(repository_path),
            ),
        )
        self.assertIn("repository-local CLI", observation.fallback_reason or "")
        run_mock.assert_called_once_with(observation.executed_command)


if __name__ == "__main__":
    unittest.main()
