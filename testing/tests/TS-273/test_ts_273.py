from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.unsupported_provider_cli_validator import (
    UnsupportedProviderCliValidator,
)
from testing.core.config.unsupported_provider_cli_config import (
    UnsupportedProviderCliConfig,
)
from testing.tests.support.unsupported_provider_cli_probe_factory import (
    create_unsupported_provider_cli_probe,
)


class UnsupportedProviderCliContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = UnsupportedProviderCliConfig.from_env()
        self.validator = UnsupportedProviderCliValidator(
            repository_root=self.repository_root,
            probe=create_unsupported_provider_cli_probe(self.repository_root),
        )

    def test_live_cli_maps_unsupported_provider_to_documented_error_contract(
        self,
    ) -> None:
        result = self.validator.validate(config=self.config)
        observation = result.unsupported_provider
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else {}
        error = payload_dict.get("error")
        error_dict = error if isinstance(error, dict) else {}
        details = error_dict.get("details")
        details_dict = details if isinstance(details, dict) else {}

        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Precondition failed: TS-273 did not target the unsupported-provider "
            "session command described by the ticket.\n"
            f"Expected command: {' '.join(self.config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsInstance(
            payload,
            dict,
            "Step 2 failed: the CLI did not return a machine-readable JSON "
            "envelope for the unsupported-provider scenario.\n"
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
            "Step 2 failed: the unsupported-provider command did not return the "
            "documented exit code.\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertFalse(
            payload_dict.get("ok"),
            "Step 2 failed: the JSON envelope did not report `ok: false` for the "
            "unsupported-provider scenario.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("code"),
            self.config.expected_error_code,
            "Step 2 failed: the JSON error code did not match the documented "
            "unsupported-provider contract.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("category"),
            self.config.expected_error_category,
            "Step 2 failed: the JSON error category did not match the documented "
            "unsupported-provider contract.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            error_dict.get("exitCode"),
            self.config.expected_exit_code,
            "Step 2 failed: the JSON error object did not repeat the documented "
            "exit code.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertEqual(
            details_dict.get("provider"),
            self.config.expected_provider,
            "Human-style verification failed: the error details did not identify "
            "the unsupported provider the user requested.\n"
            f"Observed payload: {payload_dict}",
        )
        self.assertIn(
            self.config.expected_provider,
            str(error_dict.get("message", "")),
            "Human-style verification failed: the terminal-visible error message "
            "did not mention the unsupported provider value the user entered.\n"
            f"Observed payload: {payload_dict}",
        )

        for fragment in self.config.required_stdout_fragments:
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the terminal output did not "
                "visibly show the documented JSON error contract.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
