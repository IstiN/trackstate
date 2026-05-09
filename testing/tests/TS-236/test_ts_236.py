from __future__ import annotations

import re
import shlex
from pathlib import Path
import unittest

from testing.components.services.project_quick_start_auth_failure_validator import (
    ProjectQuickStartAuthFailureValidator,
)
from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.tests.support.project_cli_probe_factory import create_project_cli_probe


class QuickStartInvalidCredentialsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ProjectCliValidationConfig.from_env()
        self.readme_path = self.repository_root / self.config.readme_path
        self.probe = create_project_cli_probe(self.repository_root)
        self.validator = ProjectQuickStartAuthFailureValidator(
            repository_root=self.repository_root,
            probe=self.probe,
        )

    def test_readme_validation_command_reports_authentication_error_for_invalid_token(
        self,
    ) -> None:
        self.assertTrue(
            self.readme_path.is_file(),
            f"Precondition failed: expected README at {self.readme_path}.",
        )

        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.quick_start_section,
            "Step 1 failed: trackstate-setup/README.md does not contain the "
            "`CLI quick start` section needed for this validation.\n"
            f"README path: {self.readme_path}",
        )
        self.assertEqual(
            result.documented_command_template,
            'gh api repos/<fork>/contents/<project-path>?ref=<default-branch> -H "Accept: application/vnd.github.raw+json"',
            "Step 1 failed: the README no longer documents the executable raw "
            "`gh api` validation command required by TS-236.\n"
            f"Observed section:\n{result.quick_start_section}",
        )
        self.assertIsNotNone(
            result.documented_command,
            "Step 1 failed: the README quick-start command could not be expanded "
            "into an executable terminal command.",
        )
        self.assertEqual(
            tuple(result.invalid_command_result.command),
            tuple(shlex.split(result.documented_command or "")),
            "Step 2 failed: the automation did not execute the exact command "
            "copied from the README quick start.\n"
            f"Expected command: {result.documented_command}\n"
            f"Executed command: {result.invalid_command_result.command_text}",
        )
        self.assertFalse(
            result.invalid_command_result.succeeded,
            "Step 2 failed: the README validation command unexpectedly succeeded "
            "even though it was executed with an invalid GitHub token.\n"
            f"Command: {result.invalid_command_result.command_text}\n"
            f"stdout:\n{result.invalid_command_result.stdout}\n"
            f"stderr:\n{result.invalid_command_result.stderr}",
        )

        observed_output = result.invalid_command_output
        self.assertRegex(
            observed_output,
            re.compile(
                r"(bad credentials|http 401|status\"\s*:\s*\"401\"|authentication failed)",
                re.IGNORECASE,
            ),
            "Step 2 failed: the command did not report a user-visible "
            "authentication error. The terminal output should explain that the "
            "credentials are invalid instead of looking like a tool failure.\n"
            f"Command: {result.invalid_command_result.command_text}\n"
            f"Observed output:\n{observed_output}",
        )
        self.assertNotRegex(
            observed_output,
            re.compile(r"(could not parse|shell metacharacters|README quick-start command was empty)", re.IGNORECASE),
            "Human-style verification failed: the terminal output indicates a "
            "test or README command-shape problem instead of a credential problem.\n"
            f"Observed output:\n{observed_output}",
        )
        self.assertRegex(
            result.invalid_command_result.command_text,
            re.compile(r"^gh api repos/.+/contents/.+\?ref=.+"),
            "Human-style verification failed: the executed terminal command did "
            "not look like the README-documented `gh api repos/.../contents/...` "
            "validation flow.\n"
            f"Executed command: {result.invalid_command_result.command_text}",
        )


if __name__ == "__main__":
    unittest.main()
