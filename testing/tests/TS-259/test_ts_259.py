from __future__ import annotations

from pathlib import Path
import unittest

import yaml


class ActionlintWorkflowReferenceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.workflow_path = (
            self.repository_root / "trackstate-setup/.github/workflows/actionlint.yml"
        )
        self.workflow = yaml.safe_load(self.workflow_path.read_text(encoding="utf-8"))

    def test_actionlint_workflow_uses_a_published_release_tag(self) -> None:
        steps = self.workflow["jobs"]["actionlint"]["steps"]
        action_step = next(
            step for step in steps if step.get("name") == "Run actionlint"
        )
        action_ref = action_step.get("uses")

        self.assertEqual(
            action_ref,
            "rhysd/actionlint@v1.7.12",
            "The actionlint workflow must pin `rhysd/actionlint` to a published "
            "release tag so GitHub Actions can resolve the action before linting "
            "workflow files.",
        )


if __name__ == "__main__":
    unittest.main()
