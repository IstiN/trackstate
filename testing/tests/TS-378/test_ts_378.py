from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.account_by_email_unsupported_cli_validator import (
    AccountByEmailUnsupportedCliValidator,
)
from testing.core.config.account_by_email_unsupported_cli_config import (
    AccountByEmailUnsupportedCliConfig,
)
from testing.tests.support.account_by_email_unsupported_cli_probe_factory import (
    create_account_by_email_unsupported_cli_probe,
)


class AccountByEmailUnsupportedCliContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = AccountByEmailUnsupportedCliConfig.from_defaults()
        self.validator = AccountByEmailUnsupportedCliValidator(
            probe=create_account_by_email_unsupported_cli_probe(self.repository_root)
        )

    def test_cli_reports_account_by_email_as_explicitly_unsupported(self) -> None:
        result = self.validator.validate(config=self.config)
        observation = result.account_by_email_unsupported
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else {}
        error = payload_dict.get("error")
        error_dict = error if isinstance(error, dict) else {}
        error_code = str(error_dict.get("code", ""))
        error_message = str(error_dict.get("message", ""))
        lowered_message = error_message.lower()

        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Precondition failed: TS-378 did not execute the ticket command.\n"
            f"Expected command: {' '.join(self.config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsInstance(
            payload,
            dict,
            "Step 2 failed: the CLI did not return a machine-readable JSON "
            "error envelope for the account-by-email request.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertEqual(
            observation.result.exit_code,
            self.config.expected_exit_code,
            "Step 2 failed: the account-by-email command did not return the "
            "documented unsupported exit code.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertIn(
            "ok",
            payload_dict,
            "Step 2 failed: the JSON envelope omitted the required `ok` field.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertIs(
            payload_dict.get("ok"),
            False,
            "Step 2 failed: the JSON envelope did not report `ok: false` for the "
            "unsupported account-by-email request.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertTrue(
            error_code.startswith(self.config.expected_error_code_prefix),
            "Step 2 failed: the JSON error code did not indicate an unsupported "
            "operation.\n"
            f"Expected prefix: {self.config.expected_error_code_prefix}\n"
            f"Observed error code: {error_code}\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("category"),
            self.config.expected_error_category,
            "Step 2 failed: the JSON error category did not match the documented "
            "unsupported account-by-email contract.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("exitCode"),
            self.config.expected_exit_code,
            "Step 2 failed: the JSON error object did not repeat the documented "
            "unsupported exit code.\n"
            f"Observed payload: {payload_dict}",
        )

        missing_message_fragments = [
            fragment
            for fragment in self.config.expected_message_fragments
            if fragment not in lowered_message
        ]
        self.assertFalse(
            missing_message_fragments,
            "Human-style verification failed: the terminal-visible error message "
            "did not explain that account-by-email is unsupported.\n"
            f"Missing message fragments: {missing_message_fragments}\n"
            f"Observed message: {error_message}\n"
            f"Observed payload: {payload_dict}",
        )

        for fragment in self.config.required_stdout_fragments:
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: stdout did not visibly show the "
                "unsupported JSON contract.\n"
                f"Missing stdout fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
