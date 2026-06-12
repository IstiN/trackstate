from __future__ import annotations

from pathlib import Path
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github/workflows/build-macos-reusable.yml"


class BuildMacosReusableWorkflowRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
        if not isinstance(workflow, dict):
            self.fail(
                f"Expected {WORKFLOW_PATH} to decode to a mapping, "
                f"got {type(workflow).__name__}."
            )
        self.workflow = workflow

    def test_verify_runner_step_fails_fast_on_label_mismatch(self) -> None:
        verify_runner_steps = self.workflow["jobs"]["verify-runner"]["steps"]
        runner_check_step = next(
            step
            for step in verify_runner_steps
            if isinstance(step, dict)
            and step.get("name") == "Check configured macOS runner labels"
        )
        script = runner_check_step["with"]["script"]

        self.assertRegex(
            script,
            r"if \(matchingRunners\.length === 0\)\s*\{\s*core\.setFailed\(",
        )
        self.assertIn(
            "No online runners found with required labels",
            script,
        )
        self.assertNotIn(
            "core.warning(",
            script,
        )
        self.assertRegex(
            script,
            r"if \(onlineRunners\.length === 0\)\s*\{\s*core\.setFailed\(",
        )
        self.assertIn(
            "Runner labels ${runnerLabels} are registered, but none are online.",
            script,
        )
        self.assertIn(
            "No online runners found with required labels ${runnerLabels} for ${owner}/${repo}.",
            script,
        )


if __name__ == "__main__":
    unittest.main()
