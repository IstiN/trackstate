from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_read_profile_local_validator import (
    TrackStateCliReadProfileLocalValidator,
)
from testing.core.config.trackstate_cli_read_profile_local_config import (
    TrackStateCliReadProfileLocalConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_read_profile_local_probe_factory import (
    create_trackstate_cli_read_profile_local_probe,
)


class TrackStateCliReadProfileLocalIdentityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliReadProfileLocalConfig.from_defaults()
        self.validator = TrackStateCliReadProfileLocalValidator(
            probe=create_trackstate_cli_read_profile_local_probe(self.repository_root)
        )

    def test_read_profile_returns_jira_user_derived_from_local_git_identity(
        self,
    ) -> None:
        observation = self.validator.validate(config=self.config).observation
        payload = self._assert_successful_payload(
            observation=observation,
            expected_command=self.config.requested_command,
            failure_prefix="Step 1 failed",
        )

        missing_keys = [
            key for key in self.config.required_keys if key not in payload
        ]
        self.assertFalse(
            missing_keys,
            "Step 2 failed: the CLI did not return the required Jira user fields.\n"
            f"Missing keys: {missing_keys}\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["displayName"],
            self.config.user_name,
            "Expected result failed: the Jira user object did not map "
            "`git config user.name` into `displayName`.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["emailAddress"],
            self.config.user_email,
            "Expected result failed: the Jira user object did not map "
            "`git config user.email` into `emailAddress`.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["accountId"],
            self.config.user_email,
            "Expected result failed: the Jira user object did not derive "
            "`accountId` from the local Git identifier.\n"
            f"Observed payload: {payload}",
        )
        self.assertNotIn(
            "ok",
            payload,
            "Expected result failed: `trackstate read profile` returned a TrackState "
            "envelope instead of the raw Jira-shaped user object.\n"
            f"Observed payload: {payload}",
        )

        for fragment in (
            '"displayName": "John Doe"',
            '"emailAddress": "john@example.com"',
            '"accountId": "john@example.com"',
        ):
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the terminal JSON a user would "
                "inspect did not visibly show the expected Local Git identity "
                "mapping.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )

    def _assert_successful_payload(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        expected_command: tuple[str, ...],
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{failure_prefix}: TS-377 did not execute the exact ticket command.\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-377 must execute a repository-local compiled binary "
            "so the seeded Local Git repository stays the current working directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-377 did not run the compiled repository-local CLI "
            "binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did not "
            "complete successfully from the seeded Local Git repository.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            f"{failure_prefix}: `{observation.requested_command_text}` did not return a "
            "JSON object.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, dict)
        return payload


if __name__ == "__main__":
    unittest.main()
