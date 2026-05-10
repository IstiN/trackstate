from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.project_quick_start_negative_path_validator import (
    ProjectQuickStartNegativePathValidator,
)
from testing.core.interfaces.project_cli_probe import ProjectCliProbe
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.project_quick_start_negative_path_result import (
    ProjectQuickStartNegativePathResult,
)


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


class QuickStartNegativePathRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        repository_root = Path(__file__).resolve().parents[3]
        self.validator = ProjectQuickStartNegativePathValidator(
            repository_root=repository_root,
            probe=_UnusedProbe(),
        )

    def test_inline_negative_paths_preserve_duplicate_occurrences(self) -> None:
        quick_start_section = """
## CLI quick start

Negative validation checks `DEMO/project.missing.json` and repeats
`DEMO/project.missing.json` before the 404 example command.
""".strip()

        self.assertEqual(
            self.validator._inline_negative_paths(quick_start_section),
            (
                "DEMO/project.missing.json",
                "DEMO/project.missing.json",
            ),
        )

    def test_tree_truncated_and_duplicate_properties_surface_review_gaps(self) -> None:
        result = ProjectQuickStartNegativePathResult(
            documentation_repository="IstiN/trackstate-setup",
            default_branch="main",
            positive_project_path="DEMO/project.json",
            quick_start_section="## CLI quick start",
            auth_status=CliCommandResult(command=("gh",), exit_code=0, stdout="", stderr=""),
            repository_info=CliCommandResult(
                command=("gh",), exit_code=0, stdout="", stderr=""
            ),
            readme_fetch=CliCommandResult(command=("gh",), exit_code=0, stdout="", stderr=""),
            tree_fetch=CliCommandResult(
                command=("gh",),
                exit_code=0,
                stdout='{"truncated": true, "tree": []}',
                stderr="",
                json_payload={"truncated": True, "tree": []},
            ),
            inline_negative_paths=(
                "DEMO/project.missing.json",
                "DEMO/project.missing.json",
            ),
            command_negative_paths=(
                "DEMO/project.missing.json",
                "DEMO/project.missing.json",
            ),
            negative_paths=("DEMO/project.missing.json",),
            negative_command_checks=(),
        )

        self.assertTrue(result.tree_truncated)
        self.assertEqual(
            result.duplicate_inline_negative_paths,
            ("DEMO/project.missing.json",),
        )
        self.assertEqual(
            result.duplicate_command_negative_paths,
            ("DEMO/project.missing.json",),
        )


if __name__ == "__main__":
    unittest.main()
