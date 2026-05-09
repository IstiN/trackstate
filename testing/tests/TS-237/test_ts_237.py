from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import shlex
import unittest

from testing.components.services.project_quick_start_validator import (
    ProjectQuickStartValidator,
)
from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.tests.support.project_cli_probe_factory import create_project_cli_probe


class QuickStartCliMissingProjectFileTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        base_config = ProjectCliValidationConfig.from_env()
        self.config = replace(
            base_config,
            readme_repository_override=base_config.upstream_repository,
        )
        self.probe: ProjectCliProbe = create_project_cli_probe(self.repository_root)
        self.validator = ProjectQuickStartValidator(
            repository_root=self.repository_root,
            probe=self.probe,
        )

    def test_cli_validation_command_returns_404_when_project_file_is_missing(self) -> None:
        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.auth_status.succeeded,
            "Step 1 failed: the CLI prerequisites were not satisfied because "
            "`gh auth status` did not confirm an authenticated GitHub CLI session.\n"
            f"Command: {result.auth_status.command_text}\n"
            f"Exit code: {result.auth_status.exit_code}\n"
            f"stdout:\n{result.auth_status.stdout}\n"
            f"stderr:\n{result.auth_status.stderr}",
        )
        self.assertTrue(
            result.viewer_login.succeeded,
            "Step 1 failed: the test could not resolve the authenticated GitHub "
            "login needed to target a forked setup repository.\n"
            f"Command: {result.viewer_login.command_text}\n"
            f"Exit code: {result.viewer_login.exit_code}\n"
            f"stdout:\n{result.viewer_login.stdout}\n"
            f"stderr:\n{result.viewer_login.stderr}",
        )
        self.assertTrue(
            result.readme_fetch.succeeded,
            "Step 2 failed: the test could not read README.md from the deployed "
            "upstream setup repository, so it could not copy the documented "
            "quick-start validation command.\n"
            f"Command: {result.readme_fetch.command_text}\n"
            f"Exit code: {result.readme_fetch.exit_code}\n"
            f"stdout:\n{result.readme_fetch.stdout}\n"
            f"stderr:\n{result.readme_fetch.stderr}",
        )
        self.assertEqual(
            result.readme_repository,
            self.config.upstream_repository,
            "Step 2 failed: the validation did not copy the command from the "
            "deployed upstream setup README.",
        )
        self.assertTrue(
            result.quick_start_section,
            "Step 2 failed: the deployed README does not contain a `CLI quick start` "
            "section to validate.",
        )
        self.assertTrue(
            result.documented_command_template,
            "Step 2 failed: the deployed README does not include an executable "
            "GitHub CLI validation command in the `CLI quick start` section.\n"
            f"Observed section:\n{result.quick_start_section}",
        )
        self.assertEqual(
            result.documented_project_file,
            result.project_path,
            "Step 2 failed: the README quick-start section no longer points at the "
            "same project file used by this validation.\n"
            f"Documented project file: {result.documented_project_file}\n"
            f"Validated project file: {result.project_path}",
        )
        self.assertEqual(
            result.documented_source_repository,
            "IstiN/trackstate",
            "Step 2 failed: the README quick-start section no longer documents the "
            "expected default runtime repository.\n"
            f"Observed source repository: {result.documented_source_repository}",
        )
        for fragment in self.config.required_quick_start_fragments:
            self.assertIn(
                fragment,
                result.quick_start_section,
                "Step 2 failed: the CLI quick-start section no longer documents "
                f"{fragment!r}, so the validation path is incomplete.\n"
                f"Observed section:\n{result.quick_start_section}",
            )
        self.assertTrue(
            result.repository_info.succeeded,
            "Step 3 failed: the test could not inspect the configured setup "
            "repository before running the validation command.\n"
            f"Command: {result.repository_info.command_text}\n"
            f"Exit code: {result.repository_info.exit_code}\n"
            f"stdout:\n{result.repository_info.stdout}\n"
            f"stderr:\n{result.repository_info.stderr}",
        )
        self.assertNotEqual(
            result.target_repository,
            result.upstream_repository,
            "Step 3 failed: the validation targeted the upstream template "
            "repository instead of a fork, so it did not prove fork connectivity.",
        )
        self.assertTrue(
            result.repository_is_fork,
            "Step 3 failed: the configured setup repository is not marked as a fork.\n"
            f"Observed repository metadata:\n{result.repository_info.stdout}",
        )
        self.assertEqual(
            result.repository_parent,
            result.upstream_repository,
            "Step 3 failed: the configured setup repository is not a fork of the "
            "expected upstream template.\n"
            f"Observed repository metadata:\n{result.repository_info.stdout}",
        )
        self.assertEqual(
            result.project_fetch.command,
            tuple(shlex.split(result.documented_command or "")),
            "Step 4 failed: the automation did not execute the exact CLI command "
            "documented in the deployed README.\n"
            f"Documented command: {result.documented_command}\n"
            f"Executed command: {result.project_fetch.command_text}",
        )
        self.assertIn(
            result.project_path,
            result.project_fetch.command_text,
            "Step 4 failed: the documented command no longer targets the expected "
            "project file path.",
        )
        self.assertIn(
            result.target_repository,
            result.project_fetch.command_text,
            "Step 4 failed: the documented command no longer targets the fork "
            "repository under test.",
        )
        self.assertFalse(
            result.project_fetch.succeeded,
            "Step 4 failed: the README-documented quick-start validation command "
            "unexpectedly succeeded even though the test case precondition requires "
            "the project file to be missing in the fork.\n"
            f"Documented command: {result.documented_command}\n"
            f"stdout:\n{result.project_fetch.stdout}\n"
            f"stderr:\n{result.project_fetch.stderr}",
        )
        self.assertIn(
            "404",
            result.project_fetch.stderr,
            "Step 4 failed: the terminal-visible error did not include HTTP 404.\n"
            f"stderr:\n{result.project_fetch.stderr}",
        )
        self.assertIn(
            "Not Found",
            result.project_fetch.stderr,
            "Step 4 failed: the terminal-visible error did not surface `Not Found`.\n"
            f"stderr:\n{result.project_fetch.stderr}",
        )
        self.assertEqual(
            result.project_fetch.stdout.strip(),
            "",
            "Step 4 failed: the missing-file validation command still printed a "
            "JSON payload instead of surfacing only the 404 error.\n"
            f"stdout:\n{result.project_fetch.stdout}",
        )
        self.assertFalse(
            result.expected_project_fetch.succeeded,
            "Step 5 failed: the repository still exposed the project file over the "
            "raw content URL, so the missing-file precondition was not satisfied.\n"
            f"Command: {result.expected_project_fetch.command_text}\n"
            f"stdout:\n{result.expected_project_fetch.stdout}\n"
            f"stderr:\n{result.expected_project_fetch.stderr}",
        )
        self.assertIn(
            "404",
            result.expected_project_fetch.stderr,
            "Step 5 failed: the direct raw-file fetch did not confirm a 404 response.\n"
            f"stderr:\n{result.expected_project_fetch.stderr}",
        )
        self.assertIsNone(
            None
            if result.project_fetch.stdout.strip() == ""
            else result.project_fetch.stdout,
            "Human-style verification failed: the README command still produced "
            "parseable project JSON instead of a user-visible 404 error.\n"
            f"stdout:\n{result.project_fetch.stdout}",
        )
        self.assertEqual(
            result.project_fetch.stdout.strip(),
            "",
            "Human-style verification failed: the missing-file scenario still "
            "rendered visible project JSON instead of an empty stdout plus 404 "
            "stderr in the terminal.\n"
            f"Observed payload:\n{result.project_fetch.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
