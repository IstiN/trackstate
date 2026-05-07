from __future__ import annotations

import os
from pathlib import Path
import unittest

from testing.components.services.project_quick_start_validator import (
    ProjectQuickStartValidator,
)
from testing.frameworks.python.github_cli_project_framework import (
    GitHubCliProjectFramework,
)


class QuickStartCliValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.target_repository = os.environ.get(
            "TS74_SETUP_REPOSITORY",
            os.environ.get("TRACKSTATE_SETUP_REPOSITORY", "IstiN/trackstate-setup"),
        )
        self.project_path = os.environ.get("TS74_PROJECT_PATH", "DEMO/project.json")
        self.expected_project_file = Path(
            os.environ.get(
                "TS74_EXPECTED_PROJECT_FILE",
                "trackstate-setup/DEMO/project.json",
            )
        )
        self.validator = ProjectQuickStartValidator(
            repository_root=self.repository_root,
            probe=GitHubCliProjectFramework(self.repository_root),
        )

    def test_cli_validation_command_returns_expected_project_json(self) -> None:
        result = self.validator.validate(
            repository=self.target_repository,
            project_path=self.project_path,
            expected_project_file=self.expected_project_file,
        )

        self.assertTrue(
            result.auth_status.succeeded,
            "Step 1 failed: the CLI prerequisites were not satisfied because "
            "`gh auth status` did not confirm an authenticated GitHub CLI session.\n"
            f"Command: {result.auth_status.command_text}\n"
            f"Exit code: {result.auth_status.exit_code}\n"
            f"stdout:\n{result.auth_status.stdout}\n"
            f"stderr:\n{result.auth_status.stderr}",
        )

        self.assertEqual(
            result.project_fetch.command,
            (
                "gh",
                "api",
                f"repos/{self.target_repository}/contents/{self.project_path}",
                "-H",
                "Accept: application/vnd.github.raw+json",
            ),
            "Step 2 failed: the validation flow did not execute the expected "
            "GitHub CLI contents command for the configured setup repository.",
        )
        self.assertTrue(
            result.project_fetch.succeeded,
            "Step 2 failed: the quick-start validation command did not complete "
            "successfully.\n"
            f"Command: {result.project_fetch.command_text}\n"
            f"Exit code: {result.project_fetch.exit_code}\n"
            f"stdout:\n{result.project_fetch.stdout}\n"
            f"stderr:\n{result.project_fetch.stderr}",
        )
        self.assertIsNotNone(
            result.actual_project,
            "Step 3 failed: the CLI command did not return parseable JSON output.",
        )
        self.assertTrue(
            result.project_fetch.stdout.lstrip().startswith("{"),
            "Step 3 failed: the CLI output did not render as a JSON object in the terminal.\n"
            f"Observed output:\n{result.project_fetch.stdout}",
        )
        self.assertDictEqual(
            result.actual_project or {},
            result.expected_project,
            "Expected the CLI validation command to return the same JSON payload "
            f"stored in {self.expected_project_file} for {self.target_repository}, "
            "but the observable terminal output differed.",
        )

        for visible_snippet in (
            '"key": "DEMO"',
            '"name": "Demo TrackState Project"',
            '"defaultLocale": "en"',
            '"issueKeyPattern": "DEMO-{number}"',
            '"dataModel": "nested-tree"',
            '"configPath": "config"',
        ):
            self.assertIn(
                visible_snippet,
                result.project_fetch.stdout,
                "Human-style verification failed: the user-visible CLI output "
                f"did not show {visible_snippet!r}.\n"
                f"Observed output:\n{result.project_fetch.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
