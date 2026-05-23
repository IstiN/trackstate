from __future__ import annotations

import json
import unittest

from testing.components.services.github_accessibility_pull_request_gate_probe import (
    GitHubAccessibilityPullRequestGateProbeService,
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


class _StubProbeService(GitHubAccessibilityPullRequestGateProbeService):
    def __init__(self, config: GitHubAccessibilityPullRequestGateConfig) -> None:
        super().__init__(config, github_api_client=_FakeGitHubApiClient({}))

    def _create_and_observe_pull_request(self, workflow_id: int) -> dict[str, object]:
        del workflow_id
        return {
            "pull_request_number": 123,
            "pull_request_url": "https://github.com/IstiN/trackstate/pull/123",
            "pull_request_checks_url": "https://github.com/IstiN/trackstate/pull/123/checks",
            "pull_request_head_branch": "ts908-accessibility-gate-20260522000000",
            "pull_request_head_sha": "abc123",
            "pull_request_probe_path": "lib/ts908_probe_surface.dart",
            "probe_render_host_path": "lib/main.dart",
            "probe_rendered_in_application": True,
            "pull_request_file_paths": ["lib/main.dart", "lib/ts908_probe_surface.dart"],
            "pull_request_state": "open",
            "pull_request_mergeable_state": "clean",
            "pull_request_status_state": "success",
            "latest_pull_request_run_id": 456,
            "latest_pull_request_run_url": "https://github.com/IstiN/trackstate/actions/runs/456",
            "latest_pull_request_run_event": "pull_request",
            "latest_pull_request_run_status": "completed",
            "latest_pull_request_run_conclusion": "success",
            "observed_branch_run_names": ["Flutter Required Checks"],
            "observed_branch_run_urls": ["https://github.com/IstiN/trackstate/actions/runs/456"],
            "observed_branch_run_statuses": ["completed"],
            "observed_branch_run_conclusions": ["success"],
            "observed_run_jobs": [
                {
                    "id": 4561,
                    "name": "Flutter checks",
                    "status": "completed",
                    "conclusion": "success",
                    "html_url": "https://github.com/IstiN/trackstate/actions/runs/456/job/4561",
                    "started_at": "2026-05-22T07:40:00Z",
                    "completed_at": "2026-05-22T07:41:00Z",
                }
            ],
            "observed_job_names": ["Flutter checks"],
            "observed_step_names": ["Analyze", "Build web app"],
            "observed_status_check_names": ["Flutter checks"],
            "observed_status_check_workflow_names": ["Flutter Required Checks"],
            "failed_status_check_names": [],
            "failed_status_check_workflow_names": [],
            "accessibility_status_check_name": None,
            "accessibility_status_check_workflow_name": None,
            "accessibility_status_check_status": None,
            "accessibility_status_check_conclusion": None,
            "accessibility_status_check_url": None,
            "matched_accessibility_markers": [],
            "matched_contrast_markers": [],
            "matched_semantic_markers": [],
            "run_log_matched_accessibility_markers": [],
            "run_log_matched_contrast_markers": [],
            "run_log_matched_semantic_markers": [],
            "run_log_mentions_accessibility": False,
            "run_log_mentions_contrast_issue": False,
            "run_log_mentions_semantic_issue": False,
            "run_log_excerpt": "",
            "run_log_error": None,
            "runtime_accessibility_surface_present": False,
            "runtime_accessibility_surface_summary": "",
            "runtime_accessibility_sample_labels": [],
            "probe_contains_low_contrast_indicator": True,
            "probe_contains_semantic_label_indicator": True,
            "probe_semantic_label": "button",
            "probe_visible_text": "Sync issue",
            "probe_contrast_technique": "Uses surface text on surface.",
            "cleanup_closed_pull_request": True,
            "cleanup_deleted_branch": True,
        }


class _SurfaceProbeService(_StubProbeService):
    def _read_json_object(self, endpoint: str, *, method: str = "GET", field_args=None):
        del method, field_args
        if endpoint != "/repos/IstiN/trackstate/pulls/123":
            raise AssertionError(f"Unexpected endpoint: {endpoint}")
        return {
            "head": {"sha": "abc123"},
            "mergeable_state": "clean",
        }

    def _read_check_runs_state(self, head_sha: str) -> str | None:
        assert head_sha == "abc123"
        return "failure"

    def _read_pull_request_status_surface(self, pull_request_number: int) -> dict[str, object]:
        assert pull_request_number == 123
        return {
            "status_checks": [],
            "status_check_names": ["Accessibility checks"],
            "status_check_workflow_names": ["Flutter Required Checks"],
            "failed_status_check_names": ["Accessibility checks"],
            "failed_status_check_workflow_names": ["Flutter Required Checks"],
        }


class GitHubAccessibilityPullRequestGateProbeRegressionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = GitHubAccessibilityPullRequestGateConfig(
            repository="IstiN/trackstate",
            base_branch="main",
            target_workflow_name="Flutter Required Checks",
            target_workflow_path=".github/workflows/unit-tests.yml",
            probe_path="lib/ts908_probe_surface.dart",
            probe_render_host_path="lib/main.dart",
            branch_prefix="ts908-accessibility-gate",
            commit_message="TS-908 probe: verify CI accessibility gate on disposable PR",
            pull_request_title="TS-908 disposable probe: verify CI accessibility gate",
            pull_request_body="Disposable PR created by TS-908 automation.",
            expected_accessibility_markers=[
                "axe-core",
                "accessibility",
                "wcag",
                "contrast",
                "aria",
                "semantic",
            ],
            contrast_evidence_markers=[
                "color-contrast",
                "color contrast",
                "contrast ratio",
                "4.5:1",
                "minimum color contrast ratio thresholds",
            ],
            semantic_evidence_markers=["aria", "semantic", "label"],
            poll_interval_seconds=5,
            run_timeout_seconds=900,
            pull_request_timeout_seconds=180,
        )

    def test_validate_combines_workflow_contract_with_live_pr_observation(self) -> None:
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
      - name: Build web app
        run: flutter build web
  accessibility-checks:
    name: Accessibility checks
    runs-on: ubuntu-latest
    needs: flutter-checks
    steps:
      - name: Run axe-core accessibility checks
        run: npm run test:a11y
  deploy-preview:
    name: Deploy preview
    runs-on: ubuntu-latest
    needs: accessibility-checks
    steps:
      - name: Publish preview
        run: echo deploy
""".strip()

        probe = GitHubAccessibilityPullRequestGateProbeService(
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
                }
            ),
        )
        probe._create_and_observe_pull_request = _StubProbeService(  # type: ignore[method-assign]
            self.config
        )._create_and_observe_pull_request

        observation = probe.validate()

        self.assertTrue(observation.target_workflow_present_on_default_branch)
        self.assertTrue(observation.target_workflow_declares_pull_request_trigger)
        self.assertEqual(
            observation.target_workflow_job_names,
            ["Flutter checks", "Accessibility checks", "Deploy preview"],
        )
        self.assertEqual(
            observation.target_workflow_step_names,
            ["Analyze", "Build web app", "Run axe-core accessibility checks", "Publish preview"],
        )
        self.assertEqual(
            observation.target_workflow_accessibility_job_names,
            ["Accessibility checks"],
        )
        self.assertEqual(observation.target_workflow_downstream_job_names, ["Deploy preview"])
        self.assertTrue(observation.target_workflow_downstream_job_depends_on_accessibility)
        self.assertEqual(observation.target_workflow.downstream_job_names, ["Deploy preview"])
        self.assertEqual(
            observation.pull_request_file_paths,
            ["lib/main.dart", "lib/ts908_probe_surface.dart"],
        )
        self.assertEqual(observation.probe_render_host_path, "lib/main.dart")
        self.assertTrue(observation.probe_rendered_in_application)
        self.assertEqual(observation.latest_pull_request_run_event, "pull_request")
        self.assertEqual(len(observation.observed_run_jobs), 1)
        self.assertEqual(observation.observed_run_jobs[0].name, "Flutter checks")
        self.assertFalse(observation.run_log_mentions_accessibility)
        self.assertTrue(observation.cleanup_closed_pull_request)
        self.assertTrue(observation.cleanup_deleted_branch)

    def test_probe_source_publishes_runtime_contrast_signal(self) -> None:
        probe_source = _StubProbeService._probe_source()  # noqa: SLF001

        self.assertIn(
            "import 'ui/features/tracker/services/accessibility_probe_signal.dart';",
            probe_source,
        )
        self.assertIn("publishAccessibilityContrastProbeSignal(", probe_source)
        self.assertIn("foreground: lowContrastColor", probe_source)
        self.assertIn("background: colorScheme.surface", probe_source)
        self.assertIn("ExcludeSemantics(", probe_source)

    def test_find_accessibility_status_check_uses_actual_check_surface(self) -> None:
        probe = _StubProbeService(self.config)

        check = probe._find_accessibility_status_check(  # noqa: SLF001
            [
                {
                    "name": "Flutter checks",
                    "workflow_name": "Flutter Required Checks",
                    "status": "completed",
                    "conclusion": "success",
                    "details_url": "https://example.test/flutter",
                },
                {
                    "name": "Accessibility audit",
                    "workflow_name": "Accessibility gate",
                    "status": "completed",
                    "conclusion": "failure",
                    "details_url": "https://example.test/accessibility",
                },
            ]
        )

        assert check is not None
        self.assertEqual(check["name"], "Accessibility audit")
        self.assertEqual(check["conclusion"], "failure")

    def test_inject_probe_into_render_host_wraps_app_startup(self) -> None:
        probe = _StubProbeService(self.config)

        patched = probe._inject_probe_into_render_host(  # noqa: SLF001
            """
import 'package:flutter/widgets.dart';

import 'ui/features/tracker/views/trackstate_app.dart';

void main() {
  runApp(const TrackStateApp());
}
""".strip()
        )

        self.assertIn("import 'package:flutter/material.dart';", patched)
        self.assertIn("import 'ts908_probe_surface.dart';", patched)
        self.assertIn(
            "runApp(_Ts908RenderedProbeApp(child: const TrackStateApp()));",
            patched,
        )
        self.assertIn("return MaterialApp(", patched)
        self.assertIn("child: const Ts908ProbeSurface(),", patched)
        self.assertNotIn("return Stack(", patched)

    def test_extract_runtime_accessibility_surface_summary_reads_success_log_line(self) -> None:
        probe = _StubProbeService(self.config)

        summary = probe._extract_runtime_accessibility_surface_summary(  # noqa: SLF001
            """
            some prefix
            Accessibility runtime surface ready: hosts=1; nodes=4; sample-labels=["Create tracker"]
            trailing line
            """
        )

        self.assertEqual(
            summary,
            'Accessibility runtime surface ready: hosts=1; nodes=4; sample-labels=["Create tracker"]',
        )

    def test_extract_runtime_accessibility_sample_labels_reads_summary_labels(self) -> None:
        probe = _StubProbeService(self.config)

        labels = probe._extract_runtime_accessibility_sample_labels(  # noqa: SLF001
            """
            some prefix
            Accessibility runtime surface ready: hosts=1; nodes=4; sample-labels=["button", "Create tracker"]
            trailing line
            """
        )

        self.assertEqual(labels, ["button", "Create tracker"])

    def test_extract_flutter_engine_initialization_log_entries_reads_distinct_states(self) -> None:
        probe = _StubProbeService(self.config)

        entries = probe._extract_flutter_engine_initialization_log_entries(  # noqa: SLF001
            """
            prefix
            Accessibility checks 2026-05-22T11:02:00Z Flutter engine initialization: bootstrap requested
            Accessibility checks 2026-05-22T11:02:01Z Flutter engine initialization: engine ready
            Accessibility checks 2026-05-22T11:02:01Z Flutter engine initialization: engine ready
            suffix
            """
        )

        self.assertEqual(
            entries,
            [
                "Accessibility checks 2026-05-22T11:02:00Z Flutter engine initialization: bootstrap requested",
                "Accessibility checks 2026-05-22T11:02:01Z Flutter engine initialization: engine ready",
            ],
        )

    def test_extract_semantics_tree_discovery_log_entries_keeps_runtime_status_lines(self) -> None:
        probe = _StubProbeService(self.config)

        entries = probe._extract_semantics_tree_discovery_log_entries(  # noqa: SLF001
            """
            Accessibility checks 2026-05-22T11:02:03Z Semantics tree discovery: waiting for nodes
            Accessibility checks 2026-05-22T11:02:08Z Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]
            """
        )

        self.assertEqual(
            entries,
            [
                "Accessibility checks 2026-05-22T11:02:03Z Semantics tree discovery: waiting for nodes",
                'Accessibility checks 2026-05-22T11:02:08Z Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]',
            ],
        )

    def test_accessibility_stage_log_scoping_ignores_other_job_markers(self) -> None:
        probe = _StubProbeService(self.config)

        scoped_log = probe._accessibility_stage_run_log_text(  # noqa: SLF001
            """
            Flutter checks Run unit and golden tests 2026-05-22T11:02:00Z Flutter engine initialization: bootstrap requested
            Flutter checks Run unit and golden tests 2026-05-22T11:02:01Z Flutter engine initialization: engine ready
            Accessibility checks Run axe-core accessibility checks 2026-05-22T11:02:08Z Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]
            """,
            [
                {"name": "Flutter checks"},
                {"name": "Accessibility checks"},
            ],
        )

        self.assertEqual(
            probe._extract_flutter_engine_initialization_log_entries(scoped_log),  # noqa: SLF001
            [],
        )
        self.assertEqual(
            probe._extract_semantics_tree_discovery_log_entries(scoped_log),  # noqa: SLF001
            [
                'Accessibility checks Run axe-core accessibility checks 2026-05-22T11:02:08Z Accessibility runtime surface ready: hosts=1; nodes=5; sample-labels=["Create tracker"]',
            ],
        )

    def test_extract_log_excerpt_prefers_engine_and_runtime_markers(self) -> None:
        probe = _StubProbeService(self.config)

        excerpt = probe._extract_log_excerpt(  # noqa: SLF001
            """
            Accessibility checks Detect accessibility changes 2026-05-22T11:01:00Z accessibility inputs resolved
            Accessibility checks Run axe-core accessibility checks 2026-05-22T11:02:00Z Flutter engine initialization: bootstrap requested
            Accessibility checks Run axe-core accessibility checks 2026-05-22T11:02:08Z Accessibility runtime surface ready: hosts=1; nodes=5
            """,
            "",
        )

        self.assertIn("Flutter engine initialization: bootstrap requested", excerpt)

    def test_wait_for_pull_request_surface_keeps_failed_check_fields(self) -> None:
        probe = _SurfaceProbeService(self.config)

        surface = probe._wait_for_pull_request_surface(123, head_sha="abc123")  # noqa: SLF001

        self.assertEqual(surface["failed_status_check_names"], ["Accessibility checks"])
        self.assertEqual(
            surface["failed_status_check_workflow_names"],
            ["Flutter Required Checks"],
        )

    def test_inject_probe_into_render_host_supports_multiline_conditional_run_app(self) -> None:
        probe = _StubProbeService(self.config)

        patched = probe._inject_probe_into_render_host(  # noqa: SLF001
            """
import 'package:flutter/widgets.dart';

import 'data/repositories/trackstate_repository.dart';
import 'ui/features/tracker/views/trackstate_app.dart';

const bool _useDemoRepositoryForAccessibility = bool.fromEnvironment(
  'TRACKSTATE_USE_DEMO_REPOSITORY',
);

void main() {
  runApp(
    _useDemoRepositoryForAccessibility
        ? const TrackStateApp(repository: DemoTrackStateRepository())
        : const TrackStateApp(),
  );
}
""".strip()
        )

        self.assertIn("import 'package:flutter/material.dart';", patched)
        self.assertIn("import 'ts908_probe_surface.dart';", patched)
        self.assertIn("runApp(_Ts908RenderedProbeApp(child:", patched)
        self.assertIn("_useDemoRepositoryForAccessibility", patched)
        self.assertIn(": const TrackStateApp()", patched)
        self.assertNotIn("runApp(const _Ts908RenderedProbeApp());", patched)
        self.assertIn("return MaterialApp(", patched)
        self.assertIn("Ts908ProbeSurface()", patched)

    def test_probe_source_preserves_variable_based_label_and_text_extraction(self) -> None:
        probe_source = _StubProbeService._probe_source()  # noqa: SLF001

        self.assertEqual(
            _StubProbeService._extract_probe_semantic_label(probe_source),  # noqa: SLF001
            "button",
        )
        self.assertEqual(
            _StubProbeService._extract_probe_visible_text(probe_source),  # noqa: SLF001
            "Sync issue",
        )
        self.assertTrue(_StubProbeService._probe_has_low_contrast_indicator(probe_source))  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
