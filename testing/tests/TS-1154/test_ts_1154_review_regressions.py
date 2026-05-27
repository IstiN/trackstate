from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from testing.components.pages.live_workspace_switcher_page import (
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
    WorkspaceSwitcherTriggerObservation,
)


def _load_ts_808_module():
    module_path = Path(__file__).parents[1] / "TS-808" / "test_ts_808.py"
    spec = importlib.util.spec_from_file_location("ts_808_runtime", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Ts1154ReviewRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = _load_ts_808_module()

    def _trigger(self) -> WorkspaceSwitcherTriggerObservation:
        return WorkspaceSwitcherTriggerObservation(
            viewport_width=1440.0,
            viewport_height=960.0,
            semantic_label=(
                "Workspace switcher: Active local workspace, Local, Local Git, "
                "/tmp/trackstate-demo, Branch: main"
            ),
            visible_text="Active local workspace\nLocal\nLocal Git\n/tmp/trackstate-demo\nBranch: main",
            raw_text_lines=(
                "Active local workspace",
                "Local",
                "Local Git",
                "/tmp/trackstate-demo",
                "Branch: main",
            ),
            display_name="Active local workspace",
            workspace_type="Local",
            state_label="Local Git",
            icon_count=1,
            left=0.0,
            top=0.0,
            width=320.0,
            height=48.0,
            top_button_labels=(),
        )

    def _row(
        self,
        *,
        selected: bool,
        display_name: str = "Active local workspace",
        target_type_label: str = "Local",
        state_label: str = "Local Git",
        detail_text: str = "/tmp/trackstate-demo, Branch: main",
        action_labels: tuple[str, ...] = (),
        button_labels: tuple[str, ...] = (),
    ) -> WorkspaceSwitcherRowObservation:
        return WorkspaceSwitcherRowObservation(
            display_name=display_name,
            target_type_label=target_type_label,
            state_label=state_label,
            detail_text=detail_text,
            visible_text=(
                f"{display_name} {target_type_label} {state_label} {detail_text}"
            ),
            selected=selected,
            semantics_label=None,
            icon_accessibility_label=None,
            action_labels=action_labels,
            button_labels=button_labels,
        )

    def test_finds_selected_local_git_row_only(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text="Workspace switcher",
            row_count=2,
            rows=(
                self._row(selected=False, display_name="Hosted workspace", target_type_label="Hosted"),
                self._row(selected=True, action_labels=("Active",), button_labels=("Active", "Delete: Active local workspace")),
            ),
        )

        row = self.module._find_active_local_row(  # type: ignore[attr-defined]
            switcher,
            trigger=self._trigger(),
        )

        self.assertTrue(row.selected)
        self.assertEqual(row.display_name, "Active local workspace")
        self.assertEqual(row.state_label, "Local Git")

    def test_rejects_trigger_matching_row_when_not_selected(self) -> None:
        switcher = WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text="Workspace switcher",
            row_count=1,
            rows=(
                self._row(
                    selected=False,
                    action_labels=("Delete: Active local workspace",),
                    button_labels=("Delete: Active local workspace",),
                ),
            ),
        )

        with self.assertRaises(AssertionError) as error:
            self.module._find_active_local_row(  # type: ignore[attr-defined]
                switcher,
                trigger=self._trigger(),
            )

        self.assertIn("selected active local workspace row", str(error.exception))


if __name__ == "__main__":
    unittest.main()
