from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.project_quick_start_validator import (
    ProjectQuickStartValidator,
)
from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.tests.support.project_cli_probe_factory import create_project_cli_probe


class QuickStartCliValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ProjectCliValidationConfig.from_env()
        self.probe: ProjectCliProbe = create_project_cli_probe(self.repository_root)
        self.validator = ProjectQuickStartValidator(
            repository_root=self.repository_root,
            probe=self.probe,
        )

    def test_cli_validation_command_returns_expected_project_json_for_a_fork(self) -> None:
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
            result.quick_start_section,
            "Step 2 failed: `trackstate-setup/README.md` does not contain a "
            "`CLI quick start` section to validate.",
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
            (
                "gh",
                "api",
                f"repos/{result.target_repository}/contents/{self.config.project_path}",
                "-H",
                "Accept: application/vnd.github.raw+json",
            ),
            "Step 4 failed: the validation flow did not execute the expected "
            "GitHub CLI project fetch for the forked setup repository.",
        )
        self.assertTrue(
            result.project_fetch.succeeded,
            "Step 4 failed: the quick-start validation command did not complete "
            "successfully.\n"
            f"Command: {result.project_fetch.command_text}\n"
            f"Exit code: {result.project_fetch.exit_code}\n"
            f"stdout:\n{result.project_fetch.stdout}\n"
            f"stderr:\n{result.project_fetch.stderr}",
        )
        self.assertTrue(
            result.expected_project_fetch.succeeded,
            "Step 5 failed: the test could not read the same project file directly "
            "from the forked repository for independent comparison.\n"
            f"Command: {result.expected_project_fetch.command_text}\n"
            f"stderr:\n{result.expected_project_fetch.stderr}",
        )
        self.assertIsNotNone(
            result.actual_project,
            "Step 5 failed: the CLI command did not return parseable JSON output.",
        )
        self.assertTrue(
            result.project_fetch.stdout.lstrip().startswith("{"),
            "Step 5 failed: the CLI output did not render as a JSON object in the terminal.\n"
            f"Observed output:\n{result.project_fetch.stdout}",
        )
        self.assertDictEqual(
            result.actual_project or {},
            result.expected_project,
            "Expected the CLI validation command to return the same JSON payload "
            f"stored in {result.target_repository}/{self.config.project_path}, "
            "but the observable terminal output differed.",
        )

        for visible_snippet in self.config.visible_project_fields:
            self.assertIn(
                visible_snippet,
                result.project_fetch.stdout,
                "Human-style verification failed: the user-visible CLI output "
                f"did not show {visible_snippet!r}.\n"
                f"Observed output:\n{result.project_fetch.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
