from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

from testing.components.pages.live_workspace_switcher_page import (
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherTabStopObservation,
)

_LIVE_TEST_PATH = Path(__file__).with_name("test_ts_911.py")
_LIVE_TEST_SPEC = spec_from_file_location("testing.tests.ts_911_live_module", _LIVE_TEST_PATH)
if _LIVE_TEST_SPEC is None or _LIVE_TEST_SPEC.loader is None:
    raise RuntimeError(f"Unable to load TS-911 helpers from {_LIVE_TEST_PATH}")
_LIVE_TEST_MODULE = module_from_spec(_LIVE_TEST_SPEC)
_LIVE_TEST_SPEC.loader.exec_module(_LIVE_TEST_MODULE)


class Ts911RegressionsTest(unittest.TestCase):
    def test_prefers_selected_saved_workspace_row_as_reverse_wrap_start_target(self) -> None:
        first_row = WorkspaceSwitcherSavedWorkspaceRowObservation(
            display_name="Hosted main workspace",
            target_type_label="Hosted",
            state_label="Attachments limited",
            detail_text="istin/trackstate-setup • Branch: main",
            selected=True,
            action_labels=("Active",),
            left=0.0,
            top=0.0,
            width=100.0,
            height=32.0,
        )
        tab_stops = (
            WorkspaceSwitcherTabStopObservation(
                label="Open: Hosted alt workspace",
                visible_text="",
                role=None,
                tag_name="BUTTON",
                tabindex="0",
                tab_index_value=0,
                dom_index=4,
                keyboard_focusable=True,
                disabled=False,
                outer_html="<button></button>",
            ),
        )

        target = _LIVE_TEST_MODULE._first_reverse_wrap_start_target(
            first_row=first_row,
            tab_stops=tab_stops,
        )

        self.assertEqual(
            target["label"],
            "Hosted main workspace, Hosted, Attachments limited, istin/trackstate-setup • Branch: main",
        )

    def test_reverse_wrap_assertion_flags_workspace_trigger_even_when_probe_mislabels_it(self) -> None:
        state = {
            "before": {
                "accessible_name": "Hosted main workspace, Hosted, Attachments limited, istin/trackstate-setup • Branch: main",
            },
            "active": {
                "accessible_name": "Workspace switcher: Hosted main workspace, Hosted, Attachments limited",
            },
            "focus": {
                "focus_owned_by_switcher": True,
                "active_within_switcher": True,
                "active_on_trigger": False,
            },
            "expected_target": {
                "label": "Branch",
            },
            "first_internal_target": {
                "label": "Hosted main workspace, Hosted, Attachments limited, istin/trackstate-setup • Branch: main",
            },
            "row_focus": {},
            "monitor": {
                "ever_hidden_after_visible": False,
            },
            "switcher": {},
        }

        with self.assertRaisesRegex(
            AssertionError,
            "focus moved to the workspace-switcher trigger instead of wrapping inside the panel",
        ):
            _LIVE_TEST_MODULE._assert_reverse_wrap(state)


if __name__ == "__main__":
    unittest.main()
