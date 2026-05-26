from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.components.services.github_accessibility_stage_log_inspector import (
    GitHubAccessibilityStageLogInspector,
)


def _load_ts_932_module():
    module_path = Path(__file__).with_name("test_ts_932.py")
    spec = importlib.util.spec_from_file_location("ts_932_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _FakeWorkflowRunLogReader:
    def __init__(self, log_text: str) -> None:
        self._log_text = log_text

    def read_run_log(self, run_id: int) -> str:
        del run_id
        return self._log_text


class Ts932ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_932_module()

    def test_stage_filter_ignores_non_accessibility_jobs(self) -> None:
        log_text = "\n".join(
            [
                "Flutter checks\tRun unit and golden tests\t2026-05-22T11:02:00Z Flutter engine initialization: bootstrap requested",
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Verified flt-semantics-placeholder before scan",
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:03Z Accessibility runtime surface ready: hosts=1; nodes=5",
            ]
        )
        inspector = GitHubAccessibilityStageLogInspector(
            _FakeWorkflowRunLogReader(log_text)
        )

        entries = inspector.read_accessibility_stage_entries(123)

        self.assertEqual(len(entries), 2)
        self.assertTrue(
            all(entry.job_name == "Accessibility checks" for entry in entries)
        )

    def test_placeholder_extraction_requires_placeholder_marker(self) -> None:
        log_text = "\n".join(
            [
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Verified flt-semantics-placeholder before scan",
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:02Z Semantics tree discovery: waiting for nodes",
            ]
        )
        inspector = GitHubAccessibilityStageLogInspector(
            _FakeWorkflowRunLogReader(log_text)
        )

        entries = inspector.read_accessibility_stage_entries(123)
        placeholder_entries = inspector.extract_placeholder_verification_entries(entries)

        self.assertEqual(
            placeholder_entries,
            [
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Verified flt-semantics-placeholder before scan"
            ],
        )

    def test_sequence_failures_accepts_placeholder_before_runtime_and_scan_progress(self) -> None:
        stage_lines = [
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Verified flt-semantics-placeholder before scan",
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:03Z Accessibility runtime surface ready: hosts=1; nodes=5",
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:06Z 4 passed (4.6s)",
        ]

        failures = self.module._sequence_failures(  # type: ignore[attr-defined]
            stage_log_lines=stage_lines,
            placeholder_entries=[stage_lines[0]],
            runtime_entries=[stage_lines[1]],
            scan_entries=[stage_lines[2]],
        )

        self.assertEqual(failures, [])

    def test_sequence_failures_rejects_missing_placeholder_verification(self) -> None:
        stage_lines = [
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:03Z Accessibility runtime surface ready: hosts=1; nodes=5",
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:06Z 4 passed (4.6s)",
        ]

        failures = self.module._sequence_failures(  # type: ignore[attr-defined]
            stage_log_lines=stage_lines,
            placeholder_entries=[],
            runtime_entries=[stage_lines[0]],
            scan_entries=[stage_lines[1]],
        )

        self.assertEqual(len(failures), 1)
        self.assertIn("flt-semantics-placeholder", failures[0])

    def test_placeholder_extraction_rejects_negative_placeholder_status(self) -> None:
        log_text = "\n".join(
            [
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z waiting for flt-semantics-placeholder to be ready",
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:02Z flt-semantics-placeholder not present yet",
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:03Z Verified flt-semantics-placeholder before scan",
            ]
        )
        inspector = GitHubAccessibilityStageLogInspector(
            _FakeWorkflowRunLogReader(log_text)
        )

        entries = inspector.read_accessibility_stage_entries(123)
        placeholder_entries = inspector.extract_placeholder_verification_entries(entries)

        self.assertEqual(
            placeholder_entries,
            [
                "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:03Z Verified flt-semantics-placeholder before scan"
            ],
        )

    def test_sequence_failures_rejects_missing_scan_evidence(self) -> None:
        stage_lines = [
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:01Z Verified flt-semantics-placeholder before scan",
            "Accessibility checks\tRun axe-core accessibility checks\t2026-05-22T11:02:03Z Accessibility runtime surface ready: hosts=1; nodes=5",
        ]

        failures = self.module._sequence_failures(  # type: ignore[attr-defined]
            stage_log_lines=stage_lines,
            placeholder_entries=[stage_lines[0]],
            runtime_entries=[stage_lines[1]],
            scan_entries=[],
        )

        self.assertEqual(len(failures), 1)
        self.assertIn("full WCAG scan proceeded", failures[0])

    def test_runtime_module_keeps_framework_wiring_inside_support_factory(self) -> None:
        module_source = Path(__file__).with_name("test_ts_932.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("GhCliWorkflowRunLogReader", module_source)
        self.assertIn(
            "create_github_accessibility_stage_log_inspector",
            module_source,
        )


if __name__ == "__main__":
    unittest.main()
