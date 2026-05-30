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
            post_fault_console_events=[],
            post_fault_page_errors=["Error", "Error"],
        )

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
                post_fault_console_events=[],
                post_fault_page_errors=["ReferenceError: shell crash"],
            )

        self.assertIn("global page error", str(error.exception))


if __name__ == "__main__":
    unittest.main()
