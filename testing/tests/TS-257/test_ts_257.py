from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.actionlint_required_pull_request_gate_config import (
    ActionlintRequiredPullRequestGateConfig,
)
from testing.core.interfaces.actionlint_required_pull_request_gate_probe import (
    ActionlintRequiredPullRequestGateProbe,
)
from testing.tests.support.actionlint_required_pull_request_gate_probe_factory import (
    create_actionlint_required_pull_request_gate_probe,
)


class ActionlintRequiredPullRequestGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ActionlintRequiredPullRequestGateConfig.from_file(
            self.repository_root / "testing/tests/TS-257/config.yaml"
        )
        self.probe: ActionlintRequiredPullRequestGateProbe = (
            create_actionlint_required_pull_request_gate_probe(self.repository_root)
        )

    def test_pull_request_with_workflow_errors_is_blocked_by_required_actionlint(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-257 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.base_branch,
            "Step 1 failed: TS-257 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.base_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertTrue(
            observation.target_workflow_present_on_default_branch,
            "Step 1 failed: the live repository does not expose the release workflow "
            "that TS-257 needs to mutate.\n"
            f"Expected workflow path: {self.config.target_workflow_path}\n"
            f"Observed workflow paths: {observation.default_branch_workflow_paths}",
        )
        self.assertTrue(
            observation.workflows_declaring_actionlint,
            "Step 2 failed: the live default branch does not expose any GitHub "
            "Actions workflow declaring actionlint, so TS-257 cannot verify a "
            "required status check.\n"
            f"Repository: {observation.repository}\n"
            f"Default branch workflow paths: {observation.default_branch_workflow_paths}",
        )
        self.assertTrue(
            observation.repository_declares_actionlint_required_check,
            "Step 2 failed: the repository does not currently declare actionlint as a "
            "required status check for the main branch.\n"
            f"Required rule descriptions: {observation.required_rule_descriptions}\n"
            f"Required check contexts: {observation.required_check_contexts}\n"
            f"Required workflow paths: {observation.required_check_workflow_paths}\n"
            f"Required workflow names: {observation.required_check_workflow_names}",
        )

        self.assertGreater(
            observation.pull_request_number,
            0,
            "Step 3 failed: TS-257 did not create a disposable pull request number.\n"
            f"Observed pull request URL: {observation.pull_request_url}",
        )
        self.assertIn(
            "/pull/",
            observation.pull_request_url,
            "Step 3 failed: TS-257 did not return a GitHub Pull Request URL.\n"
            f"Observed URL: {observation.pull_request_url}",
        )
        self.assertTrue(
            observation.pull_request_head_branch.startswith(self.config.branch_prefix),
            "Step 3 failed: the disposable pull request did not use the configured "
            "TS-257 branch prefix.\n"
            f"Expected prefix: {self.config.branch_prefix}\n"
            f"Observed branch: {observation.pull_request_head_branch}",
        )
        self.assertGreater(
            observation.observed_branch_run_count,
            0,
            "Step 3 failed: opening the disposable pull request did not produce any "
            "contributor-visible workflow run to inspect.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed run names: {observation.observed_branch_run_names}",
        )
        self.assertIsNotNone(
            observation.actionlint_run_url,
            "Step 3 failed: GitHub Actions did not expose an actionlint workflow run "
            "for the disposable pull request.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Observed run names: {observation.observed_branch_run_names}\n"
            f"Observed run paths: {observation.observed_branch_run_paths}",
        )
        self.assertEqual(
            observation.actionlint_run_conclusion,
            "failure",
            "Step 3 failed: the actionlint workflow run did not fail for the invalid "
            "workflow pull request.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Run status: {observation.actionlint_run_status}\n"
            f"Run conclusion: {observation.actionlint_run_conclusion}",
        )
        self.assertEqual(
            observation.actionlint_step_conclusion,
            "failure",
            "Human-style verification failed for Step 3: the visible actionlint step "
            "did not show a failing result in the GitHub Actions run details.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}\n"
            f"Observed step conclusion: {observation.actionlint_step_conclusion}",
        )

        self.assertIsNotNone(
            observation.actionlint_status_check_name,
            "Step 4 failed: the pull request checks surface did not expose an "
            "actionlint status check.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed status checks: {observation.observed_status_check_names}\n"
            f"Observed workflow names: "
            f"{observation.observed_status_check_workflow_names}",
        )
        self.assertEqual(
            observation.actionlint_status_check_conclusion,
            "failure",
            "Step 4 failed: the pull request checks surface did not show the "
            "actionlint status check as failed.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed status check name: {observation.actionlint_status_check_name}\n"
            f"Observed status check workflow: "
            f"{observation.actionlint_status_check_workflow_name}\n"
            f"Observed status check status: {observation.actionlint_status_check_status}\n"
            f"Observed status check conclusion: "
            f"{observation.actionlint_status_check_conclusion}",
        )
        self.assertEqual(
            observation.pull_request_status_state,
            "failure",
            "Step 4 failed: GitHub did not report failing status checks for the "
            "disposable pull request head commit.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Observed status state: {observation.pull_request_status_state}",
        )
        self.assertEqual(
            observation.pull_request_mergeable_state,
            "blocked",
            "Step 4 failed: GitHub did not report the disposable pull request as "
            "blocked after the failed actionlint check.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Observed mergeable state: {observation.pull_request_mergeable_state}\n"
            f"Observed merge state status: "
            f"{observation.pull_request_merge_state_status}\n"
            f"Observed status state: {observation.pull_request_status_state}",
        )
        self.assertEqual(
            observation.pull_request_merge_state_status,
            "BLOCKED",
            "Human-style verification failed for Step 4: the disposable pull request "
            "did not expose a merge-blocked state in GitHub's pull request surface.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed mergeStateStatus: "
            f"{observation.pull_request_merge_state_status}\n"
            f"Observed mergeable state: {observation.pull_request_mergeable_state}\n"
            f"Observed status checks: {observation.observed_status_check_names}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS257_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
