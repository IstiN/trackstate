from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import unittest

from testing.components.services.project_quick_start_walkthrough_validator import (
    ProjectQuickStartWalkthroughValidator,
)
from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.tests.support.project_cli_probe_factory import create_project_cli_probe


class QuickStartCliManualWalkthroughTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ProjectCliValidationConfig.from_env()
        self.validator = ProjectQuickStartWalkthroughValidator(
            repository_root=self.repository_root,
            probe=create_project_cli_probe(self.repository_root),
        )

    def test_readme_cli_snippets_yield_documented_results(self) -> None:
        result = self.validator.validate(config=self.config)
        self._write_result_if_requested(result.to_dict())

        self.assertTrue(
            result.auth_status.succeeded,
            "Precondition failed: `gh auth status` did not confirm an authenticated "
            "GitHub CLI session.\n"
            f"Command: {result.auth_status.command_text}\n"
            f"Exit code: {result.auth_status.exit_code}\n"
            f"stdout:\n{result.auth_status.stdout}\n"
            f"stderr:\n{result.auth_status.stderr}",
        )
        self.assertTrue(
            result.viewer_login.succeeded,
            "Precondition failed: the test could not resolve the authenticated "
            "GitHub login needed to target the fork under test.\n"
            f"Command: {result.viewer_login.command_text}\n"
            f"Exit code: {result.viewer_login.exit_code}\n"
            f"stdout:\n{result.viewer_login.stdout}\n"
            f"stderr:\n{result.viewer_login.stderr}",
        )
        self.assertTrue(
            (result.viewer_login.json_payload or "").strip(),
            "Precondition failed: `gh api user --jq .login` returned an empty login.",
        )
        self.assertTrue(
            result.readme_fetch.succeeded,
            "Step 1 failed: the test could not read the deployed README needed for "
            "the walkthrough.\n"
            f"Repository: {result.documentation_repository}\n"
            f"Command: {result.readme_fetch.command_text}\n"
            f"stderr:\n{result.readme_fetch.stderr}",
        )
        self.assertTrue(
            result.quick_start_section,
            "Step 1 failed: the deployed README does not contain a `CLI quick start` "
            "section.",
        )
        self.assertEqual(
            len(result.code_block_commands),
            2,
            "Step 1 failed: TS-253 expected exactly two copy-pasteable CLI code-block "
            "commands in `CLI quick start` (positive and negative paths).\n"
            f"Observed commands: {result.code_block_commands}",
        )
        self.assertTrue(
            result.repository_info.succeeded,
            "Precondition failed: the test could not inspect the setup repository "
            "selected for the walkthrough.\n"
            f"Repository: {result.target_repository}\n"
            f"Command: {result.repository_info.command_text}\n"
            f"stderr:\n{result.repository_info.stderr}",
        )
        self.assertNotEqual(
            result.target_repository,
            result.upstream_repository,
            "Precondition failed: the walkthrough targeted the upstream template "
            "repository instead of a fork.",
        )
        self.assertTrue(
            result.repository_is_fork,
            "Precondition failed: the setup repository under test is not marked as a "
            "fork.\n"
            f"Observed repository metadata:\n{result.repository_info.stdout}",
        )
        self.assertEqual(
            result.repository_parent,
            result.upstream_repository,
            "Precondition failed: the selected fork does not point back to the "
            "expected upstream setup repository.\n"
            f"Observed repository metadata:\n{result.repository_info.stdout}",
        )

        self.assertIn(
            "gh api repos/<repository>/contents/<project-path>?ref=<default-branch>",
            result.positive_command.template,
            "Step 2 failed: the README no longer documents the positive quick-start "
            "command in the expected shape.\n"
            f"Observed command: {result.positive_command.template}",
        )
        self.assertIn(
            'Accept: application/vnd.github.raw+json',
            result.positive_command.template,
            "Step 2 failed: the positive README command no longer requests the raw "
            "JSON payload.\n"
            f"Observed command: {result.positive_command.template}",
        )
        self.assertEqual(
            tuple(result.positive_command.result.command),
            tuple(shlex.split(result.positive_command.command)),
            "Step 2 failed: the automation did not execute the exact positive command "
            "copied from the README.\n"
            f"Expected command: {result.positive_command.command}\n"
            f"Executed command: {result.positive_command.result.command_text}",
        )
        self.assertTrue(
            result.positive_command.result.succeeded,
            "Step 2 failed: the positive README quick-start command did not succeed.\n"
            f"Command: {result.positive_command.command}\n"
            f"stdout:\n{result.positive_command.result.stdout}\n"
            f"stderr:\n{result.positive_command.result.stderr}",
        )
        self.assertTrue(
            result.expected_project_fetch.succeeded,
            "Step 2 failed: the fork did not expose the documented project file over "
            "the raw content URL.\n"
            f"Path: {result.project_path}\n"
            f"stderr:\n{result.expected_project_fetch.stderr}",
        )
        self.assertEqual(
            result.actual_project,
            result.expected_project,
            "Step 2 failed: the positive README command did not print the same JSON "
            "document stored in the fork.\n"
            f"Command output:\n{result.positive_command.result.stdout}\n"
            f"Expected payload:\n{result.expected_project_fetch.stdout}",
        )
        for fragment in self.config.visible_project_fields:
            self.assertIn(
                fragment,
                result.positive_command.result.stdout,
                "Human-style verification failed: the positive walkthrough output did "
                "not visibly show the documented project JSON in the terminal.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{result.positive_command.result.stdout}",
            )
        self.assertEqual(
            result.positive_command.result.stderr.strip(),
            "",
            "Human-style verification failed: the positive walkthrough printed an "
            "unexpected terminal error.\n"
            f"stderr:\n{result.positive_command.result.stderr}",
        )

        self.assertIn(
            "DEMO/project.missing.json",
            result.negative_command.template,
            "Step 3 failed: the README no longer documents the negative quick-start "
            "command against the missing project file path.\n"
            f"Observed command: {result.negative_command.template}",
        )
        self.assertEqual(
            tuple(result.negative_command.result.command),
            tuple(shlex.split(result.negative_command.command)),
            "Step 3 failed: the automation did not execute the exact negative command "
            "copied from the README.\n"
            f"Expected command: {result.negative_command.command}\n"
            f"Executed command: {result.negative_command.result.command_text}",
        )
        self.assertFalse(
            result.negative_command.result.succeeded,
            "Step 3 failed: the negative README quick-start command unexpectedly "
            "succeeded.\n"
            f"Command: {result.negative_command.command}\n"
            f"stdout:\n{result.negative_command.result.stdout}\n"
            f"stderr:\n{result.negative_command.result.stderr}",
        )
        self.assertIn(
            "404",
            result.negative_command.output,
            "Step 3 failed: the negative README command did not surface HTTP 404.\n"
            f"Observed output:\n{result.negative_command.output}",
        )
        self.assertIn(
            "Not Found",
            result.negative_command.output,
            "Step 3 failed: the negative README command did not surface `Not Found` "
            "to the terminal user.\n"
            f"Observed output:\n{result.negative_command.output}",
        )
        self.assertNotEqual(
            result.negative_command.result.stdout.strip(),
            result.positive_command.result.stdout.strip(),
            "Human-style verification failed: the negative walkthrough echoed the "
            "successful project JSON instead of surfacing a missing-file error.\n"
            f"Negative stdout:\n{result.negative_command.result.stdout}",
        )
        self.assertIn(
            '"status":"404"',
            result.negative_command.result.stdout,
            "Human-style verification failed: the negative walkthrough did not "
            "surface GitHub's 404 error payload in the terminal output.\n"
            f"stdout:\n{result.negative_command.result.stdout}",
        )
        self.assertFalse(
            result.negative_project_fetch.succeeded,
            "Step 3 failed: the missing project path still resolved over the raw file "
            "URL, so the negative walkthrough did not exercise a missing file.\n"
            f"Path: {result.negative_command.project_path}\n"
            f"stdout:\n{result.negative_project_fetch.stdout}",
        )
        self.assertIn(
            "404",
            result.negative_project_fetch.stderr,
            "Step 3 failed: the direct raw-file read did not confirm HTTP 404 for the "
            "missing project path.\n"
            f"stderr:\n{result.negative_project_fetch.stderr}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS253_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
