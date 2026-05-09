from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.hardcoded_hex_lint_validator import (
    HardcodedHexLintValidator,
)
from testing.core.config.hardcoded_hex_lint_config import HardcodedHexLintConfig
from testing.core.models.hardcoded_hex_lint_validation_result import (
    HardcodedHexLintValidationResult,
)
from testing.tests.support.flutter_analyze_probe_factory import (
    create_flutter_analyze_probe,
)


class HardcodedHexLintRuleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = HardcodedHexLintConfig.from_env()
        self.probe = create_flutter_analyze_probe(
            self.repository_root,
            flutter_version=self.config.flutter_version,
        )
        self.validator = HardcodedHexLintValidator(
            self.repository_root,
            self.probe,
        )

    def test_flutter_analyze_blocks_hardcoded_hex_colors_in_ui_widgets(self) -> None:
        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.flutter_version.succeeded,
            "Precondition failed: the test could not start Flutter for TS-115.\n"
            f"Command: {result.flutter_version.command_text}\n"
            f"Exit code: {result.flutter_version.exit_code}\n"
            f"stdout:\n{result.flutter_version.stdout}\n"
            f"stderr:\n{result.flutter_version.stderr}",
        )
        self.assertTrue(
            result.pub_get.succeeded,
            "Precondition failed: `flutter pub get` did not complete in the "
            "temporary reproduction project, so TS-115 could not run the real "
            "analysis flow.\n"
            f"Command: {result.pub_get.command_text}\n"
            f"Exit code: {result.pub_get.exit_code}\n"
            f"stdout:\n{result.pub_get.stdout}\n"
            f"stderr:\n{result.pub_get.stderr}",
        )

        tokenized_output = HardcodedHexLintValidationResult.combine_output(
            result.tokenized_analyze,
        )
        self.assertTrue(
            result.tokenized_analyze.succeeded,
            "Step 1 failed: the theme-tokenized probe widget did not analyze "
            "cleanly through the theme-token policy gate before the "
            "hardcoded-hex mutation.\n"
            f"Probe file: {result.probe_path}\n"
            f"Command: {result.tokenized_analyze.command_text}\n"
            f"Exit code: {result.tokenized_analyze.exit_code}\n"
            f"Analyzer output:\n{tokenized_output}",
        )
        self.assertIn(
            "No theme token policy violations found.",
            tokenized_output,
            "Human-style verification failed for Step 1: the terminal output for "
            "the theme-tokenized probe did not show a clean policy result.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{tokenized_output}",
        )

        hardcoded_output = HardcodedHexLintValidationResult.combine_output(
            result.hardcoded_analyze,
        )
        output_lower = hardcoded_output.lower()
        has_terminal_diagnostic = any(
            marker in output_lower
            for marker in (
                "error •",
                "warning •",
                "info •",
                " error - ",
                " warning - ",
                " info - ",
            )
        )
        mentions_probe_file = self.config.probe_relative_path.name in hardcoded_output
        mentions_rule_intent = any(
            fragment in output_lower
            for fragment in self.config.required_diagnostic_fragments
        )
        mentions_literal = self.config.hardcoded_color_expression in hardcoded_output

        self.assertTrue(
            result.hardcoded_analyze.exit_code != 0 or has_terminal_diagnostic,
            "Step 3 failed: the theme-token policy gate treated the hardcoded "
            "hex probe as acceptable instead of surfacing a lint violation.\n"
            f"Probe file: {result.probe_path}\n"
            f"Command: {result.hardcoded_analyze.command_text}\n"
            f"Exit code: {result.hardcoded_analyze.exit_code}\n"
            f"Analyzer output:\n{hardcoded_output}",
        )
        self.assertNotIn(
            "No issues found!",
            hardcoded_output,
            "Step 3 failed: the terminal still reported `No issues found!` "
            "after the probe widget was changed to use a hardcoded hex color.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{hardcoded_output}",
        )
        self.assertTrue(
            mentions_probe_file and (mentions_rule_intent or mentions_literal),
            "Human-style verification failed for Step 3: the analyzer output did "
            "not clearly point a user to the hardcoded-hex violation in the probe "
            "widget.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{hardcoded_output}",
        )


if __name__ == "__main__":
    unittest.main()
