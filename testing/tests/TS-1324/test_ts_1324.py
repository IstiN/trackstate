from __future__ import annotations

import json
import os
from pathlib import Path
import re
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


class ActionlintTimeoutMinutesGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config_path = self.repository_root / "testing/tests/TS-1324/config.yaml"
        self.config = ActionlintWorkflowGateConfig.from_file(self.config_path)
        self.probe: ActionlintWorkflowGateProbe = create_actionlint_workflow_gate_probe(
            self.repository_root,
            config_path=self.config_path,
        )

    def test_actionlint_rejects_workflows_missing_timeout_minutes(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-1324 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.base_branch,
            "Step 1 failed: TS-1324 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.base_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertTrue(
            observation.target_workflow_present_on_default_branch,
            "Step 1 failed: the live repository does not expose the actionlint "
            "workflow that TS-1324 needs to exercise.\n"
            f"Expected workflow path: {self.config.target_workflow_path}\n"
            f"Observed workflow paths: {observation.default_branch_workflow_paths}",
        )
        self.assertTrue(
            observation.workflows_declaring_actionlint,
            "Step 1 failed: the live default branch does not expose any GitHub "
            "Actions workflow declaring actionlint, so TS-1324 cannot inspect the "
            "CI gate.\n"
            f"Repository: {observation.repository}\n"
            f"Default branch workflow paths: {observation.default_branch_workflow_paths}",
        )
        self.assertTrue(
            observation.pushed_branch.startswith(self.config.branch_prefix),
            "Step 2 failed: the disposable branch did not use the configured "
            "TS-1324 prefix.\n"
            f"Expected prefix: {self.config.branch_prefix}\n"
            f"Observed branch: {observation.pushed_branch}",
        )
        self.assertTrue(
            observation.pushed_commit_sha,
            "Step 2 failed: the disposable branch push did not return a commit SHA.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Workflow preview: {observation.mutated_line_preview}",
        )
        self.assertIsNotNone(
            observation.actionlint_run_url,
            "Step 3 failed: GitHub Actions did not expose an actionlint run for the "
            "changed workflow file.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Observed run names: {observation.observed_branch_run_names}\n"
            f"Observed run paths: {observation.observed_branch_run_paths}",
        )
        self.assertEqual(
            observation.actionlint_run_conclusion,
            "failure",
            "Step 3 failed: the actionlint workflow did not reject a workflow job "
            "missing timeout-minutes.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Run status: {observation.actionlint_run_status}\n"
            f"Run conclusion: {observation.actionlint_run_conclusion}\n"
            f"Observed branch runs: {observation.observed_branch_run_names}\n"
            f"Observed branch conclusions: {observation.observed_branch_run_conclusions}",
        )
        self.assertTrue(
            any(
                "actionlint" in name.lower()
                for name in observation.observed_job_names + observation.observed_step_names
            ),
            "Human-style verification failed: the visible GitHub Actions job or step "
            "names for the run did not mention actionlint.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}",
        )
        self.assertEqual(
            observation.actionlint_step_conclusion,
            "failure",
            "Human-style verification failed: the visible actionlint job or step did "
            "not show a failing status on the GitHub Actions run.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}\n"
            f"Observed step conclusion: {observation.actionlint_step_conclusion}",
        )
        self.assertIsNotNone(
            observation.actionlint_log_excerpt,
            "Step 4 failed: TS-1324 could not read the visible actionlint log.\n"
            f"Run URL: {observation.actionlint_run_url}",
        )
        assert observation.actionlint_log_excerpt is not None
        self.assertIn(
            self.config.target_workflow_path,
            observation.actionlint_log_excerpt,
            "Step 4 failed: the visible actionlint log did not mention the changed "
            "workflow file.\n"
            f"Expected file path: {self.config.target_workflow_path}\n"
            f"Observed log excerpt:\n{observation.actionlint_log_excerpt}",
        )
        self.assertIn(
            "timeout-minutes",
            observation.actionlint_log_excerpt.lower(),
            "Step 4 failed: the visible actionlint log did not mention timeout-minutes "
            "at all.\n"
            f"Observed log excerpt:\n{observation.actionlint_log_excerpt}",
        )
        self.assertRegex(
            observation.actionlint_log_excerpt,
            re.compile(r"(timeout-minutes|required|must)", re.IGNORECASE),
            "Step 4 failed: the visible actionlint log did not surface a timeout-minutes "
            "policy error.\n"
            f"Observed log excerpt:\n{observation.actionlint_log_excerpt}",
        )
        self.assertTrue(
            observation.cleanup_deleted_branch,
            "Teardown failed: the disposable branch was not deleted after the probe.\n"
            f"Branch: {observation.pushed_branch}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS1324_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
