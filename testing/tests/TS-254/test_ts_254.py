from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path
import re
import unittest

from testing.components.services.project_quick_start_negative_path_validator import (
    ProjectQuickStartNegativePathValidator,
)
from testing.core.config.project_cli_validation_config import (
    ProjectCliValidationConfig,
)
from testing.tests.support.project_cli_probe_factory import create_project_cli_probe


class QuickStartNegativePathUniquenessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        base_config = ProjectCliValidationConfig.from_env()
        self.config = replace(
            base_config,
            readme_repository_override=base_config.upstream_repository,
        )
        self.probe = create_project_cli_probe(self.repository_root)
        self.validator = ProjectQuickStartNegativePathValidator(
            repository_root=self.repository_root,
            probe=self.probe,
        )

    def test_negative_validation_examples_use_unique_nonexistent_paths(self) -> None:
        result = self.validator.validate(config=self.config)

        self.assertTrue(
            result.auth_status.succeeded,
            "Precondition failed: `gh auth status` did not confirm a usable GitHub "
            "CLI session for the live README validation.\n"
            f"Command: {result.auth_status.command_text}\n"
            f"Exit code: {result.auth_status.exit_code}\n"
            f"stdout:\n{result.auth_status.stdout}\n"
            f"stderr:\n{result.auth_status.stderr}",
        )
        self.assertEqual(
            result.documentation_repository,
            self.config.upstream_repository,
            "Step 1 failed: TS-254 did not validate the deployed upstream setup "
            "repository.\n"
            f"Expected repository: {self.config.upstream_repository}\n"
            f"Observed repository: {result.documentation_repository}",
        )
        self.assertTrue(
            result.repository_info.succeeded,
            "Step 1 failed: the test could not inspect the live setup repository "
            "metadata before checking the negative validation path.\n"
            f"Command: {result.repository_info.command_text}\n"
            f"Exit code: {result.repository_info.exit_code}\n"
            f"stdout:\n{result.repository_info.stdout}\n"
            f"stderr:\n{result.repository_info.stderr}",
        )
        self.assertTrue(
            result.readme_fetch.succeeded,
            "Step 1 failed: the test could not fetch README.md from the live setup "
            "repository, so it could not inspect the documented negative example.\n"
            f"Command: {result.readme_fetch.command_text}\n"
            f"Exit code: {result.readme_fetch.exit_code}\n"
            f"stdout:\n{result.readme_fetch.stdout}\n"
            f"stderr:\n{result.readme_fetch.stderr}",
        )
        self.assertTrue(
            result.quick_start_section,
            "Step 1 failed: the deployed README does not contain the `CLI quick "
            "start` section required for this validation.",
        )
        self.assertIn(
            "DEMO/project.missing.json",
            result.negative_paths,
            "Step 1 failed: the deployed README no longer documents "
            "`DEMO/project.missing.json` as the negative validation example.\n"
            f"Observed quick-start section:\n{result.quick_start_section}",
        )
        self.assertEqual(
            result.positive_project_path,
            "DEMO/project.json",
            "Step 1 failed: the positive validation path in the live README changed, "
            "so TS-254 can no longer compare the negative example against the "
            "documented project file.\n"
            f"Observed positive path: {result.positive_project_path}",
        )

        self.assertTrue(
            result.tree_fetch.succeeded,
            "Step 2 failed: the test could not browse the live repository tree on "
            "the default branch.\n"
            f"Command: {result.tree_fetch.command_text}\n"
            f"Exit code: {result.tree_fetch.exit_code}\n"
            f"stdout:\n{result.tree_fetch.stdout}\n"
            f"stderr:\n{result.tree_fetch.stderr}",
        )
        self.assertFalse(
            result.tree_truncated,
            "Step 2 failed: the live repository tree response was truncated, so the "
            "test cannot prove the documented negative path is absent.\n"
            f"Command: {result.tree_fetch.command_text}\n"
            f"Tree payload:\n{result.tree_fetch.stdout}",
        )
        self.assertTrue(
            result.tree_paths,
            "Step 2 failed: the live repository tree response did not expose any "
            "paths to validate against the documented negative example.\n"
            f"Tree payload:\n{result.tree_fetch.stdout}",
        )

        self.assertTrue(
            result.negative_paths,
            "Step 3 failed: the `CLI quick start` section does not expose any "
            "negative validation path examples.\n"
            f"Observed quick-start section:\n{result.quick_start_section}",
        )
        self.assertEqual(
            result.duplicate_inline_negative_paths,
            (),
            "Step 4 failed: the live README repeats inline negative validation "
            "paths instead of documenting unique examples.\n"
            f"Inline negative paths: {result.inline_negative_paths}\n"
            f"Duplicate inline paths: {result.duplicate_inline_negative_paths}",
        )
        self.assertEqual(
            result.duplicate_command_negative_paths,
            (),
            "Step 4 failed: the live README repeats executable negative "
            "validation paths instead of documenting unique commands.\n"
            f"Command negative paths: {result.command_negative_paths}\n"
            f"Duplicate command paths: {result.duplicate_command_negative_paths}",
        )
        self.assertNotIn(
            result.positive_project_path,
            result.negative_paths,
            "Step 4 failed: the documented negative validation path collides with "
            "the positive project path.\n"
            f"Positive project path: {result.positive_project_path}\n"
            f"Observed negative paths: {result.negative_paths}",
        )
        self.assertEqual(
            result.existing_negative_paths,
            (),
            "Step 3 failed: at least one documented negative validation path still "
            "exists in the live repository tree.\n"
            f"Existing negative paths: {result.existing_negative_paths}\n"
            f"Observed negative paths: {result.negative_paths}",
        )

        self.assertTrue(
            result.negative_command_checks,
            "Step 4 failed: the live README does not include an executable negative "
            "`gh api` validation command.\n"
            f"Observed quick-start section:\n{result.quick_start_section}",
        )
        self.assertEqual(
            Counter(result.inline_negative_paths),
            Counter(result.command_negative_paths),
            "Step 4 failed: the inline negative path example and the executable "
            "negative command no longer point to the same path occurrences.\n"
            f"Inline negative paths: {result.inline_negative_paths}\n"
            f"Command negative paths: {result.command_negative_paths}",
        )

        for negative_check in result.negative_command_checks:
            observed_terminal_output = "\n".join(
                fragment
                for fragment in (
                    negative_check.command_result.stdout.strip(),
                    negative_check.command_result.stderr.strip(),
                )
                if fragment
            )
            self.assertFalse(
                negative_check.command_result.succeeded,
                "Step 4 failed: the documented negative validation command "
                "unexpectedly succeeded against the live repository.\n"
                f"Path: {negative_check.path}\n"
                f"Command: {negative_check.documented_command}\n"
                f"stdout:\n{negative_check.command_result.stdout}\n"
                f"stderr:\n{negative_check.command_result.stderr}",
            )
            self.assertIn(
                "404",
                negative_check.command_result.stderr,
                "Step 4 failed: the terminal-visible error for the documented "
                "negative command did not include HTTP 404.\n"
                f"Path: {negative_check.path}\n"
                f"stderr:\n{negative_check.command_result.stderr}",
            )
            self.assertIn(
                "Not Found",
                negative_check.command_result.stderr,
                "Step 4 failed: the terminal-visible error for the documented "
                "negative command did not surface `Not Found`.\n"
                f"Path: {negative_check.path}\n"
                f"stderr:\n{negative_check.command_result.stderr}",
            )
            self.assertRegex(
                observed_terminal_output,
                re.compile(r"404.*not found|not found.*404", re.IGNORECASE | re.DOTALL),
                "Step 4 failed: the combined terminal output did not clearly show "
                "a user-visible 404 Not Found failure for the documented negative "
                "command.\n"
                f"Path: {negative_check.path}\n"
                f"Observed output:\n{observed_terminal_output}",
            )
            self.assertNotIn(
                '"key": "DEMO"',
                negative_check.command_result.stdout,
                "Step 4 failed: the documented negative command still surfaced the "
                "project JSON payload instead of a missing-file failure.\n"
                f"Path: {negative_check.path}\n"
                f"stdout:\n{negative_check.command_result.stdout}",
            )
            self.assertNotIn(
                '"name": "Demo TrackState Project"',
                negative_check.command_result.stdout,
                "Step 4 failed: the documented negative command still surfaced the "
                "demo project payload instead of a missing-file failure.\n"
                f"Path: {negative_check.path}\n"
                f"stdout:\n{negative_check.command_result.stdout}",
            )
            self.assertRegex(
                negative_check.documented_command,
                re.compile(
                    rf"^gh api repos/{re.escape(result.documentation_repository)}/contents/"
                    rf"{re.escape(negative_check.path)}\?ref={re.escape(result.default_branch)}\b",
                ),
                "Human-style verification failed: the executed terminal command did "
                "not visibly target the live README example path in the setup "
                "repository.\n"
                f"Observed command: {negative_check.documented_command}",
            )


if __name__ == "__main__":
    unittest.main()
