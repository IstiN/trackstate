from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

from testing.components.pages.live_workspace_switcher_page import (
    WorkspaceSwitcherFocusOwnershipObservation,
    WorkspaceSwitcherTabStopObservation,
)
from testing.core.interfaces.web_app_session import FocusedElementObservation

_LIVE_TEST_PATH = Path(__file__).with_name("test_ts_911.py")
_LIVE_TEST_SPEC = spec_from_file_location("testing.tests.ts_911_live_module", _LIVE_TEST_PATH)
if _LIVE_TEST_SPEC is None or _LIVE_TEST_SPEC.loader is None:
    raise RuntimeError(f"Unable to load TS-911 helpers from {_LIVE_TEST_PATH}")
_LIVE_TEST_MODULE = module_from_spec(_LIVE_TEST_SPEC)
_LIVE_TEST_SPEC.loader.exec_module(_LIVE_TEST_MODULE)

class Ts911RegressionsTest(unittest.TestCase):
    def test_prefers_selected_row_when_panel_already_opens_on_first_internal_focus(self) -> None:
        target = _LIVE_TEST_MODULE._resolve_first_internal_focus_target(
            active=FocusedElementObservation(
                tag_name="BUTTON",
                role=None,
                accessible_name=(
                    "Hosted main workspace, Hosted, Attachments limited, "
                    "istin/trackstate-setup • Branch: main"
                ),
                text="",
                tabindex="0",
                outer_html="<button></button>",
            ),
            focus=WorkspaceSwitcherFocusOwnershipObservation(
                active_label=(
                    "Hosted main workspace, Hosted, Attachments limited, "
                    "istin/trackstate-setup • Branch: main"
                ),
                active_role=None,
                active_tag_name="BUTTON",
                active_outer_html="<button></button>",
                active_visible=True,
                active_in_viewport=True,
                switcher_focus_within=True,
                active_within_switcher=True,
                active_on_trigger=False,
                focus_owned_by_switcher=True,
            ),
            first_row_label=(
                "Hosted main workspace, Hosted, Attachments limited, "
                "istin/trackstate-setup • Branch: main"
            ),
            tab_stops=(
                WorkspaceSwitcherTabStopObservation(
                    label="Open: Hosted alt workspace",
                    visible_text="Open: Hosted alt workspace",
                    role=None,
                    tag_name="BUTTON",
                    tabindex="0",
                    tab_index_value=0,
                    dom_index=2,
                    keyboard_focusable=True,
                    disabled=False,
                    outer_html="<button></button>",
                ),
            ),
        )

        self.assertEqual(
            target["label"],
            "Hosted main workspace, Hosted, Attachments limited, istin/trackstate-setup • Branch: main",
        )

    def test_derives_reverse_wrap_start_target_from_first_internal_tab_stop(self) -> None:
        tab_stops = (
            WorkspaceSwitcherTabStopObservation(
                label="Hosted main workspace, Hosted, Attachments limited, istin/trackstate-setup • Branch: main",
                visible_text="",
                role=None,
                tag_name="BUTTON",
                tabindex="0",
                tab_index_value=0,
                dom_index=0,
                keyboard_focusable=True,
                disabled=False,
                outer_html="<button></button>",
            ),
        )

        target = _LIVE_TEST_MODULE._first_internal_focus_target(tab_stops=tab_stops)

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

    def test_expected_reverse_target_uses_footer_reached_by_forward_tab_trace(self) -> None:
        target = _LIVE_TEST_MODULE._expected_reverse_target_from_forward_trace(
            [
                {
                    "active": {
                        "accessible_name": "Repository",
                        "text": "",
                        "role": None,
                        "tag_name": "INPUT",
                        "tabindex": None,
                        "outer_html": "<input aria-label='Repository'>",
                    },
                    "focus": {
                        "focus_owned_by_switcher": True,
                        "active_within_switcher": True,
                        "active_on_trigger": False,
                    },
                    "monitor": {
                        "ever_hidden_after_visible": False,
                    },
                },
                {
                    "active": {
                        "accessible_name": "Save and switch",
                        "text": "",
                        "role": "button",
                        "tag_name": "FLT-SEMANTICS",
                        "tabindex": "0",
                        "outer_html": "<flt-semantics>Save and switch</flt-semantics>",
                    },
                    "focus": {
                        "focus_owned_by_switcher": True,
                        "active_within_switcher": True,
                        "active_on_trigger": False,
                    },
                    "monitor": {
                        "ever_hidden_after_visible": False,
                    },
                },
            ],
        )

        self.assertEqual(target["label"], "Save and switch")
        self.assertEqual(target["tag_name"], "FLT-SEMANTICS")

    def test_expected_reverse_target_requires_footer_to_be_reached(self) -> None:
        with self.assertRaisesRegex(
            AssertionError,
            "never reached the visible 'Save and switch' footer control",
        ):
            _LIVE_TEST_MODULE._expected_reverse_target_from_forward_trace(
                [
                    {
                        "active": {
                            "accessible_name": "Repository",
                            "text": "",
                        },
                        "focus": {
                            "focus_owned_by_switcher": True,
                            "active_within_switcher": True,
                            "active_on_trigger": False,
                        },
                        "monitor": {
                            "ever_hidden_after_visible": False,
                        },
                    },
                ],
            )


if __name__ == "__main__":
    unittest.main()
