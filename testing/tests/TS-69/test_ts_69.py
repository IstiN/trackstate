from __future__ import annotations

import json
import os
from pathlib import Path
import unittest

from testing.core.interfaces.github_pages_workflow_probe import (
    GitHubPagesWorkflowProbe,
)
from testing.tests.support.github_pages_workflow_probe_factory import (
    create_github_pages_workflow_probe,
)


class InstallUpdateTrackStateWorkflowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.probe: GitHubPagesWorkflowProbe = create_github_pages_workflow_probe(
            self.repository_root
        )

    def test_workflow_builds_pages_artifact_without_committing_web_assets(self) -> None:
        observation = self.probe.validate()
        self._write_result_if_requested(observation.to_dict())

        self.assertEqual(
            observation.repository,
            observation.requested_repository,
            (
                "Step 1 failed: the validation ran against "
                f"{observation.repository}, but TS-69 requires the requested fork "
                f"{observation.requested_repository} to be validated end-to-end."
            ),
        )
        self.assertEqual(
            observation.pages_url,
            observation.expected_pages_url,
            (
                "Step 5 failed: the deployed GitHub Pages URL did not belong to the "
                "requested repository. "
                f"Expected {observation.expected_pages_url}, got {observation.pages_url}."
            ),
        )
        self.assertEqual(
            observation.workflow_run_conclusion,
            "success",
            (
                "Step 4 failed: the Install / Update TrackState workflow did not "
                f"finish successfully for {observation.repository}. "
                f"Run: {observation.workflow_run_url}"
            ),
        )
        self.assertEqual(
            observation.pages_build_type,
            "workflow",
            "Step 2 failed: GitHub Pages was not configured to use GitHub Actions.",
        )
        self.assertEqual(
            observation.html_base_href,
            f"/{observation.requested_repository.split('/', 1)[1]}/",
            (
                "Step 5 failed: the deployed app shell did not use the expected "
                f"base href for {observation.requested_repository}. "
                f"Actual base href: {observation.html_base_href!r}"
            ),
        )
        self.assertEqual(
            observation.branch_sha_after,
            observation.branch_sha_before,
            (
                "Step 4 failed: the workflow changed the repository branch head, "
                "which indicates generated files were committed back to the branch."
            ),
        )
        self.assertEqual(
            observation.build_assets_committed_to_branch,
            [],
            (
                "Step 4 failed: generated Flutter web assets were committed to the "
                f"repository branch: {observation.build_assets_committed_to_branch}"
            ),
        )
        self.assertEqual(
            observation.missing_required_steps,
            [],
            (
                "Step 4 failed: the workflow did not expose all required build and "
                f"deployment steps. Missing: {observation.missing_required_steps}"
            ),
        )
        self.assertEqual(
            observation.failed_required_steps,
            [],
            (
                "Step 4 failed: one or more required workflow steps did not "
                f"succeed: {observation.failed_required_steps}"
            ),
        )
        self.assertEqual(
            observation.html_title,
            "TrackState.AI",
            (
                "Step 5 failed: the deployed Pages URL did not serve the TrackState "
                f"shell title. Actual title: {observation.html_title!r}"
            ),
        )
        self.assertTrue(
            observation.html_contains_bootstrap_script,
            (
                "Step 5 failed: the deployed Pages URL did not return the Flutter "
                "bootstrap script tag, so the app shell did not look deployable."
            ),
        )
        self.assertTrue(
            observation.bootstrap_asset_mentions_main_dart_js,
            (
                "Step 5 failed: flutter_bootstrap.js was reachable but did not "
                "reference main.dart.js, so the deployed app bundle did not look "
                "complete."
            ),
        )

    def _write_result_if_requested(self, payload: dict[str, object]) -> None:
        result_path = os.environ.get("TS69_RESULT_PATH")
        if not result_path:
            return

        destination = Path(result_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    unittest.main()
