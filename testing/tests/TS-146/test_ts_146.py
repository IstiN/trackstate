from __future__ import annotations

from dataclasses import replace
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


class ThemeTokenPolicyMissingTargetCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = replace(
            ThemeTokenPolicyDirectoryConfig.from_env(),
            target_path="./invalid_path_xyz",
        )
        self.expected_missing_target = self.repository_root / "invalid_path_xyz"
        self.expected_diagnostic = (
            "Theme token policy target does not exist: "
            f"{self.config.target_path}"
        )
        self.probe = create_flutter_analyze_probe(
            self.repository_root,
            flutter_version=self.config.flutter_version,
        )
        self.validator = ThemeTokenPolicyDirectoryValidator(
            self.repository_root,
            self.probe,
        )

    def test_theme_token_check_reports_missing_target_directory(self) -> None:
        self.assertFalse(
            self.expected_missing_target.exists(),
            "Precondition failed: TS-146 requires `./invalid_path_xyz` to be "
            "missing before the command runs, but the repository now contains "
            f"{self.expected_missing_target}. Remove or rename that path before "
            "using this automation result.",
        )

        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.flutter_version.succeeded,
            "Precondition failed: the test could not start Flutter for TS-146.\n"
            f"Command: {result.flutter_version.command_text}\n"
            f"Exit code: {result.flutter_version.exit_code}\n"
            f"stdout:\n{result.flutter_version.stdout}\n"
            f"stderr:\n{result.flutter_version.stderr}",
        )
        self.assertEqual(
            result.theme_token_check.command_text,
            f"{result.theme_token_check.command[0]} run tool/check_theme_tokens.dart "
            f"{self.config.target_path}",
            "Step 2 failed: the automation did not execute the exact missing-path "
            "policy command required by TS-146.\n"
            f"Observed command: {result.theme_token_check.command_text}",
        )

        output = ThemeTokenPolicyDirectoryValidationResult.combine_output(
            result.theme_token_check,
        )

        self.assertEqual(
            result.theme_token_check.exit_code,
            2,
            "Step 2 failed: the missing-target command did not exit with status 2.\n"
            f"Command: {result.theme_token_check.command_text}\n"
            f"Observed exit code: {result.theme_token_check.exit_code}\n"
            f"stdout:\n{result.theme_token_check.stdout}\n"
            f"stderr:\n{result.theme_token_check.stderr}",
        )
        self.assertIn(
            self.expected_diagnostic,
            output,
            "Human-style verification failed: the terminal output did not show "
            "the expected missing-target diagnostic.\n"
            f"Observed output:\n{output}",
        )
        self.assertNotIn(
            self.config.success_message,
            output,
            "Human-style verification failed: the missing-target command still "
            "printed the success banner.\n"
            f"Observed output:\n{output}",
        )


if __name__ == "__main__":
    unittest.main()
