from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

from testing.core.config.setup_repo_smoke_config import load_setup_repo_smoke_config


class SetupRepositoryValidationTest(unittest.TestCase):
    def setUp(self) -> None:
        self._config = load_setup_repo_smoke_config()
        self._repository_root = Path(__file__).resolve().parents[3]
        self._local_setup_root = self._repository_root / "trackstate-setup"
        self._expected_paths = [
            "DEMO/project.json",
            "DEMO/config/fields.json",
            "DEMO/config/statuses.json",
            "DEMO/config/issue-types.json",
            "DEMO/config/workflows.json",
            "DEMO/config/priorities.json",
            "DEMO/config/components.json",
            "DEMO/config/versions.json",
            ".github/workflows/install-update-trackstate.yml",
        ]

    def _run_gh(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ("gh", *args),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )

    def test_local_trackstate_setup_submodule_contains_required_template_data(self) -> None:
        self.assertTrue(
            self._local_setup_root.is_dir(),
            "Step 1 failed: the trackstate-setup submodule directory is missing.",
        )

        missing: list[str] = []
        for relative_path in self._expected_paths:
            path = self._local_setup_root / relative_path
            if not path.is_file():
                missing.append(relative_path)

        self.assertEqual(
            missing,
            [],
            "Step 2 failed: required template files are missing from the local "
            f"trackstate-setup submodule. Missing: {missing}",
        )

    def test_remote_default_branch_contains_required_template_data(self) -> None:
        repo = self._config.repository
        ref = self._config.ref

        tree_result = self._run_gh(
            "api",
            f"repos/{repo}/git/trees/{ref}?recursive=1",
            "--jq",
            ".tree[].path",
        )
        self.assertEqual(
            tree_result.returncode,
            0,
            "Step 1 failed: could not fetch the default-branch tree from the setup repository.\n"
            f"Repository: {repo}\n"
            f"Ref: {ref}\n"
            f"stderr: {tree_result.stderr}",
        )

        remote_paths = set(line.strip() for line in tree_result.stdout.splitlines() if line.strip())
        missing = [
            path for path in self._expected_paths if path not in remote_paths
        ]

        self.assertEqual(
            missing,
            [],
            "Step 2 failed: required template files are missing from the remote "
            f"setup repository default branch. Missing: {missing}",
        )

    def test_remote_project_json_is_parseable(self) -> None:
        repo = self._config.repository
        ref = self._config.ref

        content_result = self._run_gh(
            "api",
            f"repos/{repo}/contents/DEMO/project.json?ref={ref}",
            "-H",
            "Accept: application/vnd.github.raw+json",
        )
        self.assertEqual(
            content_result.returncode,
            0,
            "Step 1 failed: could not read DEMO/project.json from the setup repository.\n"
            f"stderr: {content_result.stderr}",
        )

        try:
            project = json.loads(content_result.stdout)
        except json.JSONDecodeError as error:
            self.fail(
                "Step 2 failed: DEMO/project.json is not valid JSON.\n"
                f"Error: {error}\n"
                f"Content: {content_result.stdout[:500]}"
            )

        self.assertIn(
            "key",
            project,
            "Step 3 failed: DEMO/project.json is missing the 'key' field.",
        )
        self.assertEqual(
            project.get("key"),
            "DEMO",
            "Step 3 failed: DEMO/project.json 'key' does not equal 'DEMO'.",
        )

    def test_template_workflow_file_exists_on_default_branch(self) -> None:
        repo = self._config.repository
        ref = self._config.ref
        workflow_path = ".github/workflows/install-update-trackstate.yml"

        content_result = self._run_gh(
            "api",
            f"repos/{repo}/contents/{workflow_path}?ref={ref}",
            "-H",
            "Accept: application/vnd.github.raw+json",
        )
        self.assertEqual(
            content_result.returncode,
            0,
            "Step 1 failed: the install-update workflow is missing from the setup repository.\n"
            f"Path: {workflow_path}\n"
            f"stderr: {content_result.stderr}",
        )
        self.assertIn(
            "Install / Update TrackState",
            content_result.stdout,
            "Step 2 failed: the workflow file does not appear to be the Install / Update TrackState workflow.",
        )


if __name__ == "__main__":
    unittest.main()
