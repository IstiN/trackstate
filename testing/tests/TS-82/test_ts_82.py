from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.template_workflow_file_verifier import (
    TemplateWorkflowFileVerifier,
)
from testing.core.config.template_workflow_file_config import TemplateWorkflowFileConfig
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.template_workflow_file_verification_result import (
    TemplateWorkflowFileVerificationResult,
)
from testing.tests.support.github_repository_directory_page_factory import (
    create_github_repository_directory_page,
)
from testing.tests.support.project_cli_probe_factory import create_project_cli_probe


class TemplateWorkflowFileExistsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TemplateWorkflowFileConfig.from_env()
        self.probe: ProjectCliProbe = create_project_cli_probe(self.repository_root)
        self.verifier = TemplateWorkflowFileVerifier(self.probe)

    def test_default_branch_contains_install_update_trackstate_workflow_file(self) -> None:
        result = self.verifier.validate(config=self.config)

        self.assertTrue(
            result.repository_info.succeeded,
            "Step 1 failed: the test could not open the upstream template repository "
            "metadata on GitHub.\n"
            f"Command: {result.repository_info.command_text}\n"
            f"Exit code: {result.repository_info.exit_code}\n"
            f"stdout:\n{result.repository_info.stdout}\n"
            f"stderr:\n{result.repository_info.stderr}",
        )
        self.assertEqual(
            result.target_repository,
            self.config.repository,
            "Step 1 failed: the verification targeted the wrong upstream "
            f"repository. Expected {self.config.repository}, got "
            f"{result.target_repository}.",
        )

        default_branch = result.repository_default_branch
        self.assertTrue(
            default_branch,
            "Step 2 failed: the upstream repository metadata did not expose a "
            "default branch name.\n"
            f"Observed metadata:\n{result.repository_info.stdout}",
        )
        if self.config.expected_default_branch is not None:
            self.assertEqual(
                default_branch,
                self.config.expected_default_branch,
                "Step 2 failed: the upstream repository default branch changed.\n"
                f"Expected default branch: {self.config.expected_default_branch}\n"
                f"Observed default branch: {default_branch}",
            )

        self.assertTrue(
            result.directory_fetch.succeeded,
            "Step 3 failed: the test could not open the `.github/workflows` "
            "directory from the upstream repository default branch.\n"
            f"Command: {result.directory_fetch.command_text}\n"
            f"Exit code: {result.directory_fetch.exit_code}\n"
            f"stdout:\n{result.directory_fetch.stdout}\n"
            f"stderr:\n{result.directory_fetch.stderr}",
        )
        self.assertIn(
            self.config.workflow_filename,
            result.workflow_directory_entries,
            "Step 4 failed: the workflow file was missing from the "
            f"{self.config.workflow_directory_path} directory listing on the "
            f"default branch {default_branch}.\n"
            f"Observed entries: {result.workflow_directory_entries}",
        )
        self.assertIn(
            self.config.workflow_path,
            result.tree_paths,
            "Step 4 failed: the workflow file path was missing from the default "
            f"branch tree for {self.config.repository}.\n"
            f"Observed path sample: {result.tree_paths[:25]}",
        )
        self.assertTrue(
            result.workflow_contents_fetch.succeeded,
            "Step 4 failed: GitHub did not return metadata for the workflow file "
            f"{self.config.workflow_path} on branch {default_branch}.\n"
            f"Command: {result.workflow_contents_fetch.command_text}\n"
            f"Exit code: {result.workflow_contents_fetch.exit_code}\n"
            f"stdout:\n{result.workflow_contents_fetch.stdout}\n"
            f"stderr:\n{result.workflow_contents_fetch.stderr}",
        )
        self.assertEqual(
            result.workflow_entry_type,
            "file",
            "Step 4 failed: the expected workflow path did not resolve to a file.\n"
            f"Observed metadata:\n{result.workflow_contents_fetch.stdout}",
        )
        self.assertTrue(
            result.workflow_raw_fetch.succeeded,
            "Step 4 failed: the workflow file could not be fetched as raw text from "
            f"{self.config.repository}@{default_branch}.\n"
            f"Command: {result.workflow_raw_fetch.command_text}\n"
            f"Exit code: {result.workflow_raw_fetch.exit_code}\n"
            f"stdout:\n{result.workflow_raw_fetch.stdout}\n"
            f"stderr:\n{result.workflow_raw_fetch.stderr}",
        )
        self.assertIn(
            "name: Install / Update TrackState",
            result.workflow_raw_text,
            "Step 4 failed: the fetched file content did not look like the expected "
            "workflow definition.\n"
            f"Observed file preview:\n{result.workflow_raw_text[:500]}",
        )
        self.assertIn(
            "workflow_dispatch:",
            result.workflow_raw_text,
            "Step 4 failed: the fetched file content did not expose the expected "
            "workflow trigger configuration.\n"
            f"Observed file preview:\n{result.workflow_raw_text[:500]}",
        )

        self._assert_human_visible_directory_view(result=result, default_branch=default_branch)

    def _assert_human_visible_directory_view(
        self,
        *,
        result: TemplateWorkflowFileVerificationResult,
        default_branch: str,
    ) -> None:
        page = create_github_repository_directory_page()
        observation = page.open_directory(
            repository=self.config.repository,
            branch=default_branch,
            directory_path=self.config.workflow_directory_path,
            expected_filename=self.config.workflow_filename,
        )

        self.assertIn(
            self.config.workflow_filename,
            observation.body_text,
            "Human-style verification failed: the GitHub directory page did not "
            f"visibly list {self.config.workflow_filename}.\n"
            f"URL: {observation.url}\nVisible body text:\n{observation.body_text}",
        )
        self.assertIn(
            "trackstate-setup",
            observation.body_text,
            "Human-style verification failed: the visible GitHub page content did "
            "not look like the expected upstream repository view.\n"
            f"URL: {observation.url}\nVisible body text:\n{observation.body_text}",
        )
        self.assertIn(
            "workflows",
            observation.body_text,
            "Human-style verification failed: the browser did not appear to open "
            "the workflows directory page.\n"
            f"URL: {observation.url}\nVisible body text:\n{observation.body_text}",
        )
        workflow_html_url = result.workflow_html_url
        if workflow_html_url is not None:
            self.assertIn(
                self.config.workflow_filename,
                workflow_html_url,
                "Step 4 failed: the GitHub metadata HTML URL does not point at the "
                "expected workflow file.\n"
                f"Observed html_url: {workflow_html_url}",
            )


if __name__ == "__main__":
    unittest.main()
