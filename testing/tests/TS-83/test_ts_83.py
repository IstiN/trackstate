from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.interfaces.release_source_workflow_probe import (
    ReleaseSourceWorkflowProbe,
)
from testing.tests.support.release_source_workflow_probe_factory import (
    create_release_source_workflow_probe,
)


class ReleaseSourceWorkflowInclusionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: ReleaseSourceWorkflowProbe = create_release_source_workflow_probe(
            self.repository_root
        )

    def test_latest_release_or_tag_includes_install_update_workflow(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertTrue(
            observation.default_branch_has_workflow,
            "Precondition failed: the default branch does not currently contain "
            f"{observation.workflow_path}, so TS-83 cannot verify release-source inheritance.\n"
            f"Repository: {observation.repository}\n"
            f"Default branch: {observation.default_branch}",
        )

        self.assertTrue(
            observation.releases or observation.tags,
            "Step 2 failed: GitHub does not currently expose any releases or tags "
            f"for {observation.repository}, so a user cannot select a stable source "
            f"snapshot and confirm {observation.workflow_path} is included there.\n"
            f"Observed releases: {observation.releases}\n"
            f"Observed tags: {observation.tags}\n"
            f"Releases page: {observation.releases_page_url}\n"
            f"Tags page: {observation.tags_page_url}\n"
            f"Control check: {observation.workflow_path} exists on {observation.default_branch} = "
            f"{observation.default_branch_has_workflow}",
        )

        selected_ref = observation.selected_ref
        self.assertIsNotNone(
            selected_ref,
            "Step 3 failed: the repository did not yield a latest release or tag "
            "after the releases/tags lookup completed.",
        )
        assert selected_ref is not None

        self.assertTrue(
            observation.selected_ref_has_workflow,
            "Step 5 failed: the latest stable source snapshot does not include the "
            f"required workflow file.\nRepository: {observation.repository}\n"
            f"Selected {selected_ref.kind}: {selected_ref.name}\n"
            f"Selected ref observed at: {selected_ref.observed_at}\n"
            f"Selected ref URL: {selected_ref.html_url}\n"
            f"Expected workflow path: {observation.workflow_path}",
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS83_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
