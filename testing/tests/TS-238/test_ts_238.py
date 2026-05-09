from __future__ import annotations

from pathlib import Path
import re
import unittest

from testing.components.services.project_quick_start_validator import (
    ProjectQuickStartValidator,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe


class _UnusedProbe(ProjectCliProbe):
    def auth_status(self):
        raise NotImplementedError

    def run_documented_command(self, command: str):
        raise NotImplementedError

    def viewer_login(self):
        raise NotImplementedError

    def repository_metadata(self, repository: str):
        raise NotImplementedError

    def get_contents(self, repository: str, ref: str, path: str):
        raise NotImplementedError

    def get_raw_file(self, repository: str, ref: str, path: str):
        raise NotImplementedError

    def list_tree(self, repository: str, ref: str):
        raise NotImplementedError

    def get_project(self, repository: str, default_branch: str, project_path: str):
        raise NotImplementedError


class QuickStartReadmeFormattingTest(unittest.TestCase):
    EXPECTED_COMMAND = (
        'gh api repos/<fork>/contents/<project-path>?ref=<default-branch> '
        '-H "Accept: application/vnd.github.raw+json"'
    )

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.readme_path = self.repository_root / "trackstate-setup" / "README.md"
        self.validator = ProjectQuickStartValidator(
            repository_root=self.repository_root,
            probe=_UnusedProbe(),
        )

    def test_cli_validation_command_is_enclosed_in_a_copy_pasteable_code_block(
        self,
    ) -> None:
        readme_text = self.readme_path.read_text(encoding="utf-8")
        quick_start_section = self.validator._read_quick_start_section(readme_text)

        self.assertTrue(
            quick_start_section,
            "Step 2 failed: trackstate-setup/README.md does not contain a "
            "`CLI quick start` section to verify.",
        )

        code_block_commands = self.validator.documented_validation_commands_in_code_blocks(
            quick_start_section,
        )
        self.assertTrue(
            code_block_commands,
            "Step 3 failed: the `CLI quick start` section does not contain an "
            "executable GitHub CLI validation command inside a fenced markdown "
            "code block.\n"
            f"Observed section:\n{quick_start_section}",
        )
        self.assertIn(
            self.EXPECTED_COMMAND,
            code_block_commands,
            "Step 3 failed: the quick-start code block no longer contains the "
            "approved raw `gh api` validation command for fork connectivity.\n"
            f"Observed code-block commands: {code_block_commands}",
        )

        documented_command = self.validator._documented_validation_command(
            quick_start_section,
        )
        self.assertEqual(
            documented_command,
            self.EXPECTED_COMMAND,
            "Step 3 failed: the copy-pasteable command surfaced by the quick "
            "start no longer matches the approved validation command.",
        )

        self.assertRegex(
            quick_start_section,
            re.compile(
                r"Use this GitHub CLI command to validate that your authenticated\s+"
                r"`trackstate-setup` fork exposes the same project JSON the app "
                r"reads:\s+```(?:bash|shell|sh|text)?\n"
                + re.escape(self.EXPECTED_COMMAND)
                + r"\n```",
                re.DOTALL,
            ),
            "Human-style verification failed: the README does not present the "
            "validation command directly under the quick-start guidance as a "
            "visible fenced code block a user can copy as-is.\n"
            f"Observed section:\n{quick_start_section}",
        )


if __name__ == "__main__":
    unittest.main()
