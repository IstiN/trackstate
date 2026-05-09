from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.theme_token_policy_multi_target_validator import (
    ThemeTokenPolicyMultiTargetValidator,
)
from testing.core.config.theme_token_policy_multi_target_config import (
    ThemeTokenPolicyMultiTargetConfig,
)
from testing.core.models.theme_token_policy_multi_target_validation_result import (
    ThemeTokenPolicyMultiTargetValidationResult,
)
from testing.tests.support.flutter_analyze_probe_factory import (
    create_flutter_analyze_probe,
)


class ThemeTokenPolicyMixedTargetCheckTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ThemeTokenPolicyMultiTargetConfig.from_env(
            env_prefixes=("TS158", "TS132", "TRACKSTATE"),
        )
        self.file_target = self.repository_root / self.config.file_target_path
        self.directory_target = self.repository_root / self.config.directory_target_path
        self.probe = create_flutter_analyze_probe(
            self.repository_root,
            flutter_version=self.config.flutter_version,
            env_prefixes=("TS158", "TS132", "TS115", "TRACKSTATE"),
        )
        self.validator = ThemeTokenPolicyMultiTargetValidator(
            self.repository_root,
            self.probe,
        )

    def test_theme_token_check_passes_for_mixed_file_and_directory_targets(
        self,
    ) -> None:
        self.assertTrue(
            self.file_target.is_file(),
            "Precondition failed: TS-158 requires a compliant file target, but "
            f"{self.file_target} is not a file.",
        )
        self.assertTrue(
            self.directory_target.is_dir(),
            "Precondition failed: TS-158 requires a compliant directory target, "
            f"but {self.directory_target} is not a directory.",
        )
        directory_dart_files = sorted(self.directory_target.rglob("*.dart"))
        self.assertTrue(
            directory_dart_files,
            "Precondition failed: TS-158 requires the directory target to contain "
            "at least one Dart file so the recursive scan path is exercised.\n"
            f"Directory: {self.directory_target}",
        )

        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.flutter_version.succeeded,
            "Precondition failed: the test could not start Flutter for TS-158.\n"
            f"Command: {result.flutter_version.command_text}\n"
            f"Exit code: {result.flutter_version.exit_code}\n"
            f"stdout:\n{result.flutter_version.stdout}\n"
            f"stderr:\n{result.flutter_version.stderr}",
        )
        expected_command = (
            f"{result.theme_token_check.command[0]} run tool/check_theme_tokens.dart "
            f"{self.config.file_target_path} {self.config.directory_target_path}"
        )
        self.assertEqual(
            result.theme_token_check.command_text,
            expected_command,
            "Step 3 failed: the automation did not execute the exact mixed-target "
            "policy command required by TS-158.\n"
            f"Observed command: {result.theme_token_check.command_text}",
        )

        output = ThemeTokenPolicyMultiTargetValidationResult.combine_output(
            result.theme_token_check,
        )
        normalized_output = output.lower()
        has_diagnostic = any(
            marker in normalized_output for marker in self.config.diagnostic_markers
        )

        self.assertTrue(
            result.theme_token_check.succeeded,
            "Step 3 failed: running `dart run tool/check_theme_tokens.dart "
            "lib/main.dart tool/` did not complete successfully against the live "
            "production targets.\n"
            f"Command: {result.theme_token_check.command_text}\n"
            f"Exit code: {result.theme_token_check.exit_code}\n"
            f"stdout:\n{result.theme_token_check.stdout}\n"
            f"stderr:\n{result.theme_token_check.stderr}",
        )
        self.assertIn(
            self.config.success_message,
            output,
            "Human-style verification failed: the terminal output did not show the "
            "expected success message after checking the mixed file and directory "
            "targets.\n"
            f"Observed output:\n{output}",
        )
        self.assertFalse(
            has_diagnostic,
            "Human-style verification failed: the terminal output still displayed "
            "an analyzer-style diagnostic even though TS-158 expects zero warnings.\n"
            f"Observed output:\n{output}",
        )
        self.assertNotIn(
            "Theme token policy target does not exist",
            output,
            "Human-style verification failed: the mixed-target command still "
            "reported one of the explicit targets as missing.\n"
            f"Observed output:\n{output}",
        )


if __name__ == "__main__":
    unittest.main()
