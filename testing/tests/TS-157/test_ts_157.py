from __future__ import annotations

from pathlib import Path
import re
import unittest

from testing.components.services.theme_token_nested_directory_violation_validator import (
    ThemeTokenNestedDirectoryViolationValidator,
)
from testing.core.config.theme_token_nested_directory_violation_config import (
    ThemeTokenNestedDirectoryViolationConfig,
)
from testing.core.models.theme_token_nested_directory_violation_result import (
    ThemeTokenNestedDirectoryViolationResult,
)
from testing.tests.support.flutter_analyze_probe_factory import (
    create_flutter_analyze_probe,
)


class ThemeTokenNestedDirectoryViolationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ThemeTokenNestedDirectoryViolationConfig.from_env()
        self.probe = create_flutter_analyze_probe(
            self.repository_root,
            flutter_version=self.config.flutter_version,
            env_prefixes=("TS157", "TS132", "TS115", "TRACKSTATE"),
        )
        self.validator = ThemeTokenNestedDirectoryViolationValidator(
            self.repository_root,
            self.probe,
        )

    def test_theme_token_check_detects_nested_directory_violations_recursively(
        self,
    ) -> None:
        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.flutter_version.succeeded,
            "Precondition failed: the test could not start Flutter for TS-157.\n"
            f"Command: {result.flutter_version.command_text}\n"
            f"Exit code: {result.flutter_version.exit_code}\n"
            f"stdout:\n{result.flutter_version.stdout}\n"
            f"stderr:\n{result.flutter_version.stderr}",
        )
        self.assertTrue(
            result.pub_get.succeeded,
            "Precondition failed: `flutter pub get` did not complete in the "
            "temporary reproduction project, so TS-157 could not run the real "
            "directory-scan workflow.\n"
            f"Command: {result.pub_get.command_text}\n"
            f"Exit code: {result.pub_get.exit_code}\n"
            f"stdout:\n{result.pub_get.stdout}\n"
            f"stderr:\n{result.pub_get.stderr}",
        )

        expected_command = (
            f"{result.baseline_check.command[0]} run tool/check_theme_tokens.dart "
            f"{self.config.target_path}"
        )
        self.assertEqual(
            result.baseline_check.command_text,
            expected_command,
            "Step 4 failed: the clean precondition run did not execute the "
            "ticketed parent-directory command.\n"
            f"Observed command: {result.baseline_check.command_text}",
        )
        self.assertEqual(
            result.nested_check.command_text,
            expected_command,
            "Step 4 failed: the nested-file verification did not execute the "
            "ticketed parent-directory command.\n"
            f"Observed command: {result.nested_check.command_text}",
        )

        baseline_output = ThemeTokenNestedDirectoryViolationResult.combine_output(
            result.baseline_check,
        )
        self.assertTrue(
            result.baseline_check.succeeded,
            "Precondition failed: the copied repository already failed the live "
            "theme-token directory scan before the nested violation was added.\n"
            f"Command: {result.baseline_check.command_text}\n"
            f"Exit code: {result.baseline_check.exit_code}\n"
            f"stdout:\n{result.baseline_check.stdout}\n"
            f"stderr:\n{result.baseline_check.stderr}",
        )
        self.assertIn(
            self.config.success_message,
            baseline_output,
            "Precondition failed: the clean directory scan did not show the "
            "expected success banner before the nested file was created.\n"
            f"Observed output:\n{baseline_output}",
        )

        nested_output = ThemeTokenNestedDirectoryViolationResult.combine_output(
            result.nested_check,
        )
        output_lower = nested_output.lower()
        has_warning_diagnostic = _contains_warning_diagnostic(nested_output)
        mentions_probe_file = self.config.probe_relative_path.as_posix() in nested_output
        mentions_numeric_position = _mentions_numeric_position(
            self.config.probe_relative_path.as_posix(),
            nested_output,
        )
        mentions_violation_literal = self.config.violation_literal in nested_output
        mentions_rule_intent = any(
            fragment in output_lower
            for fragment in self.config.required_diagnostic_fragments
        )

        self.assertNotEqual(
            result.nested_check.exit_code,
            0,
            "Step 4 failed: running `dart run tool/check_theme_tokens.dart lib/` "
            "still exited successfully after the nested hardcoded color file was "
            "added.\n"
            f"Probe file: {result.probe_path}\n"
            f"Command: {result.nested_check.command_text}\n"
            f"Observed output:\n{nested_output}",
        )
        self.assertTrue(
            has_warning_diagnostic,
            "Expected result failed: the recursive directory scan did not emit an "
            "analyzer-style diagnostic for the nested violation.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{nested_output}",
        )
        self.assertTrue(
            mentions_probe_file and mentions_numeric_position,
            "Human-style verification failed: the terminal diagnostic did not "
            "show the nested file path together with a numeric line/column.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{nested_output}",
        )
        self.assertTrue(
            mentions_violation_literal or mentions_rule_intent,
            "Human-style verification failed: the recursive violation output did "
            "not make it clear to a terminal user what policy problem was found "
            "inside the nested file.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{nested_output}",
        )
        self.assertNotIn(
            self.config.success_message,
            nested_output,
            "Expected result failed: the recursive violation run still printed the "
            "clean success banner.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{nested_output}",
        )


def _contains_warning_diagnostic(output: str) -> bool:
    return (
        re.search(r"(^|\n)\s*(?:warning|error)\s*(?:•|-)\s", output.lower())
        is not None
    )


def _mentions_numeric_position(path: str, output: str) -> bool:
    return re.search(rf"{re.escape(path)}:\d+:\d+\b", output) is not None


if __name__ == "__main__":
    unittest.main()
