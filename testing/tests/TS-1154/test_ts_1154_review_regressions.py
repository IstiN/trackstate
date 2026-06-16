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

    def _switcher(
        self,
        *,
        row_count: int,
        rows: tuple[WorkspaceSwitcherRowObservation, ...],
        switcher_text: str = "Workspace switcher",
    ) -> WorkspaceSwitcherObservation:
        return WorkspaceSwitcherObservation(
            body_text="Workspace switcher",
            switcher_text=switcher_text,
            row_count=row_count,
            rows=rows,
        )

    def test_finds_selected_local_git_row_only(self) -> None:
        switcher = self._switcher(
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

    def test_falls_back_to_unique_trigger_matching_local_git_row_without_actions(self) -> None:
        switcher = self._switcher(
            row_count=2,
            rows=(
                self._row(selected=False),
                self._row(
                    selected=False,
                    display_name="Hosted workspace",
                    target_type_label="Hosted",
                    state_label="Attachments limited",
                    detail_text="istin/trackstate-setup, Branch: main",
                    action_labels=("Open: Hosted workspace", "Delete: Hosted workspace"),
                    button_labels=("Open: Hosted workspace", "Delete: Hosted workspace"),
                ),
            ),
        )

        row = self.module._find_active_local_row(  # type: ignore[attr-defined]
            switcher,
            trigger=self._trigger(),
        )

        self.assertEqual(row.display_name, "Active local workspace")
        self.assertEqual(row.state_label, "Local Git")

    def test_rejects_trigger_matching_row_when_not_selected(self) -> None:
        switcher = self._switcher(
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

    def test_reprobes_when_switcher_text_shows_active_local_row_but_rows_are_empty(self) -> None:
        initial_switcher = self._switcher(
            row_count=0,
            rows=(),
            switcher_text=(
                "Workspace switcher Active local workspace, Local, Local Git, "
                "/tmp/trackstate-demo • Branch: main"
            ),
        )
        reprobed_switcher = self._switcher(
            row_count=1,
            rows=(self._row(selected=True, action_labels=("Active",), button_labels=("Active",)),),
            switcher_text=initial_switcher.switcher_text,
        )

        class _FakePage:
            def __init__(self, observation: WorkspaceSwitcherObservation) -> None:
                self.calls = 0
                self._observation = observation

            def observe_open_switcher(self, *, timeout_ms: int = 60_000) -> WorkspaceSwitcherObservation:
                self.calls += 1
                return self._observation

        page = _FakePage(reprobed_switcher)
        result: dict[str, object] = {}

        resolved = self.module._ensure_active_local_row_observable(  # type: ignore[attr-defined]
            page=page,
            switcher=initial_switcher,
            trigger=self._trigger(),
            result=result,
        )

        self.assertEqual(page.calls, 1)
        self.assertEqual(resolved.row_count, 1)
        self.assertEqual(result["switcher_row_reprobe_observation"]["row_count"], 1)

    def test_reports_instrumentation_failure_when_rows_stay_empty_after_reprobe(self) -> None:
        switcher = self._switcher(
            row_count=0,
            rows=(),
            switcher_text=(
                "Workspace switcher Active local workspace, Local, Local Git, "
                "/tmp/trackstate-demo • Branch: main"
            ),
        )

        class _FakePage:
            def observe_open_switcher(self, *, timeout_ms: int = 60_000) -> WorkspaceSwitcherObservation:
                return switcher

        original_poll_until = self.module.poll_until  # type: ignore[attr-defined]
        self.module.poll_until = (  # type: ignore[attr-defined]
            lambda **_: (False, switcher)
        )
        try:
            with self.assertRaises(AssertionError) as error:
                self.module._ensure_active_local_row_observable(  # type: ignore[attr-defined]
                    page=_FakePage(),
                    switcher=switcher,
                    trigger=self._trigger(),
                    result={},
                )
        finally:
            self.module.poll_until = original_poll_until  # type: ignore[attr-defined]

        self.assertIn("instrumentation failure", str(error.exception))

    def test_workspace_token_profile_ids_include_local_and_hosted_profiles(self) -> None:
        workspace_state = self.module._workspace_state("IstiN/trackstate-setup")  # type: ignore[attr-defined]

        profile_ids = self.module._workspace_token_profile_ids(  # type: ignore[attr-defined]
            workspace_state,
        )

        self.assertEqual(
            profile_ids,
            (
                "local:/tmp/trackstate-demo@main",
                "hosted:istin/trackstate-setup@main",
            ),
        )

    def test_authenticated_session_skips_reconnect_even_with_connect_copy(self) -> None:
        body_text = "\n".join(
            [
                "Workspace switcher: Active local workspace, Local, Local Git, /tmp/trackstate-demo, Branch: main",
                "Connected as octocat to IstiN/trackstate-setup.",
                "Manage GitHub access",
                "Connect GitHub",
            ],
        )

        requires_connect = self.module._session_requires_connect(  # type: ignore[attr-defined]
            body_text=body_text,
            user_login="octocat",
            repository="IstiN/trackstate-setup",
        )

        self.assertFalse(requires_connect)

    def test_authenticated_session_accepts_synced_local_git_shell(self) -> None:
        requires_connect = self.module._session_requires_connect(  # type: ignore[attr-defined]
            body_text="\n".join(
                [
                    "Workspace switcher: Active local workspace, Local, Local Git",
                    "Dashboard",
                    "Create issue",
                    "Synced with Git",
                ],
            ),
            user_login="octocat",
            repository="IstiN/trackstate-setup",
        )

        self.assertFalse(requires_connect)

    def test_signed_in_active_local_precondition_requires_authenticated_session(self) -> None:
        trigger = self._trigger()

        self.assertFalse(
            self.module._signed_in_active_local_precondition(  # type: ignore[attr-defined]
                trigger=trigger,
                body_text=(
                    "Workspace switcher: Active local workspace, Local, Local Git, "
                    "/tmp/trackstate-demo, Branch: main\n"
                    "Hosted setup workspace\n"
                    "Hosted\n"
                    "Needs sign-in\n"
                    "GitHub write access is not connected"
                ),
                user_login="octocat",
                repository="IstiN/trackstate-setup",
            ),
        )

        self.assertTrue(
            self.module._signed_in_active_local_precondition(  # type: ignore[attr-defined]
                trigger=trigger,
                body_text=(
                    "Workspace switcher: Active local workspace, Local, Local Git, "
                    "/tmp/trackstate-demo, Branch: main\n"
                    "Connected as octocat to IstiN/trackstate-setup.\n"
                    "Manage GitHub access"
                ),
                user_login="octocat",
                repository="IstiN/trackstate-setup",
            ),
        )

if __name__ == "__main__":
    unittest.main()
