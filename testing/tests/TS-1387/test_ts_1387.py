from __future__ import annotations

from pathlib import Path
import re
import shlex
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


class QuickStartCliSyntaxTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.readme_path = self.repository_root / "trackstate-setup" / "README.md"
        self.validator = ProjectQuickStartValidator(
            repository_root=self.repository_root,
            probe=_UnusedProbe(),
        )

    def test_readme_quick_start_command_uses_approved_syntax(self) -> None:
        readme_text = self.readme_path.read_text(encoding="utf-8")
        quick_start_section = self.validator._read_quick_start_section(readme_text)

        self.assertTrue(
            quick_start_section,
            "Step 1 failed: trackstate-setup/README.md does not contain a "
            "`CLI quick start` section to verify.",
        )

        code_block_commands = self.validator.documented_validation_commands_in_code_blocks(
            quick_start_section,
        )
        self.assertTrue(
            code_block_commands,
            "Step 2 failed: the `CLI quick start` section does not contain an "
            "executable GitHub CLI validation command inside a fenced markdown "
            "code block.\n"
            f"Observed section:\n{quick_start_section}",
        )

        command = code_block_commands[0]

        self.assertIn(
            "<fork>",
            command,
            "Step 3 failed: the quick-start command does not use the approved "
            "`<fork>` repository placeholder.\n"
            f"Observed command: {command}",
        )
        self.assertNotIn(
            "<repository>",
            command,
            "Step 3 failed: the quick-start command still uses the deprecated "
            "`<repository>` placeholder instead of `<fork>`.\n"
            f"Observed command: {command}",
        )
        self.assertRegex(
            command,
            re.compile(r"\s-H\s+['\"]Accept:\s*application/vnd\.github\.raw\+json['\"]"),
            "Step 4 failed: the quick-start command does not use the short `-H` "
            "flag with the approved raw JSON Accept header.\n"
            f"Observed command: {command}",
        )
        self.assertNotRegex(
            command,
            re.compile(r"\s--header\s"),
            "Step 4 failed: the quick-start command uses the long `--header` flag "
            "instead of the approved `-H` shorthand.\n"
            f"Observed command: {command}",
        )

        # Single-line command: no literal newlines inside the quoted command.
        self.assertNotIn(
            "\n",
            command,
            "Step 5 failed: the quick-start command contains a literal newline, "
            "so it is not a single-line copy-pasteable snippet.\n"
            f"Observed command: {command!r}",
        )

        # Syntactically parseable as a shell command.
        try:
            parsed = shlex.split(command)
        except ValueError as exc:
            self.fail(
                "Step 5 failed: the quick-start command is not a valid shell "
                f"command.\nCommand: {command}\nError: {exc}"
            )

        self.assertEqual(
            parsed[:3],
            [
                "gh",
                "api",
                "repos/<fork>/contents/<project-path>?ref=<default-branch>",
            ],
            "Step 6 failed: the quick-start command does not have the expected "
            "`gh api repos/<fork>/contents/<project-path>?ref=<default-branch>` "
            "shape.\n"
            f"Observed parsed command: {parsed}",
        )

        self.assertRegex(
            quick_start_section,
            re.compile(
                r"```bash\n"
                + re.escape(command)
                + r"\n```",
                re.DOTALL,
            ),
            "Human-style verification failed: the approved validation command is "
            "not presented as a visible `bash` fenced code block a user can copy "
            "as-is from the `CLI quick start` section.\n"
            f"Observed section:\n{quick_start_section}",
        )


if __name__ == "__main__":
    unittest.main()
