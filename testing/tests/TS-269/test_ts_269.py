from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import os
import unittest

from testing.components.services.trackstate_cli_session_contract_validator import (
    TrackStateCliSessionContractValidator,
)
from testing.core.config.trackstate_cli_session_contract_config import (
    TrackStateCliSessionContractConfig,
)
from testing.tests.support.trackstate_cli_local_target_default_probe_factory import (
    create_trackstate_cli_local_target_default_probe,
)


class LocalTargetDefaultsToCurrentWorkingDirectoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        base_config = TrackStateCliSessionContractConfig.from_env()
        dart_bin = os.environ.get("TRACKSTATE_DART_BIN", "dart")
        self.config = replace(
            base_config,
            requested_command_prefix=("trackstate", "--target", "local"),
            fallback_command_prefix=(dart_bin, "run", "trackstate", "--target", "local"),
        )
        self.validator = TrackStateCliSessionContractValidator(
            probe=create_trackstate_cli_local_target_default_probe(self.repository_root)
        )

    def test_local_target_defaults_to_current_working_directory(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.requested_command,
            self.config.requested_command_prefix,
            "Precondition failed: TS-269 must execute the exact ticket command "
            "`trackstate --target local`.\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertNotIn(
            "--path",
            observation.executed_command_text,
            "Precondition failed: TS-269 unexpectedly provided --path instead of "
            "relying on the current working directory default.\n"
            f"Executed command: {observation.executed_command_text}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            "Step 1 failed: executing `trackstate --target local` from a valid Local "
            "Git repository did not proceed successfully.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Working directory: {observation.repository_path}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertIsInstance(
            observation.result.json_payload,
            dict,
            "Step 1 failed: the CLI did not emit a JSON object that exposed the "
            "resolved target metadata.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        assert isinstance(payload, dict)
        self.assertIs(
            payload.get("ok"),
            True,
            "Step 1 failed: the CLI reported a failed result instead of opening the "
            "current repository.\n"
            f"Observed payload: {payload}",
        )

        target = payload.get("target")
        self.assertIsInstance(
            target,
            dict,
            "Step 2 failed: the JSON output did not expose target metadata as an "
            "object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(target, dict)
        self.assertEqual(
            target.get("type"),
            "local",
            "Step 2 failed: the JSON output did not identify the resolved target as "
            "local.\n"
            f"Observed target: {target}",
        )
        self.assertEqual(
            target.get("value"),
            observation.repository_path,
            "Expected result failed: the CLI did not resolve the target path to the "
            "current working directory.\n"
            f"Expected path: {observation.repository_path}\n"
            f"Observed target: {target}",
        )
        self.assertIn(
            f'"value": "{observation.repository_path}"',
            observation.result.stdout,
            "Human-style verification failed: the terminal output did not visibly "
            "show the current working directory in the target field.\n"
            f"stdout:\n{observation.result.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
