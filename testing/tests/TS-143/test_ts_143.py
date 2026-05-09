from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.theme_token_policy_directory_validator import (
    ThemeTokenPolicyDirectoryValidator,
)
from testing.core.config.theme_token_policy_directory_config import (
    ThemeTokenPolicyDirectoryConfig,
)
from testing.core.models.theme_token_policy_directory_validation_result import (
    ThemeTokenPolicyDirectoryValidationResult,
)
from testing.tests.support.flutter_analyze_probe_factory import (
    create_flutter_analyze_probe,
)


class ThemeTokenPolicyNormalizedDirectoryCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ThemeTokenPolicyDirectoryConfig.from_env(
            env_prefixes=("TS143", "TS132", "TRACKSTATE"),
            default_target_path="lib",
        )
        self.probe = create_flutter_analyze_probe(
            self.repository_root,
            flutter_version=self.config.flutter_version,
            env_prefixes=("TS143", "TS132", "TS115", "TRACKSTATE"),
        )
        self.validator = ThemeTokenPolicyDirectoryValidator(
            self.repository_root,
            self.probe,
        )

    def test_theme_token_check_passes_for_normalized_production_ui_directory(
        self,
    ) -> None:
        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.flutter_version.succeeded,
            "Precondition failed: the test could not start Flutter for TS-143.\n"
            f"Command: {result.flutter_version.command_text}\n"
            f"Exit code: {result.flutter_version.exit_code}\n"
            f"stdout:\n{result.flutter_version.stdout}\n"
            f"stderr:\n{result.flutter_version.stderr}",
        )
        self.assertEqual(
            result.theme_token_check.command_text,
            f"{result.theme_token_check.command[0]} run tool/check_theme_tokens.dart "
            f"{self.config.target_path}",
            "Step 2 failed: the automation did not execute the exact command "
            "required by TS-143.\n"
            f"Observed command: {result.theme_token_check.command_text}",
        )

        output = ThemeTokenPolicyDirectoryValidationResult.combine_output(
            result.theme_token_check,
        )
        normalized_output = output.lower()
        has_diagnostic = any(
            marker in normalized_output for marker in self.config.diagnostic_markers
        )

        self.assertTrue(
            result.theme_token_check.succeeded,
            "Step 2 failed: running `dart run tool/check_theme_tokens.dart lib` "
            "did not complete successfully against the live production UI directory.\n"
            f"Command: {result.theme_token_check.command_text}\n"
            f"Exit code: {result.theme_token_check.exit_code}\n"
            f"stdout:\n{result.theme_token_check.stdout}\n"
            f"stderr:\n{result.theme_token_check.stderr}",
        )
        self.assertIn(
            self.config.success_message,
            output,
            "Human-style verification failed: the terminal output did not show the "
            "expected success message after checking the normalized production "
            "UI directory.\n"
            f"Observed output:\n{output}",
        )
        self.assertFalse(
            has_diagnostic,
            "Human-style verification failed: the terminal output still displayed "
            "an analyzer-style diagnostic even though TS-143 expects zero warnings.\n"
            f"Observed output:\n{output}",
        )
        self.assertNotIn(
            "Theme token policy target does not exist",
            output,
            "Human-style verification failed: the normalized `lib` directory was "
            "still rejected as a missing target.\n"
            f"Observed output:\n{output}",
        )


if __name__ == "__main__":
    unittest.main()
