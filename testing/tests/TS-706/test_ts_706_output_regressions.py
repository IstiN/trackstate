from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "testing/tests/TS-706/test_ts_706.py"
MODULE_SPEC = importlib.util.spec_from_file_location("ts_706_module", MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Could not load TS-706 module from {MODULE_PATH}")
ts_706 = importlib.util.module_from_spec(MODULE_SPEC)
MODULE_SPEC.loader.exec_module(ts_706)


class TS706OutputRegressionTest(unittest.TestCase):
    def test_precondition_failures_write_failed_machine_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs_dir = Path(temp_dir)
            original_paths = {
                "OUTPUTS_DIR": ts_706.OUTPUTS_DIR,
                "JIRA_COMMENT_PATH": ts_706.JIRA_COMMENT_PATH,
                "PR_BODY_PATH": ts_706.PR_BODY_PATH,
                "RESPONSE_PATH": ts_706.RESPONSE_PATH,
                "RESULT_PATH": ts_706.RESULT_PATH,
                "REVIEW_REPLIES_PATH": ts_706.REVIEW_REPLIES_PATH,
                "BUG_DESCRIPTION_PATH": ts_706.BUG_DESCRIPTION_PATH,
            }
            try:
                ts_706.OUTPUTS_DIR = outputs_dir
                ts_706.JIRA_COMMENT_PATH = outputs_dir / "jira_comment.md"
                ts_706.PR_BODY_PATH = outputs_dir / "pr_body.md"
                ts_706.RESPONSE_PATH = outputs_dir / "response.md"
                ts_706.RESULT_PATH = outputs_dir / "test_automation_result.json"
                ts_706.REVIEW_REPLIES_PATH = outputs_dir / "review_replies.json"
                ts_706.BUG_DESCRIPTION_PATH = outputs_dir / "bug_description.md"

                outputs_dir.mkdir(parents=True, exist_ok=True)
                ts_706._write_failure_outputs(
                    {
                        "repository": "IstiN/trackstate",
                        "default_branch": "main",
                        "error": (
                            "Precondition failed: TS-706 could not reproduce the no-runner "
                            "failure condition because a matching macOS release runner was online."
                        ),
                        "precondition_failure": True,
                        "product_failure": False,
                    }
                )

                result_payload = json.loads(
                    ts_706.RESULT_PATH.read_text(encoding="utf-8")
                )
                self.assertEqual(result_payload["status"], "failed")
                self.assertEqual(result_payload["passed"], 0)
                self.assertEqual(result_payload["failed"], 1)
                self.assertEqual(result_payload["skipped"], 0)
                self.assertIn("Precondition failed:", result_payload["error"])
                self.assertFalse(ts_706.BUG_DESCRIPTION_PATH.exists())
            finally:
                for name, value in original_paths.items():
                    setattr(ts_706, name, value)

    def test_precondition_warning_requires_stable_signal_before_product_failure(self) -> None:
        config = ts_706.GitHubActionsPreflightGateConfig(
            repository="IstiN/trackstate",
            default_branch="main",
            workflow_name="Apple Release Builds",
            workflow_file="build-native.yml",
            workflow_path=".github/workflows/build-native.yml",
            preflight_job_name="Verify macOS runner availability",
            downstream_job_name="Build macOS desktop and CLI artifacts",
            expected_preflight_runner="ubuntu-latest",
            expected_runner_labels=[
                "self-hosted",
                "macOS",
                "trackstate-release",
                "ARM64",
            ],
            expected_failure_markers=["No runner registered for", "none are online"],
            recent_runs_limit=20,
            poll_interval_seconds=5,
            run_timeout_seconds=240,
            ui_timeout_seconds=60,
        )
        original_open_actions_page = ts_706._open_actions_page
        warning_text = (
            "Skipping macOS runner availability preflight because the token cannot read "
            "repository runners. The build job will still target the required self-hosted "
            "labels and GitHub Actions will queue it until a matching runner is available."
        )
        base_result = {
            "repository": "IstiN/trackstate",
            "default_branch": "main",
            "workflow_name": "Apple Release Builds",
            "tag_name": "v98.test",
            "head_sha": "head-sha",
            "error": "Precondition failed: queued run observed",
            "precondition_failure": True,
            "product_failure": False,
            "steps": [],
            "human_verification": [],
            "run": {
                "id": 91,
                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91",
                "status": "in_progress",
            },
            "preflight_job": {
                "name": "Verify macOS runner availability",
                "conclusion": "success",
                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91/job/101",
            },
            "downstream_job": {
                "name": "Build macOS desktop and CLI artifacts",
                "status": "queued",
                "conclusion": None,
                "html_url": "https://github.com/IstiN/trackstate/actions/runs/91/job/202",
            },
        }
        observations = iter(
            [
                ts_706.GitHubActionsPageObservation(
                    url="https://github.com/IstiN/trackstate/actions/runs/91",
                    matched_text="Verify macOS runner availability",
                    body_text=warning_text,
                    screenshot_path="/tmp/run.png",
                ),
                ts_706.GitHubActionsPageObservation(
                    url="https://github.com/IstiN/trackstate/actions/runs/91/job/101",
                    matched_text="success",
                    body_text=warning_text,
                    screenshot_path="/tmp/job.png",
                ),
                ts_706.GitHubActionsPageObservation(
                    url="https://github.com/IstiN/trackstate/actions/runs/91",
                    matched_text="Verify macOS runner availability",
                    body_text=warning_text,
                    screenshot_path="/tmp/run.png",
                ),
                ts_706.GitHubActionsPageObservation(
                    url="https://github.com/IstiN/trackstate/actions/runs/91/job/101",
                    matched_text="success",
                    body_text=warning_text,
                    screenshot_path="/tmp/job.png",
                ),
            ]
        )
        try:
            ts_706._open_actions_page = lambda **_: next(observations)

            transient_result = deepcopy(base_result)
            ts_706._collect_precondition_run_evidence(transient_result, config)

            self.assertTrue(transient_result["precondition_failure"])
            self.assertFalse(transient_result["product_failure"])
            self.assertIn("Precondition failed:", transient_result["error"])
            self.assertEqual(transient_result["steps"][-1]["status"], "blocked")

            stable_result = deepcopy(base_result)
            stable_result["stable_runner_mismatch"] = True
            ts_706._collect_precondition_run_evidence(stable_result, config)

            self.assertFalse(stable_result["precondition_failure"])
            self.assertTrue(stable_result["product_failure"])
            self.assertIn("Step 4 failed", stable_result["error"])
            self.assertEqual(stable_result["steps"][-1]["status"], "failed")
        finally:
            ts_706._open_actions_page = original_open_actions_page


if __name__ == "__main__":
    unittest.main()
