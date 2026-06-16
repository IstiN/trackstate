from __future__ import annotations

from pathlib import Path
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


class QuickStartReadmeContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.readme_path = self.repository_root / "trackstate-setup" / "README.md"
        self.validator = ProjectQuickStartValidator(
            repository_root=self.repository_root,
            probe=_UnusedProbe(),
        )

    def test_cli_quick_start_documents_raw_project_validation_command(self) -> None:
        readme_text = self.readme_path.read_text(encoding="utf-8")
        quick_start_section = self.validator._read_quick_start_section(readme_text)

        self.assertTrue(
            quick_start_section,
            "Expected trackstate-setup/README.md to contain a `CLI quick start` section.",
        )

        documented_command = self.validator._documented_validation_command(
            quick_start_section
        )

        self.assertEqual(
            documented_command,
            'gh api repos/<fork>/contents/<project-path>?ref=<default-branch> -H "Accept: application/vnd.github.raw+json"',
            "Expected the CLI quick start to document the executable raw `gh api` "
            "command that prints the fork project JSON without using shell pipes.",
        )

        expanded_command = self.validator._expand_documented_command(
            documented_command,
            target_repository="octocat/trackstate-setup",
            default_branch="main",
            project_path="DEMO/project.json",
        )

        self.assertEqual(
            expanded_command,
            'gh api repos/octocat/trackstate-setup/contents/DEMO/project.json?ref=main -H "Accept: application/vnd.github.raw+json"',
        )


if __name__ == "__main__":
    unittest.main()
