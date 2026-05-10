from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.local_target_validation_cli_validator import (
    LocalTargetValidationCliValidator,
)
from testing.core.config.local_target_validation_cli_config import (
    LocalTargetValidationCliConfig,
)
from testing.tests.support.local_target_validation_cli_probe_factory import (
    create_local_target_validation_cli_probe,
)


class LocalTargetValidationCliContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = LocalTargetValidationCliConfig.from_env()
        self.validator = LocalTargetValidationCliValidator(
            probe=create_local_target_validation_cli_probe(self.repository_root)
        )

    def test_invalid_local_target_reports_repository_open_failed(self) -> None:
        observation = self.validator.validate(config=self.config).observation
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else {}
        target = payload_dict.get("target")
        target_dict = target if isinstance(target, dict) else {}
        error = payload_dict.get("error")
        error_dict = error if isinstance(error, dict) else {}
        details = error_dict.get("details")
        details_dict = details if isinstance(details, dict) else {}

        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Precondition failed: TS-270 did not target the local session command "
            "described by the ticket.\n"
            f"Expected command: {' '.join(self.config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsInstance(
            payload,
            dict,
            "Step 2 failed: the CLI did not return a machine-readable JSON error "
            "envelope when the working directory was not a Git repository.\n"
            f"Working directory: {observation.working_directory}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertEqual(
            observation.result.exit_code,
            self.config.expected_exit_code,
            "Step 2 failed: the local target command did not return the documented "
            "repository-open failure exit code.\n"
            f"Working directory: {observation.working_directory}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertIs(
            payload_dict.get("ok"),
            False,
            "Step 2 failed: the JSON envelope did not report `ok: false` for the "
            "invalid local repository scenario.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            payload_dict.get("provider"),
            self.config.expected_provider,
            "Step 2 failed: the JSON envelope did not identify the Local Git "
            "provider.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            target_dict.get("type"),
            self.config.expected_target_type,
            "Step 2 failed: the JSON envelope did not identify the local target "
            "type.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            target_dict.get("value"),
            observation.working_directory,
            "Step 2 failed: the JSON envelope did not report the non-repository "
            "working directory the CLI attempted to open.\n"
            f"Expected target value: {observation.working_directory}\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("code"),
            self.config.expected_error_code,
            "Step 2 failed: the JSON error code did not match the documented local "
            "repository failure contract.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("category"),
            self.config.expected_error_category,
            "Step 2 failed: the JSON error category did not match the documented "
            "repository failure contract.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("exitCode"),
            self.config.expected_exit_code,
            "Step 2 failed: the JSON error object did not repeat the documented exit "
            "code.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("message"),
            (
                "Local repository session could not be opened for "
                f"\"{observation.working_directory}\"."
            ),
            "Step 2 failed: the visible repository-open failure message changed from "
            "the documented contract.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            details_dict.get("path"),
            observation.working_directory,
            "Step 2 failed: the JSON error details did not repeat the non-repository "
            "path the CLI tried to open.\n"
            f"Observed payload: {payload_dict}",
        )
        reason_text = str(details_dict.get("reason", ""))
        for fragment in self.config.expected_reason_fragments:
            self.assertIn(
                fragment,
                reason_text,
                "Step 2 failed: the repository-open failure details no longer make it "
                "clear that the current directory is not a Git repository.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed payload: {payload_dict}",
            )

        for fragment in self.config.required_stdout_fragments:
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the terminal output did not visibly "
                "show the documented repository-open JSON contract.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )
        self.assertIn(
            observation.working_directory,
            observation.result.stdout,
            "Human-style verification failed: the terminal output did not visibly "
            "show the non-repository path the user tried to open.\n"
            f"Observed stdout:\n{observation.result.stdout}",
        )
        self.assertIn(
            "fatal: not a git repository",
            observation.output,
            "Human-style verification failed: the terminal-visible error details did "
            "not make it clear that the current directory was not a Git repository.\n"
            f"Observed output:\n{observation.output}",
        )


if __name__ == "__main__":
    unittest.main()
