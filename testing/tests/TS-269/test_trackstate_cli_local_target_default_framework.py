from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from testing.core.models.cli_command_result import CliCommandResult
from testing.frameworks.python.trackstate_cli_local_target_default_framework import (
    PythonTrackStateCliLocalTargetDefaultFramework,
)


class TrackStateCliLocalTargetDefaultFrameworkRegressionTest(unittest.TestCase):
    def test_run_from_repository_cwd_without_path_argument(self) -> None:
        framework = PythonTrackStateCliLocalTargetDefaultFramework(Path.cwd())
        repository_path = Path("/tmp/ts-269-repo")
        expected_result = CliCommandResult(
            command=(),
            exit_code=0,
            stdout="{}",
            stderr="",
            json_payload={},
        )

        with (
            patch.dict(os.environ, {"TRACKSTATE_DART_BIN": "/custom/dart"}, clear=False),
            patch.object(framework, "_seed_local_repository") as seed_mock,
            patch.object(framework, "_run", return_value=expected_result) as run_mock,
        ):
            observation = framework.observe_default_json_session(
                config=self._config_for_probe(),
            )

        seed_mock.assert_called_once()
        self.assertEqual(
            observation.executed_command,
            (
                "/custom/dart",
                str(Path.cwd() / "bin" / "trackstate.dart"),
                "--target",
                "local",
            ),
        )
        self.assertEqual(observation.repository_path, str(run_mock.call_args.kwargs["cwd"]))
        self.assertNotIn("--path", observation.executed_command_text)
        run_mock.assert_called_once_with(
            observation.executed_command,
            cwd=run_mock.call_args.kwargs["cwd"],
        )

    @staticmethod
    def _config_for_probe():
        from dataclasses import replace

        from testing.core.config.trackstate_cli_session_contract_config import (
            TrackStateCliSessionContractConfig,
        )

        base_config = TrackStateCliSessionContractConfig.from_env()
        return replace(
            base_config,
            requested_command_prefix=("trackstate", "--target", "local"),
            fallback_command_prefix=("dart", "run", "trackstate", "--target", "local"),
        )


if __name__ == "__main__":
    unittest.main()
