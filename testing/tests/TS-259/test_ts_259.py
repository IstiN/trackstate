from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest
from urllib.parse import quote

import yaml

from testing.frameworks.python.gh_cli_api_client import GhCliApiClient


class ActionlintWorkflowReferenceTest(unittest.TestCase):
    expected_action_ref = "rhysd/actionlint@v1.7.12"

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.repository = "IstiN/trackstate-setup"
        self.workflow_path = ".github/workflows/actionlint.yml"
        self.local_workflow_path = self.repository_root / "trackstate-setup" / self.workflow_path
        self.github_api_client = GhCliApiClient(self.repository_root)
        repository_metadata = json.loads(
            self.github_api_client.request_text(endpoint=f"/repos/{self.repository}")
        )
        self.default_branch = str(repository_metadata["default_branch"])

    def test_checked_out_submodule_workflow_uses_a_published_release_tag(self) -> None:
        workflow = self._read_local_workflow()

        self._assert_action_ref(
            workflow,
            "The checked-out `trackstate-setup` submodule workflow must pin "
            "`rhysd/actionlint` to a published release tag so this repository tracks "
            "the shipped setup fix instead of only observing it remotely.",
        )

    def test_live_actionlint_workflow_uses_a_published_release_tag(self) -> None:
        workflow = self._read_workflow(ref=self.default_branch)

        self._assert_action_ref(
            workflow,
            "The live trackstate-setup Actionlint workflow must pin "
            "`rhysd/actionlint` to a published release tag so GitHub Actions can "
            "resolve the action before linting workflow files.",
        )

    def test_checked_out_submodule_commit_uses_the_same_published_release_tag(self) -> None:
        workflow = self._read_workflow(ref=self._checked_out_setup_commit())

        self._assert_action_ref(
            workflow,
            "The checked-out `trackstate-setup` submodule commit must reference the same "
            "published `rhysd/actionlint` release tag as the live setup repository.",
        )

    def _assert_action_ref(self, workflow: dict[str, object], message: str) -> None:
        self.assertEqual(
            self._extract_action_ref(workflow),
            self.expected_action_ref,
            message,
        )

    def _read_local_workflow(self) -> dict[str, object]:
        return self._load_workflow(self.local_workflow_path.read_text(encoding="utf-8"))

    def _read_workflow(self, *, ref: str) -> dict[str, object]:
        workflow_text = self.github_api_client.request_text(
            endpoint=(
                f"/repos/{self.repository}/contents/"
                f"{quote(self.workflow_path, safe='/')}?ref={quote(ref, safe='')}"
            ),
            field_args=["-H", "Accept: application/vnd.github.raw+json"],
        )
        return self._load_workflow(workflow_text)

    def _load_workflow(self, workflow_text: str) -> dict[str, object]:
        workflow = yaml.safe_load(workflow_text)
        if not isinstance(workflow, dict):
            self.fail(
                f"Expected {self.workflow_path} to decode to a mapping, "
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

    def _checked_out_setup_commit(self) -> str:
        completed = subprocess.run(
            ["git", "-C", "trackstate-setup", "rev-parse", "HEAD"],
            cwd=self.repository_root,
            check=True,
            capture_output=True,
            text=True,
        )
        commit = completed.stdout.strip()
        self.assertRegex(
            commit,
            r"^[0-9a-f]{40}$",
            "Expected `git -C trackstate-setup rev-parse HEAD` to return a commit SHA.",
        )
        return commit


if __name__ == "__main__":
    unittest.main()
