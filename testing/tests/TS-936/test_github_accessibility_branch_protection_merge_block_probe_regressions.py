from __future__ import annotations

import json
import unittest

from testing.components.services.github_accessibility_branch_protection_merge_block_probe import (
    GitHubAccessibilityBranchProtectionMergeBlockProbeService,
)
from testing.core.config.github_accessibility_pull_request_gate_config import (
    GitHubAccessibilityPullRequestGateConfig,
)


class _FakeGitHubApiClient:
    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses

    def request_text(
        self,
        *,
        endpoint: str,
        method: str = "GET",
        field_args=None,
        stdin_json=None,
    ) -> str:
        del field_args, stdin_json
        if method != "GET":
            raise AssertionError(f"Unexpected method for regression probe: {method}")
        if endpoint not in self._responses:
            raise AssertionError(f"Unexpected endpoint: {endpoint}")
        response = self._responses[endpoint]
        if isinstance(response, str):
            return response
        return json.dumps(response)


class _StubProbeService(GitHubAccessibilityBranchProtectionMergeBlockProbeService):
    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        del workflow_id
        return {
            "pull_request_number": 123,
            "pull_request_url": "https://github.com/IstiN/trackstate/pull/123",
            "pull_request_checks_url": "https://github.com/IstiN/trackstate/pull/123/checks",
            "pull_request_head_branch": "ts936-a11y-merge-block-20260522000000",
            "pull_request_head_sha": "abc123",
            "pull_request_probe_path": "lib/ts936_probe_surface.dart",
            "probe_render_host_path": "lib/main.dart",
            "probe_rendered_in_application": True,
            "pull_request_file_paths": ["lib/main.dart", "lib/ts936_probe_surface.dart"],
            "pull_request_state": "open",
            "pull_request_mergeable_state": "blocked",
            "pull_request_status_state": "failure",
            "pull_request_mergeable": "MERGEABLE",
            "pull_request_merge_state_status": "BLOCKED",
            "latest_pull_request_run_id": 456,
            "latest_pull_request_run_url": "https://github.com/IstiN/trackstate/actions/runs/456",
            "latest_pull_request_run_event": "pull_request",
            "latest_pull_request_run_status": "completed",
            "latest_pull_request_run_conclusion": "failure",
            "observed_branch_run_names": ["Flutter Required Checks"],
            "observed_branch_run_urls": ["https://github.com/IstiN/trackstate/actions/runs/456"],
            "observed_branch_run_statuses": ["completed"],
            "observed_branch_run_conclusions": ["failure"],
            "observed_run_jobs": [
                {
                    "id": 4561,
                    "name": "Accessibility checks",
                    "status": "completed",
                    "conclusion": "failure",
                    "html_url": "https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    "started_at": "2026-05-22T07:40:00Z",
                    "completed_at": "2026-05-22T07:41:00Z",
                }
            ],
            "observed_job_names": ["Accessibility checks"],
            "observed_step_names": ["Run axe-core accessibility checks"],
            "observed_status_check_names": ["Accessibility checks"],
            "observed_status_check_workflow_names": ["Flutter Required Checks"],
            "failed_status_check_names": ["Accessibility checks"],
            "failed_status_check_workflow_names": ["Flutter Required Checks"],
            "accessibility_status_check_name": "Accessibility checks",
            "accessibility_status_check_workflow_name": "Flutter Required Checks",
            "accessibility_status_check_status": "completed",
            "accessibility_status_check_conclusion": "failure",
            "accessibility_status_check_url": "https://github.com/IstiN/trackstate/actions/runs/456",
            "matched_accessibility_markers": ["accessibility"],
            "matched_contrast_markers": ["contrast"],
            "matched_semantic_markers": ["semantic"],
            "run_log_matched_accessibility_markers": ["axe-core"],
            "run_log_matched_contrast_markers": ["contrast"],
            "run_log_matched_semantic_markers": ["semantic"],
            "run_log_mentions_accessibility": True,
            "run_log_mentions_contrast_issue": True,
            "run_log_mentions_semantic_issue": True,
            "run_log_excerpt": "Accessibility checks failed with a contrast violation.",
            "run_log_error": None,
            "runtime_accessibility_surface_present": True,
            "runtime_accessibility_surface_summary": "flt-semantics tree present",
            "probe_contains_low_contrast_indicator": True,
            "probe_contains_semantic_label_indicator": True,
            "probe_semantic_label": "button",
            "probe_contrast_technique": "Uses onSurface.withAlpha(89) on surface.",
            "cleanup_closed_pull_request": True,
            "cleanup_deleted_branch": True,
        }


class GitHubAccessibilityBranchProtectionMergeBlockProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="lib/ts936_probe_surface.dart",
            probe_render_host_path="lib/main.dart",
            branch_prefix="ts936-a11y-merge-block",
            commit_message="TS-936 probe: verify branch protection blocks accessibility failure merge",
            pull_request_title="TS-936 disposable probe",
            pull_request_body="Disposable PR created by TS-936 automation.",
            expected_accessibility_markers=["accessibility", "axe-core"],
            contrast_evidence_markers=["contrast", "4.5:1"],
            semantic_evidence_markers=["semantic", "label"],
            poll_interval_seconds=5,
            run_timeout_seconds=900,
            pull_request_timeout_seconds=180,
        )

    def test_validate_exposes_required_checks_and_merge_state_surface(self) -> None:
        workflow_text = """
name: Flutter Required Checks
on:
  pull_request:
    types: [opened, synchronize]
jobs:
  flutter-checks:
    name: Flutter checks
    runs-on: ubuntu-latest
    steps:
      - name: Analyze
        run: flutter analyze
  accessibility-checks:
    name: Accessibility checks
    runs-on: ubuntu-latest
    needs: flutter-checks
    steps:
      - name: Run axe-core accessibility checks
        run: npm run test:a11y
""".strip()
        probe = _StubProbeService(
            self.config,
            github_api_client=_FakeGitHubApiClient(
                {
                    "/repos/IstiN/trackstate": {"default_branch": "main"},
                    "/repos/IstiN/trackstate/actions/workflows?per_page=100": {
                        "workflows": [
                            {
                                "id": 1,
                                "name": "Flutter Required Checks",
                                "path": ".github/workflows/unit-tests.yml",
                            }
                        ]
                    },
                    "/repos/IstiN/trackstate/contents/.github/workflows/unit-tests.yml?ref=main": workflow_text,
                    "/repos/IstiN/trackstate/rules/branches/main": [
                        {
                            "type": "required_status_checks",
                            "parameters": {
                                "required_status_checks": [{"context": "Accessibility checks"}]
                            },
                        }
                    ],
                    "/repos/IstiN/trackstate/branches/main/protection": {
                        "required_status_checks": {"contexts": ["Accessibility checks"]}
                    },
                }
            ),
        )

        observation = probe.validate()

        self.assertTrue(observation.repository_declares_accessibility_required_check)
        self.assertEqual(observation.required_check_contexts, ["Accessibility checks"])
        self.assertEqual(observation.pull_request_merge_state_status, "BLOCKED")
        self.assertEqual(observation.gate.pull_request_mergeable_state, "blocked")
        self.assertEqual(observation.gate.accessibility_status_check_name, "Accessibility checks")

    def test_low_contrast_helper_accepts_same_surface_probe_pattern(self) -> None:
        probe = _StubProbeService(
            self.config,
            github_api_client=_FakeGitHubApiClient(
                {
                    "/repos/IstiN/trackstate": {"default_branch": "main"},
                    "/repos/IstiN/trackstate/actions/workflows?per_page=100": {"workflows": []},
                }
            ),
        )

        self.assertTrue(
            probe._probe_has_low_contrast_indicator(  # noqa: SLF001
                """
                final colorScheme = Theme.of(context).colorScheme;
                final lowContrastColor = colorScheme.surface;
                return ColoredBox(
                  color: colorScheme.surface,
                  child: Text(
                    'Sync issue',
                    style: TextStyle(color: colorScheme.surface),
                  ),
                );
                """
            )
        )

    def test_inject_probe_into_render_host_replaces_stale_checked_in_probe_import(self) -> None:
        probe = _StubProbeService(
            self.config,
            github_api_client=_FakeGitHubApiClient(
                {
                    "/repos/IstiN/trackstate": {"default_branch": "main"},
                    "/repos/IstiN/trackstate/actions/workflows?per_page=100": {"workflows": []},
                }
            ),
        )

        patched = probe._inject_probe_into_render_host(  # noqa: SLF001
            """
import 'package:flutter/material.dart';

import 'data/repositories/trackstate_repository.dart';
import 'ui/features/tracker/views/trackstate_app.dart';
import 'ts908_probe_surface.dart';

const bool _useDemoRepositoryForAccessibility = bool.fromEnvironment(
  'TRACKSTATE_USE_DEMO_REPOSITORY',
);

void main() {
  runApp(_Ts908RenderedProbeApp(child: _useDemoRepositoryForAccessibility
        ? const TrackStateApp(repository: DemoTrackStateRepository())
        : const TrackStateApp(),));
}

class _Ts908RenderedProbeApp extends StatelessWidget {
  const _Ts908RenderedProbeApp({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'TrackState.AI',
      home: Scaffold(
        body: Align(
          alignment: Alignment.topLeft,
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: const Ts908ProbeSurface(),
          ),
        ),
      ),
    );
  }
}
""".strip()
        )

        self.assertIn("import 'ts936_probe_surface.dart';", patched)
        self.assertNotIn("import 'ts908_probe_surface.dart';", patched)


if __name__ == "__main__":
    unittest.main()
