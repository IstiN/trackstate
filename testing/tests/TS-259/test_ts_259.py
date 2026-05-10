from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest
from urllib.parse import quote

import yaml

from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


class ActionlintWorkflowReferenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.repository = "IstiN/trackstate-setup"
        self.workflow_path = ".github/workflows/actionlint.yml"
        self.github_api_client = GhCliApiClient(self.repository_root)
        repository_metadata = json.loads(
            self.github_api_client.request_text(endpoint=f"/repos/{self.repository}")
        )
        self.default_branch = str(repository_metadata["default_branch"])

    def test_live_actionlint_workflow_uses_a_published_release_tag(self) -> None:
        workflow = self._read_workflow(ref=self.default_branch)
        action_ref = self._extract_action_ref(workflow)

        self.assertEqual(
            action_ref,
            "rhysd/actionlint@v1.7.12",
            "The live trackstate-setup Actionlint workflow must pin "
            "`rhysd/actionlint` to a published release tag so GitHub Actions can "
            "resolve the action before linting workflow files.",
        )

    def test_tracked_submodule_commit_uses_the_same_published_release_tag(self) -> None:
        workflow = self._read_workflow(ref=self._tracked_setup_commit())
        action_ref = self._extract_action_ref(workflow)

        self.assertEqual(
            action_ref,
            "rhysd/actionlint@v1.7.12",
            "The tracked `trackstate-setup` submodule commit must reference the same "
            "published `rhysd/actionlint` release tag as the live setup repository.",
        )

    def _read_workflow(self, *, ref: str) -> dict[str, object]:
        workflow_text = self.github_api_client.request_text(
            endpoint=(
                f"/repos/{self.repository}/contents/"
                f"{quote(self.workflow_path, safe='/')}?ref={quote(ref, safe='')}"
            ),
            field_args=["-H", "Accept: application/vnd.github.raw+json"],
        )
        workflow = yaml.safe_load(workflow_text)
        if not isinstance(workflow, dict):
            self.fail(
                f"Expected {self.workflow_path} at {ref} to decode to a mapping, "
                f"got {type(workflow).__name__}."
            )
        return workflow

    def _extract_action_ref(self, workflow: dict[str, object]) -> object:
        action_step = next(
            step
            for step in workflow["jobs"]["actionlint"]["steps"]
            if isinstance(step, dict) and step.get("name") == "Run actionlint"
        )
        return action_step.get("uses")

    def _tracked_setup_commit(self) -> str:
        completed = subprocess.run(
            ["git", "ls-tree", "HEAD", "trackstate-setup"],
            cwd=self.repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
        parts = completed.stdout.strip().split()
        self.assertGreaterEqual(
            len(parts),
            3,
            "Expected `git ls-tree HEAD trackstate-setup` to return a gitlink entry.",
        )
        return parts[2]


if __name__ == "__main__":
    unittest.main()
