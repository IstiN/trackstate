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
                "role": "button",
                "tag_name": "BUTTON",
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

    def test_reverse_wrap_assertion_does_not_treat_body_fallback_as_trigger(self) -> None:
        state = {
            "before": {
                "accessible_name": "Hosted main workspace, Hosted, Attachments limited, istin/trackstate-setup • Branch: main",
            },
            "active": {
                "accessible_name": "Workspace switcher: Hosted main workspace, Hosted, Attachments limited",
                "tag_name": "BODY",
                "role": None,
            },
            "focus": {
                "focus_owned_by_switcher": False,
                "active_within_switcher": False,
                "active_on_trigger": False,
            },
            "expected_target": {
                "label": "Save and switch",
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

        with self.assertRaises(AssertionError) as context:
            _LIVE_TEST_MODULE._assert_reverse_wrap(state)

        message = str(context.exception)
        self.assertIn("focus escaped the workspace switcher after Shift+Tab", message)
        self.assertNotIn(
            "focus moved to the workspace-switcher trigger instead of wrapping inside the panel",
            message,
        )

    def test_visible_footer_target_prefers_live_save_and_switch_control(self) -> None:
        target = _LIVE_TEST_MODULE._visible_footer_target(
            button_focusability={
                "label": "Save and switch",
                "visible_text": "Save and switch",
                "role": "button",
                "tag_name": "FLT-SEMANTICS",
                "tabindex": "0",
                "keyboard_focusable": True,
                "outer_html": "<flt-semantics>Save and switch</flt-semantics>",
            },
            fallback_target={
                "label": "Branch",
                "visible_text": "",
                "role": None,
                "tag_name": "INPUT",
                "tabindex": None,
                "tab_index_value": 0,
                "dom_index": 19,
                "keyboard_focusable": True,
                "disabled": False,
                "outer_html": "<input aria-label='Branch'>",
            },
        )

        self.assertEqual(target["label"], "Save and switch")
        self.assertEqual(target["tag_name"], "FLT-SEMANTICS")

    def test_best_available_reverse_wrap_target_falls_back_when_tab_stops_missing(self) -> None:
        target = _LIVE_TEST_MODULE._best_available_reverse_wrap_target(
            {
                "internal_tab_stops": [],
                "expected_target": {
                    "label": "Save and switch",
                },
            },
        )

        self.assertEqual(target["label"], "Save and switch")

    def test_supporting_wrap_target_proof_derives_last_reachable_in_panel_target(self) -> None:
        context = _LIVE_TEST_MODULE._supporting_wrap_target_context(
            {
                "status": "derived",
                "expected_target": {
                    "label": "Branch",
                },
                "note": (
                    "Forward Tab did not prove 'Save and switch' as the terminal reachable "
                    "control; the last reachable in-panel control in this run was 'Branch'."
                ),
            },
        )

        self.assertEqual(context["status"], "derived")
        self.assertIn("last reachable in-panel control", context["note"])

    def test_supporting_wrap_target_context_uses_inconclusive_proof_note(self) -> None:
        context = _LIVE_TEST_MODULE._supporting_wrap_target_context(
            {
                "status": "inconclusive",
                "expected_target": {
                    "label": "Branch",
                },
                "note": "Forward Tab evidence was inconclusive; using the best available in-panel target 'Branch'.",
            },
        )

        self.assertEqual(context["status"], "inconclusive")
        self.assertIn("best available in-panel target", context["note"])


if __name__ == "__main__":
    unittest.main()
