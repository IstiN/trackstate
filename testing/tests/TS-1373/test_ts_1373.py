from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from testing.components.services.trackstate_cli_session_contract_validator import (
    TrackStateCliSessionContractValidator,
)
from testing.core.config.trackstate_cli_session_contract_config import (
    TrackStateCliSessionContractConfig,
)
from testing.tests.support.trackstate_cli_session_contract_probe_factory import (
    create_trackstate_cli_session_contract_probe,
)


class TrackStateLocalAuthSourceRegressionTest(unittest.TestCase):
    """TS-1373: local-target sessions must not inherit hosted GitHub auth state."""

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliSessionContractConfig.from_env()
        self.validator = TrackStateCliSessionContractValidator(
            probe=create_trackstate_cli_session_contract_probe(self.repository_root)
        )

    def test_local_target_ignores_ambient_github_tokens(self) -> None:
        # Simulate an environment where a GitHub CLI token is available.
        # The CLI must not report "gh" as the auth source for a local target.
        ambient_github_tokens = {
            "GH_TOKEN": "ghp_trackstate_regression_dummy_token",
            "GITHUB_TOKEN": "ghp_trackstate_regression_dummy_token",
        }

        with patch.dict(os.environ, ambient_github_tokens, clear=False):
            observation = self.validator.validate(config=self.config).observation

        self.assertTrue(
            observation.result.succeeded,
            "Step 1 failed: the TrackState session command did not complete "
            "successfully against the seeded Local Git repository.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Repository path: {observation.repository_path}\n"
            f"Exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        self.assertIsInstance(
            payload,
            dict,
            "Step 2 failed: the CLI did not return a valid JSON object by default.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        assert isinstance(payload, dict)

        data = payload.get("data")
        self.assertIsInstance(
            data,
            dict,
            "Expected result failed: the command data payload was not encoded as an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(data, dict)

        self.assertEqual(
            data.get("authSource"),
            "none",
            "Expected result failed: a local-target session must report authSource 'none' "
            "even when ambient GitHub CLI tokens are present.\n"
            f"Injected tokens: {list(ambient_github_tokens.keys())}\n"
            f"Observed data: {data}",
        )

        # Human-style verification: the emitted stdout must visibly show the local
        # auth source and must not show a hosted GitHub auth source.
        stdout = observation.result.stdout
        self.assertIn(
            '"authSource": "none"',
            stdout,
            "Human-style verification failed: the emitted stdout did not visibly show "
            "the local-only authSource a user would inspect.\n"
            f"stdout:\n{stdout}",
        )
        self.assertNotIn(
            '"authSource": "gh"',
            stdout,
            "Regression check failed: the emitted stdout still reports a hosted GitHub "
            "auth source for a local-target session.\n"
            f"stdout:\n{stdout}",
        )


if __name__ == "__main__":
    unittest.main()
