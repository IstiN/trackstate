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


class ActionlintWorkflowGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = ActionlintWorkflowGateConfig.from_file(
            self.repository_root / "testing/tests/TS-251/config.yaml"
        )
        self.probe: ActionlintWorkflowGateProbe = create_actionlint_workflow_gate_probe(
            self.repository_root
        )

    def test_push_invalid_release_workflow_is_blocked_by_actionlint(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-251 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.base_branch,
            "Step 1 failed: TS-251 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.base_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertTrue(
            observation.target_workflow_present_on_default_branch,
            "Step 1 failed: the live repository does not expose the release workflow "
            "that TS-251 needs to mutate.\n"
            f"Expected workflow path: {self.config.target_workflow_path}\n"
            f"Observed workflow paths: {observation.default_branch_workflow_paths}",
        )
        self.assertTrue(
            observation.pushed_branch.startswith(self.config.branch_prefix),
            "Step 2 failed: the disposable branch did not use the configured "
            "TS-251 prefix.\n"
            f"Expected prefix: {self.config.branch_prefix}\n"
            f"Observed branch: {observation.pushed_branch}",
        )
        self.assertTrue(
            observation.pushed_commit_sha,
            "Step 2 failed: the disposable branch push did not return a commit SHA.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Mutated workflow line: {observation.mutated_line_preview}",
        )
        self.assertTrue(
            observation.workflows_declaring_actionlint,
            "Step 3 failed: the live default branch does not expose any GitHub "
            "Actions workflow declaring actionlint, so invalid workflow files are "
            "not guarded before they can break release automation.\n"
            f"Repository: {observation.repository}\n"
            f"Default branch workflow paths: {observation.default_branch_workflow_paths}\n"
            f"Observed branch runs after push: {observation.observed_branch_run_names}\n"
            f"Actions page: {observation.branch_actions_page_url}",
        )
        self.assertGreater(
            observation.observed_branch_run_count,
            0,
            "Step 3 failed: pushing the invalid workflow branch did not produce any "
            "GitHub Actions pipeline run to inspect.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Actions page: {observation.branch_actions_page_url}\n"
            f"Workflow paths declaring actionlint on default branch: "
            f"{observation.workflows_declaring_actionlint}",
        )
        self.assertIsNotNone(
            observation.actionlint_run_url,
            "Step 3 failed: GitHub Actions did not expose an actionlint validation "
            "run for the pushed invalid workflow branch.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Observed run names: {observation.observed_branch_run_names}\n"
            f"Observed run paths: {observation.observed_branch_run_paths}\n"
            f"Observed run URLs: {observation.observed_branch_run_urls}\n"
            f"Actions page: {observation.branch_actions_page_url}",
        )
        assert observation.actionlint_run_url is not None
        self.assertIn(
            "/actions/runs/",
            observation.actionlint_run_url,
            "Step 3 failed: the actionlint validation did not expose a GitHub "
            "Actions run URL.\n"
            f"Observed URL: {observation.actionlint_run_url}",
        )
        self.assertEqual(
            observation.actionlint_run_conclusion,
            "failure",
            "Step 3 failed: the actionlint pipeline did not fail after pushing the "
            "invalid release workflow.\n"
            f"Branch: {observation.pushed_branch}\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Run status: {observation.actionlint_run_status}\n"
            f"Run conclusion: {observation.actionlint_run_conclusion}",
        )
        self.assertTrue(
            any(
                "actionlint" in name.lower()
                for name in observation.observed_job_names + observation.observed_step_names
            ),
            "Human-style verification failed: the visible GitHub Actions job or step "
            "names for the failing run did not mention actionlint.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}",
        )
        self.assertEqual(
            observation.actionlint_step_conclusion,
            "failure",
            "Human-style verification failed: the visible actionlint step did not "
            "show a failing status on the GitHub Actions run.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}\n"
            f"Observed step conclusion: {observation.actionlint_step_conclusion}",
        )
        self.assertIsNotNone(
            observation.actionlint_log_excerpt,
            "Human-style verification failed: the actionlint run did not expose any "
            "failed log output that a contributor could use to understand the "
            "workflow problem.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}",
        )
        assert observation.actionlint_log_excerpt is not None
        log_excerpt = observation.actionlint_log_excerpt
        lower_log_excerpt = log_excerpt.lower()
        target_file_name = Path(self.config.target_workflow_path).name.lower()
        self.assertTrue(
            (
                self.config.target_workflow_path.lower() in lower_log_excerpt
                or target_file_name in lower_log_excerpt
            )
            and re.search(
                r"(syntax|trigger|yaml|parse|invalid|unexpected|schema|error)",
                log_excerpt,
                flags=re.IGNORECASE,
            ),
            "Human-style verification failed: the visible actionlint failure did not "
            "identify the broken workflow syntax or trigger configuration.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Target workflow: {self.config.target_workflow_path}\n"
            f"Observed log excerpt:\n{observation.actionlint_log_excerpt}",
        )
        self.assertNotIn(
            "unable to resolve action",
            lower_log_excerpt,
            "Human-style verification failed: the actionlint workflow failed during "
            "its own setup instead of reporting the invalid workflow syntax or "
            "trigger error.\n"
            f"Run URL: {observation.actionlint_run_url}\n"
            f"Observed log excerpt:\n{observation.actionlint_log_excerpt}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS251_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
