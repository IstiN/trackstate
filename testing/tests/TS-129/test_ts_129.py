from __future__ import annotations

from dataclasses import replace
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


class ThemeTokenPolicySuccessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = replace(
            HardcodedHexLintConfig.from_env(),
            probe_relative_path=Path("lib/ts129_lint_probe.dart"),
        )
        self.probe = create_flutter_analyze_probe(
            self.repository_root,
            flutter_version=self.config.flutter_version,
        )
        self.validator = HardcodedHexLintValidator(
            self.repository_root,
            self.probe,
        )

    def test_theme_token_check_allows_compliant_ui_code(self) -> None:
        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.flutter_version.succeeded,
            "Precondition failed: the test could not start Flutter for TS-129.\n"
            f"Command: {result.flutter_version.command_text}\n"
            f"Exit code: {result.flutter_version.exit_code}\n"
            f"stdout:\n{result.flutter_version.stdout}\n"
            f"stderr:\n{result.flutter_version.stderr}",
        )
        self.assertTrue(
            result.pub_get.succeeded,
            "Precondition failed: `flutter pub get` did not complete in the "
            "temporary reproduction project, so TS-129 could not run the real "
            "theme-token policy command.\n"
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
            "Step 3 failed: the supported theme-token policy command rejected a "
            "compliant Flutter UI probe that uses the centralized TrackState "
            "theme token.\n"
            f"Probe file: {result.probe_path}\n"
            f"Command: {result.tokenized_analyze.command_text}\n"
            f"Exit code: {result.tokenized_analyze.exit_code}\n"
            f"Command output:\n{tokenized_output}",
        )
        self.assertIn(
            "No theme token policy violations found.",
            tokenized_output,
            "Human-style verification failed: the terminal output for the "
            "compliant probe did not clearly tell a user that the file passed "
            "the theme-token policy gate.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{tokenized_output}",
        )
        self.assertFalse(
            _has_terminal_diagnostic(tokenized_output),
            "Human-style verification failed: the compliant probe still "
            "printed an analyzer-style warning or error diagnostic.\n"
            f"Probe file: {result.probe_path}\n"
            f"Observed output:\n{tokenized_output}",
        )


def _has_terminal_diagnostic(output: str) -> bool:
    output_lower = output.lower()
    return any(
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


if __name__ == "__main__":
    unittest.main()
