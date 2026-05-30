from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.hosted_auth_precedence_cli_validator import (
    HostedAuthPrecedenceCliValidator,
)
from testing.core.config.hosted_auth_precedence_cli_config import (
    HostedAuthPrecedenceCliConfig,
)
from testing.tests.support.hosted_auth_precedence_cli_probe_factory import (
    create_hosted_auth_precedence_cli_probe,
)


class HostedAuthPrecedenceExplicitTokenOverrideTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = HostedAuthPrecedenceCliConfig.from_env()
        self.validator = HostedAuthPrecedenceCliValidator(
            repository_root=self.repository_root,
            probe=create_hosted_auth_precedence_cli_probe(self.repository_root),
        )

    def test_explicit_invalid_token_overrides_valid_environment_token(self) -> None:
        result = self.validator.validate(config=self.config)
        token_probe = result.token_resolution.probe_result

        self.assertTrue(
            result.token_resolution.succeeded,
            "Precondition failed: TS-271 could not obtain a valid hosted token from "
            "TS271_VALID_TRACKSTATE_TOKEN, TRACKSTATE_TOKEN, or `gh auth token`.\n"
            f"Resolved source: {result.token_resolution.source}\n"
            f"Command: {token_probe.command_text if token_probe else 'not run'}\n"
            f"Exit code: {token_probe.exit_code if token_probe else 'n/a'}\n"
            f"stderr:\n{token_probe.stderr if token_probe else ''}",
        )
        self.assertIn(
            result.token_resolution.source,
            ("TS271_VALID_TRACKSTATE_TOKEN", "TRACKSTATE_TOKEN", "gh auth token"),
            "Precondition failed: TS-271 resolved an unexpected credential source.\n"
            f"Observed source: {result.token_resolution.source}",
        )

        baseline = result.environment_session
        self.assertIsNotNone(
            baseline,
            "Precondition failed: TS-271 could not run the baseline hosted session "
            "with the environment token.",
        )
        assert baseline is not None

        baseline_payload = baseline.result.json_payload
        baseline_payload_dict = (
            baseline_payload if isinstance(baseline_payload, dict) else {}
        )
        baseline_data = baseline_payload_dict.get("data")
        baseline_data_dict = baseline_data if isinstance(baseline_data, dict) else {}

        self.assertEqual(
            baseline.requested_command,
            self.config.requested_environment_command,
            "Step 1 failed: the automation did not target the hosted session command "
            "required for the environment-backed control run.\n"
            f"Expected command: {' '.join(self.config.requested_environment_command)}\n"
            f"Observed command: {baseline.requested_command_text}",
        )
        self.assertEqual(
            baseline.result.exit_code,
            0,
            "Step 1 failed: the hosted session did not succeed when only the valid "
            "environment token was available, so the precedence precondition was not "
            "satisfied.\n"
            f"Requested command: {baseline.requested_command_text}\n"
            f"Executed command: {baseline.executed_command_text}\n"
            f"Fallback reason: {baseline.fallback_reason}\n"
            f"stdout:\n{baseline.result.stdout}\n"
            f"stderr:\n{baseline.result.stderr}",
        )
        self.assertIs(
            baseline_payload_dict.get("ok"),
            True,
            "Step 1 failed: the baseline hosted session did not return a success "
            "JSON envelope.\n"
            f"Observed payload: {baseline_payload_dict}",
        )
        self.assertEqual(
            baseline_data_dict.get("authSource"),
            self.config.expected_success_auth_source,
            "Step 1 failed: the successful baseline run did not visibly report the "
            "environment credential source.\n"
            f"Observed payload: {baseline_payload_dict}",
        )
        self.assertEqual(
            baseline_payload_dict.get("provider"),
            self.config.provider,
            "Step 1 failed: the baseline run targeted the wrong hosted provider.\n"
            f"Observed payload: {baseline_payload_dict}",
        )
        self.assertEqual(
            (baseline_payload_dict.get("target") or {}).get("value")
            if isinstance(baseline_payload_dict.get("target"), dict)
            else None,
            self.config.repository,
            "Step 1 failed: the baseline run targeted the wrong hosted repository.\n"
            f"Observed payload: {baseline_payload_dict}",
        )

        explicit_override = result.explicit_invalid_token_session
        self.assertIsNotNone(
            explicit_override,
            "Step 2 failed: TS-271 could not rerun the hosted session with the "
            "explicit invalid token.",
        )
        assert explicit_override is not None

        failure_payload = explicit_override.result.json_payload
        failure_payload_dict = (
            failure_payload if isinstance(failure_payload, dict) else {}
        )
        failure_error = failure_payload_dict.get("error")
        failure_error_dict = failure_error if isinstance(failure_error, dict) else {}
        failure_details = failure_error_dict.get("details")
        failure_details_dict = (
            failure_details if isinstance(failure_details, dict) else {}
        )

        self.assertEqual(
            explicit_override.requested_command,
            self.config.requested_invalid_token_command,
            "Step 2 failed: the automation did not execute the hosted session with "
            "the explicit invalid token override required by TS-271.\n"
            f"Expected command: {' '.join(self.config.requested_invalid_token_command)}\n"
            f"Observed command: {explicit_override.requested_command_text}",
        )
        self.assertEqual(
            explicit_override.result.exit_code,
            self.config.expected_failure_exit_code,
            "Step 2 failed: the hosted session did not exit with the documented "
            "authentication failure status after the explicit invalid token was "
            "passed.\n"
            f"Requested command: {explicit_override.requested_command_text}\n"
            f"Executed command: {explicit_override.executed_command_text}\n"
            f"Fallback reason: {explicit_override.fallback_reason}\n"
            f"stdout:\n{explicit_override.result.stdout}\n"
            f"stderr:\n{explicit_override.result.stderr}",
        )
        self.assertIs(
            failure_payload_dict.get("ok"),
            False,
            "Step 2 failed: the explicit invalid-token run did not report a failed "
            "JSON envelope.\n"
            f"Observed payload: {failure_payload_dict}",
        )
        self.assertEqual(
            failure_error_dict.get("code"),
            self.config.expected_failure_error_code,
            "Step 2 failed: the explicit invalid-token run did not map to the "
            "documented hosted authentication error code.\n"
            f"Observed payload: {failure_payload_dict}",
        )
        self.assertEqual(
            failure_error_dict.get("category"),
            self.config.expected_failure_error_category,
            "Step 2 failed: the explicit invalid-token run did not map to the "
            "documented hosted authentication error category.\n"
            f"Observed payload: {failure_payload_dict}",
        )
        self.assertEqual(
            failure_error_dict.get("message"),
            self.config.expected_visible_failure_message,
            "Step 2 failed: the terminal-visible error message changed from the "
            "documented hosted authentication contract.\n"
            f"Observed payload: {failure_payload_dict}",
        )
        self.assertEqual(
            failure_details_dict.get("provider"),
            self.config.provider,
            "Step 2 failed: the failed JSON envelope did not identify the hosted "
            "provider under test.\n"
            f"Observed payload: {failure_payload_dict}",
        )
        self.assertEqual(
            failure_details_dict.get("repository"),
            self.config.repository,
            "Step 2 failed: the failed JSON envelope did not identify the hosted "
            "repository under test.\n"
            f"Observed payload: {failure_payload_dict}",
        )
        reason_text = str(failure_details_dict.get("reason", ""))
        for fragment in self.config.expected_failure_reason_fragments:
            self.assertIn(
                fragment,
                reason_text,
                "Step 2 failed: the authentication failure details no longer make it "
                "clear that the explicit token itself was rejected by GitHub.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed payload: {failure_payload_dict}",
            )

        self.assertNotIn(
            "--token",
            baseline.executed_command_text,
            "Precondition failed: the control run unexpectedly included an explicit "
            "token flag, so it could not validate environment-token behavior.\n"
            f"Executed command: {baseline.executed_command_text}",
        )
        self.assertIn(
            "--token",
            explicit_override.executed_command_text,
            "Step 2 failed: the invalid-token run did not visibly include the "
            "explicit token argument.\n"
            f"Executed command: {explicit_override.executed_command_text}",
        )
        self.assertIn(
            self.config.invalid_explicit_token,
            explicit_override.executed_command_text,
            "Step 2 failed: the invalid-token run did not use the ticketed explicit "
            "token value.\n"
            f"Executed command: {explicit_override.executed_command_text}",
        )

        self.assertIn(
            '"authSource": "env"',
            baseline.result.stdout,
            "Human-style verification failed: the successful control run did not "
            "visibly show that the environment variable supplied the hosted token.\n"
            f"Observed stdout:\n{baseline.result.stdout}",
        )
        for visible_fragment in (
            self.config.expected_failure_error_code,
            self.config.expected_visible_failure_message,
            *self.config.expected_failure_reason_fragments,
        ):
            self.assertIn(
                visible_fragment,
                explicit_override.output,
                "Human-style verification failed: the terminal output for the "
                "explicit invalid-token run did not visibly show the expected hosted "
                "authentication failure.\n"
                f"Missing fragment: {visible_fragment}\n"
                f"Observed output:\n{explicit_override.output}",
            )


if __name__ == "__main__":
    unittest.main()
