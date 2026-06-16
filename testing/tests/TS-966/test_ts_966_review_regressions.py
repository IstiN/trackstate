from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.components.pages.live_workspace_switcher_page import (
    WorkspaceSwitcherObservation,
)


def _load_ts_966_module():
    module_path = Path(__file__).with_name("test_ts_966.py")
    spec = importlib.util.spec_from_file_location("ts_966_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts966ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_966_module()

    def test_accepts_saved_workspace_context_without_row_metadata(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text=(
                "Workspace switcher Hosted main workspace · Hosted · Attachments limited "
                "Saved workspaces Hosted Hosted Attachments limited Attachments limited "
                "Hosted Hosted Needs sign-in Needs sign-in "
                "Open: Hosted fallback workspace Delete: Hosted fallback workspace "
                "Add workspace Manage GitHub access"
            ),
            row_count=0,
            rows=(),
        )

        self.module._assert_fault_locally_contained(  # type: ignore[attr-defined]
            switcher_after_fault=switcher,
            post_fault_console_events=[
                {
                    "level": "log",
                    "text": (
                        "Error: TS-966 synthetic workspace switcher runtime error "
                        "(selector=[flt-semantics-identifier^=\"trackstate-workspace-switcher-row-\"])"
                    ),
                },
            ],
            post_fault_page_errors=[
                {
                    "text": "Error",
                    "message": "Error",
                    "stack": (
                        "Error: TS-966 synthetic workspace switcher runtime error "
                        "(selector=[flt-semantics-identifier^=\"trackstate-workspace-switcher-row-\"])"
                    ),
                    "name": "Error",
                },
                {
                    "text": "Error",
                    "message": "Error",
                    "stack": (
                        "Error: TS-966 synthetic workspace switcher runtime error "
                        "(selector=[flt-semantics-identifier^=\"trackstate-workspace-switcher-row-\"])"
                    ),
                    "name": "Error",
                },
            ],
        )

    def test_accepts_fault_marker_page_error_without_probe_console_signature(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text=(
                "Workspace switcher Hosted main workspace · Hosted · Attachments limited "
                "Saved workspaces Open: Hosted fallback workspace Add workspace"
            ),
            row_count=0,
            rows=(),
        )

        self.module._assert_fault_locally_contained(  # type: ignore[attr-defined]
            switcher_after_fault=switcher,
            post_fault_console_events=[],
            post_fault_page_errors=[
                "Error: TS-966 synthetic workspace switcher runtime error (selector=[flt-semantics-identifier^=\"trackstate-workspace-switcher-row-\"])",
            ],
        )

    def test_accepts_probe_stack_signature_without_console_signature(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text=(
                "Workspace switcher Hosted main workspace · Hosted · Attachments limited "
                "Saved workspaces Open: Hosted fallback workspace Add workspace"
            ),
            row_count=0,
            rows=(),
        )

        self.module._assert_fault_locally_contained(  # type: ignore[attr-defined]
            switcher_after_fault=switcher,
            post_fault_console_events=[],
            post_fault_page_errors=[
                {
                    "text": "Error",
                    "message": "Error",
                    "stack": (
                        "Error\n"
                        "    at recordAndThrow (<anonymous>:21:11)\n"
                        "    at HTMLDocument.patchedSelectorMethod [as querySelectorAll] (<anonymous>:33:18)\n"
                        "    at someFlutterFrame (https://example.test/main.dart.js:1:1)"
                    ),
                    "name": "",
                },
            ],
        )

    def test_rejects_generic_page_error_without_probe_signature(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text=(
                "Workspace switcher Hosted main workspace · Hosted · Attachments limited "
                "Saved workspaces Open: Hosted fallback workspace Add workspace"
            ),
            row_count=0,
            rows=(),
        )

        with self.assertRaises(AssertionError) as error:
            self.module._assert_fault_locally_contained(  # type: ignore[attr-defined]
                switcher_after_fault=switcher,
                post_fault_console_events=[],
                post_fault_page_errors=["Error"],
            )

        self.assertIn("global page error", str(error.exception))

    def test_rejects_generic_page_error_even_with_probe_console_signature(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text=(
                "Workspace switcher Hosted main workspace · Hosted · Attachments limited "
                "Saved workspaces Open: Hosted fallback workspace Add workspace"
            ),
            row_count=0,
            rows=(),
        )

        with self.assertRaises(AssertionError) as error:
            self.module._assert_fault_locally_contained(  # type: ignore[attr-defined]
                switcher_after_fault=switcher,
                post_fault_console_events=[
                    {
                        "level": "log",
                        "text": (
                            "Error: TS-966 synthetic workspace switcher runtime error "
                            "(selector=[flt-semantics-identifier^=\"trackstate-workspace-switcher-row-\"])"
                        ),
                    },
                ],
                post_fault_page_errors=["Error"],
            )

        self.assertIn("global page error", str(error.exception))

    def test_rejects_specific_page_errors(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text=(
                "Workspace switcher Hosted main workspace · Hosted · Attachments limited "
                "Saved workspaces Open: Hosted fallback workspace Add workspace"
            ),
            row_count=0,
            rows=(),
        )

        with self.assertRaises(AssertionError) as error:
            self.module._assert_fault_locally_contained(  # type: ignore[attr-defined]
                switcher_after_fault=switcher,
                post_fault_console_events=[
                    {
                        "level": "log",
                        "text": (
                            "Error: TS-966 synthetic workspace switcher runtime error "
                            "(selector=[flt-semantics-identifier^=\"trackstate-workspace-switcher-row-\"])"
                        ),
                    },
                ],
                post_fault_page_errors=["ReferenceError: shell crash"],
            )

        self.assertIn("global page error", str(error.exception))

    def test_rejects_missing_saved_workspace_context(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text="Workspace switcher Saved workspaces Add workspace",
            row_count=0,
            rows=(),
        )

        with self.assertRaises(AssertionError) as error:
            self.module._assert_fault_locally_contained(  # type: ignore[attr-defined]
                switcher_after_fault=switcher,
                post_fault_console_events=[],
                post_fault_page_errors=[],
            )

        self.assertIn("saved-workspace context", str(error.exception))

    def test_rejects_probe_console_error_level_even_with_fault_marker(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text=(
                "Workspace switcher Hosted main workspace · Hosted · Attachments limited "
                "Saved workspaces Open: Hosted fallback workspace Add workspace"
            ),
            row_count=0,
            rows=(),
        )

        with self.assertRaises(AssertionError) as error:
            self.module._assert_fault_locally_contained(  # type: ignore[attr-defined]
                switcher_after_fault=switcher,
                post_fault_console_events=[
                    {
                        "level": "error",
                        "text": (
                            "Error: TS-966 synthetic workspace switcher runtime error "
                            "(selector=[flt-semantics-identifier^=\"trackstate-workspace-switcher-row-\"])"
                        ),
                    },
                ],
                post_fault_page_errors=[
                    "Error: TS-966 synthetic workspace switcher runtime error (selector=[flt-semantics-identifier^=\"trackstate-workspace-switcher-row-\"])",
                ],
            )

        self.assertIn("global console error", str(error.exception))


if __name__ == "__main__":
    unittest.main()
