from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.config.pull_request_release_dry_run_config import (
    PullRequestReleaseDryRunConfig,
)
from testing.core.interfaces.pull_request_release_dry_run_probe import (
    PullRequestReleaseDryRunProbe,
)
from testing.tests.support.pull_request_release_dry_run_probe_factory import (
    create_pull_request_release_dry_run_probe,
)


class PullRequestReleaseDryRunTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = PullRequestReleaseDryRunConfig.from_file(
            self.repository_root / "testing/tests/TS-250/config.yaml"
        )
        self.probe: PullRequestReleaseDryRunProbe = (
            create_pull_request_release_dry_run_probe(self.repository_root)
        )

    def test_pull_request_to_main_exposes_successful_release_dry_run(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            self.config.repository,
            "Step 1 failed: TS-250 targeted the wrong repository.\n"
            f"Expected repository: {self.config.repository}\n"
            f"Observed repository: {observation.repository}",
        )
        self.assertEqual(
            observation.default_branch,
            self.config.base_branch,
            "Step 1 failed: TS-250 targeted the wrong default branch.\n"
            f"Expected default branch: {self.config.base_branch}\n"
            f"Observed default branch: {observation.default_branch}",
        )
        self.assertEqual(
            observation.workflow_path,
            self.config.workflow_path,
            "Step 1 failed: TS-250 targeted the wrong workflow file.\n"
            f"Expected workflow path: {self.config.workflow_path}\n"
            f"Observed workflow path: {observation.workflow_path}",
        )
        self.assertEqual(
            observation.workflow_name,
            self.config.workflow_name,
            "Step 1 failed: GitHub Actions returned an unexpected workflow name.\n"
            f"Expected workflow name: {self.config.workflow_name}\n"
            f"Observed workflow name: {observation.workflow_name}",
        )

        self.assertTrue(
            observation.workflow_declares_pull_request_trigger,
            "Step 2 failed: the live release workflow does not declare a contributor-"
            "visible pull request trigger (`pull_request` or `pull_request_target`), "
            "so opening a pull request to main cannot execute a release dry-run.\n"
            f"Workflow URL: {observation.workflow_html_url}\n"
            f"Observed workflow text:\n{observation.workflow_text}",
        )
        self.assertTrue(
            observation.workflow_declares_dry_run_step,
            "Step 2 failed: the live release workflow source does not visibly declare "
            "a dry-run step.\n"
            f"Workflow URL: {observation.workflow_html_url}\n"
            f"Expected markers: {self.config.dry_run_name_markers}\n"
            f"Observed workflow text:\n{observation.workflow_text}",
        )
        self.assertTrue(
            observation.workflow_declares_dry_run_command,
            "Step 2 failed: the live release workflow source does not include a "
            "dry-run command marker.\n"
            f"Workflow URL: {observation.workflow_html_url}\n"
            f"Expected command markers: {self.config.dry_run_command_markers}\n"
            f"Observed workflow text:\n{observation.workflow_text}",
        )

        self.assertTrue(
            observation.pull_request_number > 0,
            "Step 3 failed: TS-250 did not create a disposable pull request number.\n"
            f"Observed pull request URL: {observation.pull_request_url}",
        )
        self.assertIn(
            "/pull/",
            observation.pull_request_url,
            "Step 3 failed: TS-250 did not return a GitHub Pull Request URL.\n"
            f"Observed URL: {observation.pull_request_url}",
        )
        self.assertTrue(
            observation.pull_request_head_branch.startswith(self.config.branch_prefix),
            "Step 3 failed: the disposable pull request did not use the configured "
            "TS-250 branch prefix.\n"
            f"Expected prefix: {self.config.branch_prefix}\n"
            f"Observed branch: {observation.pull_request_head_branch}",
        )
        self.assertGreater(
            observation.observed_branch_run_count,
            0,
            "Step 3 failed: opening the disposable pull request did not produce any "
            "contributor-visible pull request workflow run to inspect.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed events: {observation.observed_branch_run_events}\n"
            f"Observed runs: {observation.observed_branch_run_names}",
        )
        self.assertEqual(
            observation.dry_run_run_path,
            self.config.workflow_path,
            "Step 3 failed: the disposable pull request did not expose a run for the "
            "release workflow under test.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed run paths: {observation.observed_branch_run_paths}",
        )
        self.assertIn(
            observation.dry_run_run_event,
            {"pull_request", "pull_request_target"},
            "Step 3 failed: the observed release workflow run was not triggered by "
            "a contributor-visible pull request event.\n"
            f"Run URL: {observation.dry_run_run_url}\n"
            f"Observed event: {observation.dry_run_run_event}",
        )
        self.assertEqual(
            observation.dry_run_run_conclusion,
            "success",
            "Step 3 failed: the release workflow run for the disposable pull request "
            "did not complete successfully.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Run URL: {observation.dry_run_run_url}\n"
            f"Run status: {observation.dry_run_run_status}\n"
            f"Run conclusion: {observation.dry_run_run_conclusion}",
        )
        self.assertIsNotNone(
            observation.dry_run_step_name,
            "Step 3 failed: the release workflow run did not expose a visible dry-run "
            "step on the pull request checks surface.\n"
            f"Run URL: {observation.dry_run_run_url}\n"
            f"Observed jobs: {observation.observed_job_names}\n"
            f"Observed steps: {observation.observed_step_names}",
        )
        self.assertEqual(
            observation.dry_run_step_conclusion,
            "success",
            "Human-style verification failed: the visible dry-run step on the pull "
            "request checks surface did not show a successful conclusion.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Run URL: {observation.dry_run_run_url}\n"
            f"Observed job: {observation.dry_run_job_name}\n"
            f"Observed step: {observation.dry_run_step_name}\n"
            f"Observed step status: {observation.dry_run_step_status}\n"
            f"Observed step conclusion: {observation.dry_run_step_conclusion}",
        )
        self.assertEqual(
            observation.pull_request_status_state,
            "success",
            "Human-style verification failed: GitHub did not report successful checks "
            "for the disposable pull request head commit.\n"
            f"Pull Request URL: {observation.pull_request_url}\n"
            f"Checks URL: {observation.pull_request_checks_url}\n"
            f"Observed status state: {observation.pull_request_status_state}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS250_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
