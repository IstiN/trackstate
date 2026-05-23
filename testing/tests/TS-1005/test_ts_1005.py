from __future__ import annotations

import json
import platform
import shutil
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import (  # noqa: E402
    StartupSurfaceObservation,
    TrackStateTrackerPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-1005"
TEST_CASE_TITLE = (
    "Active workspace directory mismatch on startup clears selection and returns to landing state"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1005/test_ts_1005.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1005-mismatched-workspace"
LOCAL_DISPLAY_NAME = "Broken local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
LINKED_BUGS = ["TS-995"]
STARTUP_SETTLE_TIMEOUT_SECONDS = 30
STARTUP_SETTLE_INTERVAL_SECONDS = 1
STARTUP_STABILITY_SAMPLES = 3
SWITCHER_ROW_TIMEOUT_MS = 30_000
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
DASHBOARD_ONLY_SIGNAL_TEXTS = (
    "Open Issues",
    "Issues in Progress",
    "Completed",
    "Team Velocity",
)
LANDING_SIGNAL_TEXTS = (
    "Connect GitHub",
    "Add workspace",
    "Saved workspaces",
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1005_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1005_failure.png"

REQUEST_STEPS = [
    "Launch the application URL in a clean browser session.",
    "Wait for the startup hydration sequence (WorkspaceHydrationService) to complete.",
    "Observe the current view and URL rendered by the application.",
    "Open the Workspace switcher from the application header.",
]
EXPECTED_RESULT = (
    "The application does not load the dashboard for the mismatched workspace. "
    "The user is redirected to the default landing state (for example, the setup "
    "or workspace selection screen). In the Workspace switcher, the mismatched "
    "workspace is marked as `Unavailable` and no longer has an `Active` label "
    "or indicator."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    _cleanup_local_workspace()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "startup_settle_timeout_seconds": STARTUP_SETTLE_TIMEOUT_SECONDS,
        "steps": [],
        "human_verification": [],
    }
    page: LiveWorkspaceSwitcherPage | None = None

    try:
        config = load_live_setup_test_config()
        result["app_url"] = config.app_url

        service = LiveSetupRepositoryService(config=config)
        token = service.token
        if not token:
            raise RuntimeError(
                "TS-1005 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        result["repository"] = service.repository
        result["repository_ref"] = service.ref

        workspace_state = _workspace_state(service.repository)
        result["preloaded_workspace_state"] = workspace_state

        runtime = StoredWorkspaceProfilesRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=(
                f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}",
            ),
        )
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime_observation = tracker_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["runtime_state"] = runtime_observation.kind
                result["runtime_body_text"] = runtime_observation.body_text
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app in a fresh Chromium session with the "
                        "mismatched saved local workspace preloaded as the active startup "
                        "target plus one hosted fallback workspace."
                    ),
                )

                try:
                    page.dismiss_connection_banner()
                except AssertionError:
                    pass

                startup_stability: dict[str, object] = {"signature": None, "count": 0}
                settled, startup_state = poll_until(
                    probe=lambda: _capture_startup_state(
                        tracker_page,
                        page,
                        startup_stability=startup_stability,
                    ),
                    is_satisfied=_startup_state_is_stable_final,
                    timeout_seconds=STARTUP_SETTLE_TIMEOUT_SECONDS,
                    interval_seconds=STARTUP_SETTLE_INTERVAL_SECONDS,
                )
                result["startup_state"] = startup_state
                if not settled:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "Startup hydration never reached a stable final post-hydration "
                            "state within the wait window.\n"
                            f"startup_state={json.dumps(startup_state, indent=2)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "Not reached because the application never exposed a stable "
                            "visible state for the post-hydration view check."
                        ),
                    )
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "Not reached because Workspace switcher could not be evaluated "
                            "without a stable post-hydration surface."
                        ),
                    )
                    raise AssertionError(
                        "Step 2 failed: startup hydration did not settle into a stable final "
                        "post-hydration state within the wait window.\n"
                        f"Observed startup state:\n{json.dumps(startup_state, indent=2)}"
                    )

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Waited for startup hydration to reach the same final visible "
                        f"state for {STARTUP_STABILITY_SAMPLES} consecutive samples "
                        "before evaluating the visible surface and workspace selection "
                        "state.\n"
                        f"startup_state={json.dumps(startup_state, indent=2)}"
                    ),
                )

                startup_surface = startup_state["startup_observation"]
                shell_observation = startup_state["shell_observation"]
                trigger_payload = startup_state.get("trigger")
                result["startup_observation"] = startup_surface
                result["shell_observation"] = shell_observation
                result["trigger_before_switcher"] = trigger_payload

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live post-startup page as a user would and noted the "
                        "visible URL, buttons, and main body text."
                    ),
                    observed=(
                        f"url={startup_surface['location_href']!r}; "
                        f"buttons={json.dumps(startup_surface['button_labels'], ensure_ascii=True)}; "
                        f"body_excerpt={_snippet(startup_surface['body_text'])!r}"
                    ),
                )

                step_3_failures = _current_view_failures(startup_state)
                if step_3_failures:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="\n".join(step_3_failures),
                    )
                else:
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "The visible post-hydration surface no longer looked like the "
                            "tracker dashboard and instead exposed landing-state cues.\n"
                            f"url={startup_surface['location_href']!r}\n"
                            f"buttons={json.dumps(startup_surface['button_labels'], indent=2)}\n"
                            f"body_excerpt={_snippet(startup_surface['body_text'])!r}"
                        ),
                    )

                switcher: WorkspaceSwitcherObservation | None = None
                local_row: WorkspaceSwitcherRowObservation | None = None
                refreshed_switcher: WorkspaceSwitcherObservation | None = None
                refreshed_local_row: WorkspaceSwitcherRowObservation | None = None
                selected_row: WorkspaceSwitcherRowObservation | None = None
                step_4_failures: list[str] = []

                if trigger_payload is None:
                    step_4_failures.append(
                        "Step 4 failed: the application header never exposed a visible "
                        "Workspace switcher trigger after startup hydration.\n"
                        f"startup_state={json.dumps(startup_state, indent=2)}"
                    )
                else:
                    trigger = page.observe_trigger(timeout_ms=15_000)
                    result["trigger_before_open"] = _trigger_payload(trigger)
                    switcher = page.open_and_observe(timeout_ms=20_000)
                    result["switcher_observation"] = _switcher_payload(switcher)
                    local_row = _find_seeded_local_row(switcher)
                    result["local_row"] = _row_payload(local_row)
                    try:
                        local_row = page.observe_saved_workspace_row(
                            display_name=LOCAL_DISPLAY_NAME,
                            target_path=LOCAL_TARGET,
                            target_type_label="Local",
                            expected_state_label="Unavailable",
                            timeout_ms=SWITCHER_ROW_TIMEOUT_MS,
                        )
                        result["observed_local_row"] = _row_payload(local_row)
                        refreshed_switcher = page.wait_for_refreshed_switcher_row_state(
                            display_name=LOCAL_DISPLAY_NAME,
                            target_path=LOCAL_TARGET,
                            target_type_label="Local",
                            expected_state_label="Unavailable",
                            timeout_ms=SWITCHER_ROW_TIMEOUT_MS,
                        )
                        result["refreshed_switcher_observation"] = _switcher_payload(
                            refreshed_switcher,
                        )
                        refreshed_local_row = _find_seeded_local_row(refreshed_switcher)
                        result["refreshed_local_row"] = _row_payload(refreshed_local_row)
                        selected_row = _find_selected_row(refreshed_switcher)
                        result["selected_row"] = _row_payload(selected_row)
                    except AssertionError as error:
                        step_4_failures.append(str(error))

                    _record_human_verification(
                        result,
                        check=(
                            "Opened Workspace switcher and read the broken local workspace "
                            "row and any active selection exactly as a user would."
                        ),
                        observed=(
                            f"trigger={json.dumps(result.get('trigger_before_open'), ensure_ascii=True)}; "
                            f"switcher={json.dumps(result.get('switcher_observation'), ensure_ascii=True)}; "
                            f"refreshed_local_row={json.dumps(result.get('refreshed_local_row'), ensure_ascii=True)}; "
                            f"selected_row={json.dumps(result.get('selected_row'), ensure_ascii=True)}"
                        ),
                    )

                    step_4_failures.extend(
                        _workspace_switcher_failures(
                            trigger=trigger,
                            switcher=refreshed_switcher or switcher,
                            local_row=refreshed_local_row or local_row,
                            selected_row=selected_row,
                        ),
                    )

                if step_4_failures:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed="\n".join(step_4_failures),
                    )
                else:
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "Workspace switcher showed the mismatched local workspace as "
                            "`Unavailable` without any remaining `Active` selection or "
                            "indicator.\n"
                            f"refreshed_local_row={json.dumps(result.get('refreshed_local_row'), indent=2)}\n"
                            f"selected_row={json.dumps(result.get('selected_row'), indent=2)}"
                        ),
                    )

                failures = [*step_3_failures, *step_4_failures]
                if failures:
                    raise AssertionError("\n\n".join(failures))

            except Exception:
                try:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                raise

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        result["failure_kind"] = "product"
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["failure_kind"] = "setup"
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": local_id,
        "migrationComplete": True,
        "unavailableLocalWorkspaceIds": [],
        "profiles": [
            {
                "id": local_id,
                "displayName": LOCAL_DISPLAY_NAME,
                "customDisplayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-22T23:55:00.000Z",
            },
        ],
    }


def _cleanup_local_workspace() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


def _capture_startup_state(
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    *,
    startup_stability: dict[str, object] | None = None,
) -> dict[str, object]:
    startup_observation = _startup_surface_payload(tracker_page.observe_startup_surface())
    shell_observation = tracker_page.observe_interactive_shell(SHELL_NAVIGATION_LABELS, timeout_ms=1_000)
    trigger = _safe_trigger_payload(page)
    looks_like_dashboard = _looks_like_dashboard_surface(
        startup_observation,
        shell_observation,
    )
    looks_like_landing = _looks_like_landing_surface(
        startup_observation,
        shell_observation,
    )
    state_kind = _startup_state_kind(
        trigger=trigger,
        looks_like_dashboard=looks_like_dashboard,
        looks_like_landing=looks_like_landing,
    )
    state_signature = _startup_state_signature(
        state_kind=state_kind,
        startup_observation=startup_observation,
        trigger=trigger,
    )
    consecutive_samples = (
        _record_stable_startup_sample(startup_stability, state_signature)
        if startup_stability is not None
        else 1
    )
    return {
        "startup_observation": startup_observation,
        "shell_observation": shell_observation,
        "trigger": trigger,
        "looks_like_dashboard": looks_like_dashboard,
        "looks_like_landing": looks_like_landing,
        "state_kind": state_kind,
        "state_signature": state_signature,
        "consecutive_samples": consecutive_samples,
    }


def _startup_state_is_stable_final(state: dict[str, object]) -> bool:
    state_kind = str(state.get("state_kind", ""))
    consecutive_samples = int(state.get("consecutive_samples", 0))
    return (
        state_kind in {"dashboard", "landing", "trigger-unavailable"}
        and consecutive_samples >= STARTUP_STABILITY_SAMPLES
    )


def _current_view_failures(startup_state: dict[str, object]) -> list[str]:
    startup_observation = startup_state["startup_observation"]
    shell_observation = startup_state["shell_observation"]
    failures: list[str] = []
    if bool(startup_state.get("looks_like_dashboard")):
        failures.append(
            "Step 3 failed: startup still rendered the dashboard for the mismatched "
            "workspace instead of returning to the default landing state.\n"
            f"Observed URL: {startup_observation['location_href']!r}\n"
            f"Observed buttons: {json.dumps(startup_observation['button_labels'], indent=2)}\n"
            f"Observed shell state: {json.dumps(shell_observation, indent=2)}\n"
            f"Observed body excerpt: {_snippet(startup_observation['body_text'])!r}"
        )
    elif not bool(startup_state.get("looks_like_landing")):
        failures.append(
            "Step 3 failed: the post-hydration surface was not the dashboard, but it also "
            "did not expose a clear landing-state UI that a user could continue from.\n"
            f"Observed URL: {startup_observation['location_href']!r}\n"
            f"Observed buttons: {json.dumps(startup_observation['button_labels'], indent=2)}\n"
            f"Observed shell state: {json.dumps(shell_observation, indent=2)}\n"
            f"Observed body excerpt: {_snippet(startup_observation['body_text'])!r}"
        )
    return failures


def _looks_like_dashboard_surface(
    startup_observation: dict[str, object],
    shell_observation: dict[str, object],
) -> bool:
    dashboard_signal_count = len(
        _matched_surface_signals(startup_observation, DASHBOARD_ONLY_SIGNAL_TEXTS),
    )
    return dashboard_signal_count >= 2 or (
        bool(shell_observation.get("shell_ready")) and dashboard_signal_count >= 1
    )


def _looks_like_landing_surface(
    startup_observation: dict[str, object],
    shell_observation: dict[str, object],
) -> bool:
    del shell_observation
    landing_signal_count = len(
        _matched_surface_signals(startup_observation, LANDING_SIGNAL_TEXTS),
    )
    dashboard_signal_count = len(
        _matched_surface_signals(startup_observation, DASHBOARD_ONLY_SIGNAL_TEXTS),
    )
    return landing_signal_count >= 1 and dashboard_signal_count == 0


def _workspace_switcher_failures(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation | None,
    local_row: WorkspaceSwitcherRowObservation | None,
    selected_row: WorkspaceSwitcherRowObservation | None,
) -> list[str]:
    failures: list[str] = []
    if switcher is None:
        failures.append(
            "Step 4 failed: Workspace switcher did not produce an observable panel state."
        )
        return failures
    if local_row is None:
        failures.append(
            "Step 4 failed: Workspace switcher did not expose the seeded mismatched local "
            "workspace row required for verification.\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}"
        )
        return failures

    if local_row.display_name != LOCAL_DISPLAY_NAME or LOCAL_TARGET not in local_row.detail_text:
        failures.append(
            "Step 4 failed: the row inspected in Workspace switcher did not match the "
            "seeded mismatched local workspace.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if local_row.state_label != "Unavailable":
        failures.append(
            "Step 4 failed: the mismatched local workspace row did not render the expected "
            "`Unavailable` state.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if "Local Git" in local_row.visible_text or "Local Git" in (local_row.semantics_label or ""):
        failures.append(
            "Step 4 failed: the mismatched local workspace still presented `Local Git` "
            "instead of the final unavailable recovery state.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if (
        local_row.selected
        or "Active" in local_row.visible_text
        or "Active" in local_row.action_labels
        or "Active" in local_row.button_labels
    ):
        failures.append(
            "Step 4 failed: Workspace switcher still showed the mismatched local workspace "
            "as selected / `Active` after startup hydration finished.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}\n"
            f"Observed selected row: {json.dumps(_row_payload(selected_row), indent=2)}"
        )
    if trigger.display_name == LOCAL_DISPLAY_NAME:
        failures.append(
            "Step 4 failed: the header Workspace switcher trigger still named the broken "
            "local workspace as the current selection instead of clearing the active "
            "workspace on redirect.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}"
        )
    return failures


def _startup_state_kind(
    *,
    trigger: dict[str, object] | None,
    looks_like_dashboard: bool,
    looks_like_landing: bool,
) -> str:
    if looks_like_landing:
        return "landing"
    if looks_like_dashboard:
        return "dashboard"
    if (
        isinstance(trigger, dict)
        and str(trigger.get("state_label", "")).strip() == "Unavailable"
    ):
        return "trigger-unavailable"
    return "indeterminate"


def _startup_state_signature(
    *,
    state_kind: str,
    startup_observation: dict[str, object],
    trigger: dict[str, object] | None,
) -> str:
    return json.dumps(
        {
            "state_kind": state_kind,
            "location_href": startup_observation.get("location_href"),
            "button_labels": startup_observation.get("button_labels"),
            "body_excerpt": _snippet(str(startup_observation.get("body_text", ""))),
            "trigger_display_name": None if trigger is None else trigger.get("display_name"),
            "trigger_state_label": None if trigger is None else trigger.get("state_label"),
        },
        sort_keys=True,
    )


def _record_stable_startup_sample(
    tracker: dict[str, object],
    signature: str,
) -> int:
    previous_signature = tracker.get("signature")
    if previous_signature == signature:
        next_count = int(tracker.get("count", 0)) + 1
    else:
        next_count = 1
    tracker["signature"] = signature
    tracker["count"] = next_count
    return next_count


def _matched_surface_signals(
    startup_observation: dict[str, object],
    signals: tuple[str, ...],
) -> tuple[str, ...]:
    body_text = str(startup_observation.get("body_text", ""))
    button_labels = [str(label) for label in startup_observation.get("button_labels", [])]
    return tuple(
        signal
        for signal in signals
        if signal in body_text or signal in button_labels
    )


def _startup_surface_payload(observation: StartupSurfaceObservation) -> dict[str, object]:
    return {
        "title": observation.title,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "body_text": observation.body_text,
        "button_labels": list(observation.button_labels),
    }


def _switcher_payload(observation: WorkspaceSwitcherObservation | None) -> dict[str, object] | None:
    if observation is None:
        return None
    return {
        "body_text": observation.body_text,
        "switcher_text": observation.switcher_text,
        "row_count": observation.row_count,
        "rows": [_row_payload(row) for row in observation.rows],
    }


def _trigger_payload(observation: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": observation.semantic_label,
        "visible_text": observation.visible_text,
        "display_name": observation.display_name,
        "workspace_type": observation.workspace_type,
        "state_label": observation.state_label,
        "top_button_labels": list(observation.top_button_labels),
    }


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, object] | None:
    try:
        return _trigger_payload(page.observe_trigger(timeout_ms=1_000))
    except (AssertionError, WebAppTimeoutError):
        return None


def _row_payload(row: WorkspaceSwitcherRowObservation | None) -> dict[str, object] | None:
    if row is None:
        return None
    return {
        "display_name": row.display_name,
        "target_type_label": row.target_type_label,
        "state_label": row.state_label,
        "detail_text": row.detail_text,
        "visible_text": row.visible_text,
        "selected": row.selected,
        "semantics_label": row.semantics_label,
        "icon_accessibility_label": row.icon_accessibility_label,
        "action_labels": list(row.action_labels),
        "button_labels": list(row.button_labels),
    }


def _find_seeded_local_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if (
            row.display_name == LOCAL_DISPLAY_NAME
            and row.target_type_label == "Local"
            and LOCAL_TARGET in row.detail_text
        ):
            return row
    return None


def _find_selected_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if row.selected or "Active" in row.action_labels or "Active" in row.button_labels:
            return row
    return None


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if not isinstance(steps, list):
        raise TypeError("result['steps'] must be a list")
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        },
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    if not isinstance(checks, list):
        raise TypeError("result['human_verification'] must be a list")
    checks.append({"check": check, "observed": observed})


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    if result.get("failure_kind") == "product":
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was automated",
        "* Preloaded a broken saved local workspace as the active startup target, plus one hosted fallback workspace, in browser storage.",
        f"* Waited up to {STARTUP_SETTLE_TIMEOUT_SECONDS} seconds for startup hydration to settle before judging the visible surface.",
        "* Verified the current visible URL and page content did not keep the user on the dashboard for the broken workspace.",
        "* Opened Workspace switcher and verified the broken local workspace resolved to {code}Unavailable{code} without still showing {code}Active{code}.",
        "",
        "h4. Automation checks",
        *_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot*: {result['screenshot']}"])
    if not passed:
        lines.extend(
            [
                "",
                "h4. Assertion / error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_pr_body(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        f"## {TICKET_KEY} passed" if passed else f"## {TICKET_KEY} failed",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Preloaded the broken local workspace as the active startup target plus a hosted fallback workspace.",
        f"- Waited up to {STARTUP_SETTLE_TIMEOUT_SECONDS} seconds for startup hydration to settle before asserting the post-startup view.",
        "- Verified the current visible route and surface did not keep the user on the broken workspace dashboard.",
        "- Opened Workspace switcher and checked the broken local workspace row for `Unavailable` without any remaining `Active` indicator.",
        "",
        "## Automation checks",
        *_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *_human_lines(result, jira=False),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        _actual_result_summary(result, passed=passed),
    ]
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Outcome*",
        (
            "* PASSED — startup redirected away from the broken workspace dashboard and Workspace switcher cleared the stale active selection."
            if passed
            else f"* FAILED — {result.get('error', 'The deployed app did not expose the expected landing-state redirect.')}"
        ),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_bug_description(result: dict[str, object]) -> str:
    annotated_steps: list[str] = []
    steps = result.get("steps", [])
    for index, action in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and int(step.get("step", -1)) == index
            ),
            None,
        )
        if matching is None:
            annotated_steps.append(f"{index}. ⏭️ {action} Not reached.")
            continue
        icon = "✅" if str(matching.get("status")) == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}"
        )

    startup_observation = result.get("startup_observation")
    trigger_before_open = result.get("trigger_before_open") or result.get("trigger_before_switcher")
    refreshed_local_row = result.get("refreshed_local_row") or result.get("observed_local_row") or result.get("local_row")
    selected_row = result.get("selected_row")
    actual_summary = (
        "- **Actual:** navigating to the live app kept the user on the tracker dashboard "
        "at the root URL instead of redirecting to the landing surface, and Workspace "
        "switcher still showed the mismatched local workspace row as selected with an "
        "`Active` action even though its state label was `Unavailable`."
    )
    lines = [
        f"# {TICKET_KEY} bug report",
        "",
        "## Steps to reproduce",
        *annotated_steps,
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        actual_summary,
        "",
        "## Exact missing/broken production capability",
        (
            "- When startup hydration resolves the previously active local workspace to "
            "`Unavailable`, the production app does not clear the active workspace "
            "selection or return to the landing surface. The dashboard still renders for "
            "the broken workspace, and Workspace switcher still exposes the broken row as "
            "`Active`."
        ),
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Failing command",
        f"- `{RUN_COMMAND}`",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`" if result.get("screenshot") else "- Screenshot: not captured",
        f"- Startup observation: `{json.dumps(startup_observation, ensure_ascii=True)}`",
        f"- Trigger observation: `{json.dumps(trigger_before_open, ensure_ascii=True)}`",
        f"- Switcher observation: `{json.dumps(result.get('switcher_observation'), ensure_ascii=True)}`",
        f"- Refreshed local row: `{json.dumps(refreshed_local_row, ensure_ascii=True)}`",
        f"- Selected row: `{json.dumps(selected_row, ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        local_row = result.get("refreshed_local_row", result.get("observed_local_row"))
        return (
            "Startup hydration redirected away from the broken workspace dashboard and "
            "Workspace switcher showed the mismatched local workspace as `Unavailable` "
            f"without any remaining `Active` indicator. Observed row: {local_row}"
        )
    return str(
        result.get(
            "error",
            "The deployed app did not expose the expected landing-state redirect.",
        ),
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        if jira:
            lines.append(
                f"# Step {step['step']} *{str(step['status']).upper()}*: {step['action']}\n"
                f"Observed: {{{{code}}}}{step['observed']}{{{{code}}}}",
            )
        else:
            lines.append(
                f"- Step {step['step']} **{step['status']}** — {step['action']}  \n"
                f"  Observed: `{step['observed']}`",
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        if not isinstance(entry, dict):
            continue
        if jira:
            lines.append(
                f"* {entry['check']} Observed: {{{{code}}}}{entry['observed']}{{{{code}}}}",
            )
        else:
            lines.append(f"- **{entry['check']}** Observed: `{entry['observed']}`")
    return lines


def _snippet(text: str, *, limit: int = 300) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


if __name__ == "__main__":
    main()
