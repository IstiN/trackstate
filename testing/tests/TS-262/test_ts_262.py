from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.actionlint_non_workflow_pull_request_gate_config import (
    ActionlintNonWorkflowPullRequestGateConfig,
)
from testing.core.interfaces.actionlint_non_workflow_pull_request_gate_probe import (
    ActionlintNonWorkflowPullRequestGateObservation,
    ActionlintNonWorkflowPullRequestGateProbe,
)
from testing.tests.support.actionlint_non_workflow_pull_request_gate_probe_factory import (
    create_actionlint_non_workflow_pull_request_gate_probe,
)


class ActionlintNonWorkflowPullRequestGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ActionlintNonWorkflowPullRequestGateConfig.from_file(
            self.repository_root / "testing/tests/TS-262/config.yaml"
        )
        self.probe: ActionlintNonWorkflowPullRequestGateProbe = (
            create_actionlint_non_workflow_pull_request_gate_probe(self.repository_root)
        )

    def test_non_workflow_pull_request_is_not_blocked_by_actionlint(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-262 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.base_branch,
            "Step 1 failed: TS-262 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.base_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertTrue(
            observation.probe_file_present_on_default_branch,
            "Step 2 failed: the live repository does not expose the non-workflow "
            "probe file TS-262 needs to edit.\n"
            f"Expected file path: {self.config.probe_file_path}",
        )
        self.assertTrue(
            observation.actionlint_workflow_present_on_default_branch,
            "Step 2 failed: the live repository does not expose the actionlint "
            "workflow TS-262 expects to inspect.\n"
            f"Expected workflow path: {self.config.actionlint_workflow_path}",
        )
        self.assertTrue(
            observation.actionlint_workflow_declares_pull_request_trigger,
            "Step 2 failed: the live actionlint workflow no longer declares a "
            "pull_request trigger, so TS-262 cannot verify non-workflow PR behavior.\n"
            f"Workflow path: {observation.actionlint_workflow_path}",
        )
        self.assertTrue(
            observation.actionlint_workflow_uses_expected_paths_filter,
            "Step 2 failed: the live actionlint workflow no longer scopes itself to "
            "workflow file paths, so TS-262 cannot prove that a README-only PR should "
            "avoid actionlint gating.\n"
            f"Expected path filter: {self.config.expected_paths_filter}\n"
            f"Workflow path: {observation.actionlint_workflow_path}",
        )
        self.assertTrue(
            observation.workflows_declaring_actionlint,
            "Step 2 failed: the live default branch does not expose any GitHub "
            "Actions workflow declaring actionlint.\n"
            f"Observed workflow paths: {observation.workflows_declaring_actionlint}",
        )

        self.assertGreater(
            observation.pull_request_number,
            0,
            "Step 3 failed: TS-262 did not create a disposable pull request.\n"
            f"Observed pull request URL: {observation.pull_request_url}",
        )
        self.assertIn(
            "/pull/",
            observation.pull_request_url,
            "Step 3 failed: TS-262 did not return a GitHub Pull Request URL.\n"
            f"Observed URL: {observation.pull_request_url}",
        )
        self.assertTrue(
            observation.pull_request_head_branch.startswith(self.config.branch_prefix),
            "Step 3 failed: the disposable pull request did not use the configured "
            "TS-262 branch prefix.\n"
            f"Expected prefix: {self.config.branch_prefix}\n"
            f"Observed branch: {observation.pull_request_head_branch}",
        )
        self.assertIn(
            "TS-262 probe",
            observation.pull_request_probe_marker,
            "Step 3 failed: TS-262 did not append the expected marker to the README "
            "probe change.\n"
            f"Observed marker: {observation.pull_request_probe_marker}",
        )

        self._assert_actionlint_gate(observation)

        self.assertEqual(
            observation.pull_request_mergeable,
            "MERGEABLE",
            "Step 4 failed: the disposable README-only pull request was not mergeable "
            "from the contributor-visible PR surface.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed mergeable: {observation.pull_request_mergeable}\n"
            f"Observed mergeStateStatus: {observation.pull_request_merge_state_status}\n"
            f"Observed status checks: {observation.observed_status_check_names}",
        )
        self.assertIn(
            observation.pull_request_merge_state_status,
            {"CLEAN", "HAS_HOOKS", "UNSTABLE"},
            "Human-style verification failed for Step 4: the GitHub PR surface did "
            "not keep the merge button in an enabled-style state for the README-only "
            "change.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed mergeStateStatus: {observation.pull_request_merge_state_status}\n"
            f"Observed mergeable: {observation.pull_request_mergeable}\n"
            f"Observed status checks: {observation.observed_status_check_names}\n"
            f"Observed workflow checks: {observation.observed_status_check_workflow_names}",
        )

    def _assert_actionlint_gate(
        self,
        observation: ActionlintNonWorkflowPullRequestGateObservation,
    ) -> None:
        failure_like_states = {"failure", "cancelled", "timed_out", "action_required"}
        if observation.actionlint_status_check_name is None:
            self.assertIsNone(
                observation.actionlint_run_name,
                "Step 4 failed: GitHub Actions exposed an actionlint run for a "
                "README-only pull request even though the actionlint workflow is "
                "scoped to workflow file paths.\n"
                f"Pull Request URL: {observation.pull_request_url}\n"
                f"Observed run name: {observation.actionlint_run_name}\n"
                f"Observed run path: {observation.actionlint_run_path}\n"
                f"Observed run URL: {observation.actionlint_run_url}\n"
                f"Observed branch runs: {observation.observed_branch_run_names}\n"
                f"Observed branch run paths: {observation.observed_branch_run_paths}",
            )
            return

        self.assertNotIn(
            observation.actionlint_status_check_conclusion,
            failure_like_states,
            "Step 4 failed: the PR checks surface showed actionlint as a failing gate "
            "for a README-only pull request.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed actionlint check: {observation.actionlint_status_check_name}\n"
            f"Observed workflow: {observation.actionlint_status_check_workflow_name}\n"
            f"Observed status: {observation.actionlint_status_check_status}\n"
            f"Observed conclusion: {observation.actionlint_status_check_conclusion}",
        )
        if observation.actionlint_run_name is not None:
            self.assertNotIn(
                observation.actionlint_run_conclusion,
                failure_like_states,
                "Human-style verification failed for Step 4: the visible GitHub "
                "Actions run for actionlint finished in a failing state for the "
                "README-only pull request.\n"
                f"Pull Request URL: {observation.pull_request_url}\n"
                f"Run URL: {observation.actionlint_run_url}\n"
                f"Observed run conclusion: {observation.actionlint_run_conclusion}\n"
                f"Observed jobs: {observation.observed_job_names}\n"
                f"Observed steps: {observation.observed_step_names}\n"
                f"Observed log excerpt:\n{observation.actionlint_log_excerpt}",
            )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS262_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
