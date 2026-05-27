from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.actionlint_workflow_gate_config import (
    ActionlintWorkflowGateConfig,
)
from testing.core.interfaces.actionlint_workflow_gate_probe import (
    ActionlintWorkflowGateProbe,
)
from testing.tests.support.actionlint_workflow_gate_probe_factory import (
    create_actionlint_workflow_gate_probe,
)


class ActionlintValidWorkflowPassesTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config_path = self.repository_root / "testing/tests/TS-256/config.yaml"
        self.config = ActionlintWorkflowGateConfig.from_file(self.config_path)
        self.probe: ActionlintWorkflowGateProbe = create_actionlint_workflow_gate_probe(
            self.repository_root,
            config_path=self.config_path,
        )

    def test_push_valid_workflow_change_passes_actionlint(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-256 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.base_branch,
            "Step 1 failed: TS-256 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.base_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertTrue(
            observation.target_workflow_present_on_default_branch,
            "Step 1 failed: the live repository does not expose the workflow "
            "TS-256 needs to update.\n"
            f"Expected workflow path: {self.config.target_workflow_path}\n"
            f"Observed workflow paths: {observation.default_branch_workflow_paths}",
        )
        self.assertTrue(
            observation.workflows_declaring_actionlint,
            "Step 1 failed: the live default branch does not expose any GitHub "
            "Actions workflow declaring actionlint, so TS-256 cannot verify the "
            "successful validation path.\n"
            f"Repository: {observation.repository}\n"
            f"Default branch workflow paths: {observation.default_branch_workflow_paths}",
        )
        self.assertTrue(
            observation.pushed_branch.startswith(self.config.branch_prefix),
            "Step 2 failed: the disposable branch did not use the configured "
            "TS-256 prefix.\n"
            f"Expected prefix: {self.config.branch_prefix}\n"
            f"Observed branch: {observation.pushed_branch}",
        )
        self.assertTrue(
            observation.pushed_commit_sha,
            "Step 3 failed: the disposable branch push did not return a commit SHA.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Workflow preview: {observation.mutated_line_preview}",
        )
        self.assertGreater(
            observation.observed_branch_run_count,
            0,
            "Step 4 failed: pushing the valid workflow change did not produce any "
            "GitHub Actions pipeline run to inspect.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Actions page: {observation.branch_actions_page_url}",
        )
        self.assertIsNotNone(
            observation.actionlint_run_url,
            "Step 4 failed: GitHub Actions did not expose an actionlint validation "
            "run for the pushed branch.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Observed run names: {observation.observed_branch_run_names}\n"
            f"Observed run paths: {observation.observed_branch_run_paths}\n"
            f"Observed run URLs: {observation.observed_branch_run_urls}",
        )
        assert observation.actionlint_run_url is not None
        self.assertIn(
            "/actions/runs/",
            observation.actionlint_run_url,
            "Step 4 failed: the actionlint validation did not expose a GitHub "
            "Actions run URL.\n"
            f"Observed URL: {observation.actionlint_run_url}",
        )
        self.assertEqual(
            observation.actionlint_run_conclusion,
            "success",
            "Step 4 failed: the actionlint workflow did not complete successfully "
            "for the valid workflow change.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Run status: {observation.actionlint_run_status}\n"
            f"Run conclusion: {observation.actionlint_run_conclusion}\n"
            f"Observed branch runs: {observation.observed_branch_run_names}\n"
            f"Observed branch conclusions: {observation.observed_branch_run_conclusions}\n"
            f"Visible log excerpt:\n{observation.actionlint_log_excerpt}",
        )
        self.assertTrue(
            any(
                "actionlint" in name.lower()
                for name in observation.observed_job_names + observation.observed_step_names
            ),
            "Human-style verification failed: the visible GitHub Actions job or step "
            "names for the successful run did not mention actionlint.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}",
        )
        self.assertEqual(
            observation.actionlint_step_conclusion,
            "success",
            "Human-style verification failed: the visible actionlint job or step "
            "did not show a successful status on the GitHub Actions run.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}\n"
            f"Observed step conclusion: {observation.actionlint_step_conclusion}\n"
            f"Visible log excerpt:\n{observation.actionlint_log_excerpt}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS256_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
