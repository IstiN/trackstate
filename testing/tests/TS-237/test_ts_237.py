from __future__ import annotations

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
        self.config = ProjectCliValidationConfig.from_env()
        self.probe: ProjectCliProbe = create_project_cli_probe(self.repository_root)
        self.validator = ProjectQuickStartValidator(
            repository_root=self.repository_root,
            probe=self.probe,
        )

    def test_cli_validation_command_returns_404_when_project_file_is_missing(self) -> None:
        auth_status = self.probe.auth_status()
        viewer_login = self.probe.viewer_login()
        target_repository = self.validator._resolve_target_repository(
            self.config,
            viewer_login,
        )
        target_repository_info = self.probe.repository_metadata(target_repository)
        target_default_branch = self.validator._repository_default_branch(
            target_repository_info,
        )
        upstream_repository_info = self.probe.repository_metadata(
            self.config.upstream_repository,
        )
        upstream_default_branch = self.validator._repository_default_branch(
            upstream_repository_info,
        )
        readme_fetch = self.probe.get_contents(
            self.config.upstream_repository,
            upstream_default_branch,
            self.config.readme_path.name,
        )
        readme_text = self.validator._decode_repository_text(readme_fetch)
        quick_start_section = self.validator._read_quick_start_section(readme_text)
        documented_source_repository = self.validator._documented_source_repository(
            quick_start_section,
        )
        documented_project_file = self.validator._documented_project_file(
            quick_start_section,
        )
        project_path = documented_project_file or self.config.project_path
        documented_command_template = self.validator._documented_validation_command(
            quick_start_section,
        )
        documented_command = self.validator._expand_documented_command(
            documented_command_template,
            target_repository=target_repository,
            default_branch=target_default_branch,
            project_path=project_path,
        )
        project_fetch = self.probe.run_documented_command(documented_command or "")
        expected_project_fetch = self.probe.get_raw_file(
            target_repository,
            target_default_branch,
            project_path,
        )

        self.assertTrue(
            auth_status.succeeded,
            "Step 1 failed: the CLI prerequisites were not satisfied because "
            "`gh auth status` did not confirm an authenticated GitHub CLI session.\n"
            f"Command: {auth_status.command_text}\n"
            f"Exit code: {auth_status.exit_code}\n"
            f"stdout:\n{auth_status.stdout}\n"
            f"stderr:\n{auth_status.stderr}",
        )
        self.assertTrue(
            viewer_login.succeeded,
            "Step 1 failed: the test could not resolve the authenticated GitHub "
            "login needed to target a forked setup repository.\n"
            f"Command: {viewer_login.command_text}\n"
            f"Exit code: {viewer_login.exit_code}\n"
            f"stdout:\n{viewer_login.stdout}\n"
            f"stderr:\n{viewer_login.stderr}",
        )
        self.assertTrue(
            readme_fetch.succeeded,
            "Step 2 failed: the test could not read README.md from the deployed "
            "upstream setup repository, so it could not copy the documented "
            "quick-start validation command.\n"
            f"Command: {readme_fetch.command_text}\n"
            f"Exit code: {readme_fetch.exit_code}\n"
            f"stdout:\n{readme_fetch.stdout}\n"
            f"stderr:\n{readme_fetch.stderr}",
        )
        self.assertTrue(
            quick_start_section,
            "Step 2 failed: the deployed README does not contain a `CLI quick start` "
            "section to validate.",
        )
        self.assertTrue(
            documented_command_template,
            "Step 2 failed: the deployed README does not include an executable "
            "GitHub CLI validation command in the `CLI quick start` section.\n"
            f"Observed section:\n{quick_start_section}",
        )
        self.assertEqual(
            documented_project_file,
            project_path,
            "Step 2 failed: the README quick-start section no longer points at the "
            "same project file used by this validation.\n"
            f"Documented project file: {documented_project_file}\n"
            f"Validated project file: {project_path}",
        )
        self.assertEqual(
            documented_source_repository,
            "IstiN/trackstate",
            "Step 2 failed: the README quick-start section no longer documents the "
            "expected default runtime repository.\n"
            f"Observed source repository: {documented_source_repository}",
        )
        for fragment in self.config.required_quick_start_fragments:
            self.assertIn(
                fragment,
                quick_start_section,
                "Step 2 failed: the CLI quick-start section no longer documents "
                f"{fragment!r}, so the validation path is incomplete.\n"
                f"Observed section:\n{quick_start_section}",
            )
        self.assertTrue(
            target_repository_info.succeeded,
            "Step 3 failed: the test could not inspect the configured setup "
            "repository before running the validation command.\n"
            f"Command: {target_repository_info.command_text}\n"
            f"Exit code: {target_repository_info.exit_code}\n"
            f"stdout:\n{target_repository_info.stdout}\n"
            f"stderr:\n{target_repository_info.stderr}",
        )
        self.assertNotEqual(
            target_repository,
            self.config.upstream_repository,
            "Step 3 failed: the validation targeted the upstream template "
            "repository instead of a fork, so it did not prove fork connectivity.",
        )
        self.assertTrue(
            target_repository_info.json_payload.get("fork") is True
            if isinstance(target_repository_info.json_payload, dict)
            else False,
            "Step 3 failed: the configured setup repository is not marked as a fork.\n"
            f"Observed repository metadata:\n{target_repository_info.stdout}",
        )
        self.assertEqual(
            (
                target_repository_info.json_payload.get("parent", {}).get("full_name")
                if isinstance(target_repository_info.json_payload, dict)
                else None
            ),
            self.config.upstream_repository,
            "Step 3 failed: the configured setup repository is not a fork of the "
            "expected upstream template.\n"
            f"Observed repository metadata:\n{target_repository_info.stdout}",
        )
        self.assertEqual(
            tuple(shlex.split(documented_command or "")),
            project_fetch.command,
            "Step 4 failed: the automation did not execute the exact CLI command "
            "documented in the deployed README.\n"
            f"Documented command: {documented_command}\n"
            f"Executed command: {project_fetch.command_text}",
        )
        self.assertIn(
            project_path,
            project_fetch.command_text,
            "Step 4 failed: the documented command no longer targets the expected "
            "project file path.",
        )
        self.assertIn(
            target_repository,
            project_fetch.command_text,
            "Step 4 failed: the documented command no longer targets the fork "
            "repository under test.",
        )
        self.assertFalse(
            project_fetch.succeeded,
            "Step 4 failed: the README-documented quick-start validation command "
            "unexpectedly succeeded even though the test case precondition requires "
            "the project file to be missing in the fork.\n"
            f"Documented command: {documented_command}\n"
            f"stdout:\n{project_fetch.stdout}\n"
            f"stderr:\n{project_fetch.stderr}",
        )
        self.assertIn(
            "404",
            project_fetch.stderr,
            "Step 4 failed: the terminal-visible error did not include HTTP 404.\n"
            f"stderr:\n{project_fetch.stderr}",
        )
        self.assertIn(
            "Not Found",
            project_fetch.stderr,
            "Step 4 failed: the terminal-visible error did not surface `Not Found`.\n"
            f"stderr:\n{project_fetch.stderr}",
        )
        self.assertEqual(
            project_fetch.stdout.strip(),
            "",
            "Step 4 failed: the missing-file validation command still printed a "
            "JSON payload instead of surfacing only the 404 error.\n"
            f"stdout:\n{project_fetch.stdout}",
        )
        self.assertFalse(
            expected_project_fetch.succeeded,
            "Step 5 failed: the repository still exposed the project file over the "
            "raw content URL, so the missing-file precondition was not satisfied.\n"
            f"Command: {expected_project_fetch.command_text}\n"
            f"stdout:\n{expected_project_fetch.stdout}\n"
            f"stderr:\n{expected_project_fetch.stderr}",
        )
        self.assertIn(
            "404",
            expected_project_fetch.stderr,
            "Step 5 failed: the direct raw-file fetch did not confirm a 404 response.\n"
            f"stderr:\n{expected_project_fetch.stderr}",
        )
        self.assertIsNone(
            None if project_fetch.stdout.strip() == "" else project_fetch.stdout,
            "Human-style verification failed: the README command still produced "
            "parseable project JSON instead of a user-visible 404 error.\n"
            f"stdout:\n{project_fetch.stdout}",
        )
        self.assertEqual(
            project_fetch.stdout.strip(),
            "",
            "Human-style verification failed: the missing-file scenario still "
            "rendered visible project JSON instead of an empty stdout plus 404 "
            "stderr in the terminal.\n"
            f"Observed payload:\n{project_fetch.stdout}",
        )


if __name__ == "__main__":
    unittest.main()
