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
        payload_dict = payload if isinstance(payload, dict) else None
        error_dict = (
            payload_dict.get("error")
            if isinstance(payload_dict, dict) and isinstance(payload_dict.get("error"), dict)
            else None
        )
        error_code = str(error_dict.get("code", "")) if error_dict else ""
        error_message = str(error_dict.get("message", "")) if error_dict else ""
        lowered_message = error_message.lower()
        failures: list[str] = []

        if observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-378 did not execute the ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )

        if payload_dict is None:
            failures.append(
                "Step 2 failed: the CLI did not return a machine-readable JSON "
                "error envelope for the account-by-email request.\n"
                f"Requested command: {observation.requested_command_text}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}\n"
                f"Exit code: {observation.result.exit_code}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )
        else:
            if observation.result.exit_code != self.config.expected_exit_code:
                failures.append(
                    "Step 2 failed: the account-by-email command did not return the "
                    "documented unsupported exit code.\n"
                    f"Requested command: {observation.requested_command_text}\n"
                    f"Executed command: {observation.executed_command_text}\n"
                    f"Fallback reason: {observation.fallback_reason}\n"
                    f"Expected exit code: {self.config.expected_exit_code}\n"
                    f"Observed exit code: {observation.result.exit_code}\n"
                    f"Observed payload: {payload_dict}\n"
                    f"stdout:\n{observation.result.stdout}\n"
                    f"stderr:\n{observation.result.stderr}"
                )

            if "ok" not in payload_dict:
                failures.append(
                    "Step 2 failed: the JSON envelope omitted the required `ok` "
                    f"field.\nObserved payload: {payload_dict}"
                )
            elif payload_dict.get("ok") is not False:
                failures.append(
                    "Step 2 failed: the JSON envelope did not report `ok: false` "
                    "for the unsupported account-by-email request.\n"
                    f"Observed payload: {payload_dict}"
                )

            if error_dict is None:
                failures.append(
                    "Step 2 failed: the JSON envelope omitted the required error "
                    f"object.\nObserved payload: {payload_dict}"
                )
            else:
                if not error_code.startswith(self.config.expected_error_code_prefix):
                    failures.append(
                        "Step 2 failed: the JSON error code did not indicate an "
                        "unsupported operation.\n"
                        f"Expected prefix: {self.config.expected_error_code_prefix}\n"
                        f"Observed error code: {error_code}\n"
                        f"Observed payload: {payload_dict}"
                    )

                if error_dict.get("category") != self.config.expected_error_category:
                    failures.append(
                        "Step 2 failed: the JSON error category did not match the "
                        "documented unsupported account-by-email contract.\n"
                        f"Expected category: {self.config.expected_error_category}\n"
                        f"Observed category: {error_dict.get('category')}\n"
                        f"Observed payload: {payload_dict}"
                    )

                if error_dict.get("exitCode") != self.config.expected_exit_code:
                    failures.append(
                        "Step 2 failed: the JSON error object did not repeat the "
                        "documented unsupported exit code.\n"
                        f"Expected error exitCode: {self.config.expected_exit_code}\n"
                        f"Observed error exitCode: {error_dict.get('exitCode')}\n"
                        f"Observed payload: {payload_dict}"
                    )

                missing_message_fragments = [
                    fragment
                    for fragment in self.config.expected_message_fragments
                    if fragment not in lowered_message
                ]
                if missing_message_fragments:
                    failures.append(
                        "Human-style verification failed: the terminal-visible error "
                        "message did not explain that account-by-email is "
                        "unsupported.\n"
                        f"Missing message fragments: {missing_message_fragments}\n"
                        f"Observed message: {error_message}\n"
                        f"Observed payload: {payload_dict}"
                    )

            for fragment in self.config.required_stdout_fragments:
                if fragment not in observation.result.stdout:
                    failures.append(
                        "Human-style verification failed: stdout did not visibly "
                        "show the unsupported JSON contract.\n"
                        f"Missing stdout fragment: {fragment}\n"
                        f"Observed stdout:\n{observation.result.stdout}"
                    )

        self.assertFalse(failures, "\n\n".join(failures))


if __name__ == "__main__":
    unittest.main()
