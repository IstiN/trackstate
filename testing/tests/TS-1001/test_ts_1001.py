from __future__ import annotations

import json
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_create_issue_gate_page import (  # noqa: E402
    CreateIssueGateObservation,
    LiveCreateIssueGatePage,
)
from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.delayed_auth_workspace_profiles_runtime import (  # noqa: E402
    DelayedAuthWorkspaceProfilesRuntime,
)
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    ShellReadyTransitionTracker,
    build_annotated_steps,
    build_workspace_state,
    format_human_lines,
    format_step_lines,
    observe_live_startup_shell_window,
    prepare_local_workspace_repository,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    relative_startup_event_seconds,
    safe_trigger_payload,
    snippet,
    startup_surface_payload,
    trigger_payload,
    write_test_automation_result,
)

TICKET_KEY = "TS-1001"
TEST_CASE_TITLE = "Fallback state session — capabilities are restricted after 11s startup timeout"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1001/test_ts_1001.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1001-local"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SYNC_TIMEOUT_SECONDS = 11
SIMULATED_PROBE_DELAY_SECONDS = 30
TIMEOUT_ASSERTION_SECONDS = SYNC_TIMEOUT_SECONDS + 1
AUTH_PROBE_START_WAIT_SECONDS = 60
STARTUP_RENDER_WAIT_SECONDS = 60
OBSERVATION_TIMEOUT_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + 10
POLL_INTERVAL_SECONDS = 0.5
LINKED_BUGS = ["TS-1022", "TS-1014", "TS-1013", "TS-1012", "TS-996", "TS-992"]
REVIEW_THREADS = (
    {"inReplyToId": 3306440550, "threadId": "PRRT_kwDOSU6Gf86E6IGq"},
    {"inReplyToId": 3306440710, "threadId": "PRRT_kwDOSU6Gf86E6IIj"},
)
WORKSPACE_PROFILE_STATE_KEYS = TrackStateTrackerPage.WORKSPACE_PROFILE_STATE_KEYS
LINKED_BUG_NOTES = (
    "Reviewed TS-1022, TS-1014, TS-1013, TS-1012, TS-996, and TS-992. The linked "
    "startup fixes all depend on real delayed `/user` timing, so this test waits "
    "past the 11-second timeout, proves the live `/user` request actually started, "
    "and samples the same browser session while that request is still pending."
)
REWORK_SUMMARY_ITEMS = (
    "Started the live scenario from the local workspace so the delayed GitHub `/user` "
    "startup probe is exercised deterministically, then switched into the hosted "
    "workspace after `shell_ready` to inspect the fallback state.",
    "Moved the Step 4 capability scan behind `TrackStateTrackerPage` so the "
    "ticket flow depends on a reusable page component instead of raw browser "
    "session evaluation.",
    "Scoped capability matches to the active hosted workspace contract; only "
    "same-session evidence for the exercised hosted fallback workspace can "
    "satisfy `canWrite=false` and `canCreateBranch=false`.",
    "If the live app still exposes only indirect evidence like the blocked Create "
    "issue gate plus `hostedAccessMode=disconnected`, the test fails as a real "
    "product gap instead of reporting a false-positive pass.",
)

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Wait for the 11-second synchronization timeout to expire and the UI shell to render (shell_ready=true).",
    "Access the session metadata or inspect the state of a write-enabled action (e.g., 'Save' or 'Create Branch').",
    "Verify the 'canWrite' and 'canCreateBranch' flags are set to false.",
]
EXPECTED_RESULT = (
    "The application enters the shell_ready state, but the session reflects the "
    "default fallback state with restricted capabilities, ensuring data integrity "
    "is maintained while the authentication remains unresolved."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1001_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1001_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1001 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    expected_hosted_workspace_id = next(
        str(profile["id"])
        for profile in workspace_state["profiles"]
        if isinstance(profile, dict) and profile.get("targetType") == "hosted"
    )
    runtime = DelayedAuthWorkspaceProfilesRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=SIMULATED_PROBE_DELAY_SECONDS,
        delayed_paths=("/user",),
        workspace_token_profile_ids=(expected_hosted_workspace_id,),
    )

    result: dict[str, Any] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "linked_bug_notes": LINKED_BUG_NOTES,
        "sync_timeout_seconds": SYNC_TIMEOUT_SECONDS,
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
        "timeout_assertion_seconds": TIMEOUT_ASSERTION_SECONDS,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "expected_hosted_workspace_id": expected_hosted_workspace_id,
        "auth_probe_observed": False,
        "startup_probe_missing": False,
        "startup_probe_late": False,
        "product_failure": False,
        "steps": [],
        "human_verification": [],
    }

    tracker_page: TrackStateTrackerPage | None = None
    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            switcher_page = LiveWorkspaceSwitcherPage(tracker_page)
            create_gate_page = LiveCreateIssueGatePage(tracker_page)
            startup_started_at_monotonic = time.monotonic()
            failures: list[str] = []

            switcher_page.set_viewport(**DESKTOP_VIEWPORT)
            tracker_page.open_entrypoint()
            result["startup_observation_initial"] = _startup_surface_payload(tracker_page)

            startup_rendered, startup_surface = poll_until(
                probe=lambda: _startup_surface_payload(tracker_page),
                is_satisfied=_startup_surface_loaded,
                timeout_seconds=STARTUP_RENDER_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["startup_observation_after_render"] = startup_surface
            if not startup_rendered:
                step_one_error = (
                    "Step 1 failed: the deployed app never rendered beyond the bare "
                    "startup title before the delayed-auth fallback scenario began.\n"
                    f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}"
                )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=step_one_error,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the deployed page during startup and checked whether it "
                        "moved beyond the bare title into a user-visible shell."
                    ),
                    observed=(
                        f"startup_surface={json.dumps(startup_surface, ensure_ascii=True)}; "
                        f"screenshot={result['screenshot']!r}"
                    ),
                )
                _record_not_reached_steps(result, starting_step=2)
                raise AssertionError(step_one_error)

            if not runtime.wait_for_auth_probe_start(timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS):
                late_surface = _startup_surface_payload(tracker_page)
                trigger = _safe_trigger_payload(switcher_page)
                result["startup_observation_late"] = late_surface
                result["trigger_observation"] = trigger
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)
                late_start_seconds = relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    runtime.auth_probe_started_at_monotonic,
                )
                if runtime.delayed_request_urls or runtime.auth_probe_started_at_monotonic is not None:
                    result["startup_probe_late"] = True
                    result["product_failure"] = True
                    step_one_error = (
                        "Step 1 failed: the delayed GitHub `/user` request did not start "
                        "within the startup observation window. It only appeared after the "
                        "app had already issued other repository bootstrap requests, so the "
                        "TS-1001 delayed-auth startup scenario was not exercised as a startup "
                        "probe.\n"
                        f"Observed GitHub requests:\n{json.dumps(result['github_request_urls'], indent=2)}\n"
                        f"Observed delayed requests:\n{json.dumps(result['delayed_request_urls'], indent=2)}\n"
                        f"auth_probe_started_after_start_seconds={late_start_seconds!r}\n"
                        f"Observed startup surface:\n{json.dumps(late_surface, indent=2)}\n"
                        f"Observed trigger:\n{json.dumps(trigger, indent=2) if trigger else 'null'}\n"
                        f"Observed body text:\n{tracker_page.body_text()}"
                    )
                elif runtime.github_request_urls:
                    result["startup_probe_missing"] = True
                    result["product_failure"] = True
                    step_one_error = (
                        "Step 1 failed: the deployed app never issued the required GitHub "
                        "`/user` startup auth probe. Startup only requested other GitHub "
                        "endpoints, so the TS-1001 delayed-auth fallback scenario cannot be "
                        "exercised from the current production surface.\n"
                        f"Observed GitHub requests:\n{json.dumps(result['github_request_urls'], indent=2)}\n"
                        f"Observed delayed requests:\n{json.dumps(result['delayed_request_urls'], indent=2)}\n"
                        f"Observed startup surface:\n{json.dumps(late_surface, indent=2)}\n"
                        f"Observed trigger:\n{json.dumps(trigger, indent=2) if trigger else 'null'}\n"
                        f"Observed body text:\n{tracker_page.body_text()}"
                    )
                else:
                    step_one_error = (
                        "Step 1 failed: the delayed GitHub `/user` startup probe never "
                        "started, so the 11-second startup-timeout fallback scenario was not "
                        "exercised.\n"
                        f"Observed startup surface:\n{json.dumps(late_surface, indent=2)}\n"
                        f"Observed trigger:\n{json.dumps(trigger, indent=2) if trigger else 'null'}\n"
                        f"Observed body text:\n{tracker_page.body_text()}"
                    )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=step_one_error,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live startup shell like a user and checked whether the "
                        "current production build ever issued the required delayed GitHub "
                        "`/user` startup auth probe."
                    ),
                    observed=(
                        f"github_request_urls={json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}; "
                        f"delayed_request_urls={json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}; "
                        f"trigger={json.dumps(trigger, ensure_ascii=True) if trigger else 'null'}; "
                        f"body_excerpt={_snippet(tracker_page.body_text())!r}; "
                        f"screenshot={result['screenshot']!r}"
                    ),
                )
                _record_not_reached_steps(result, starting_step=2)
                raise AssertionError(step_one_error)
            result["auth_probe_observed"] = True

            auth_probe_started_after_start_seconds = relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.auth_probe_started_at_monotonic,
            )
            result["auth_probe_started_after_start_seconds"] = (
                auth_probe_started_after_start_seconds
            )
            _record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app with preloaded local and hosted "
                    "workspaces, started from the local workspace, and delayed the GitHub "
                    f"`/user` startup probe by {SIMULATED_PROBE_DELAY_SECONDS} seconds.\n"
                    f"startup_surface={json.dumps(startup_surface, ensure_ascii=True)}; "
                    f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
                    f"delayed_request_urls={runtime.delayed_request_urls!r}"
                ),
            )

            transition_tracker = ShellReadyTransitionTracker()
            timeout_reached, timeout_window = poll_until(
                probe=lambda: _observe_timeout_window(
                    tracker_page=tracker_page,
                    page=switcher_page,
                    runtime=runtime,
                    startup_started_at_monotonic=startup_started_at_monotonic,
                    transition_tracker=transition_tracker,
                ),
                is_satisfied=lambda observation: (
                    observation["elapsed_since_auth_start_seconds"] is not None
                    and float(observation["elapsed_since_auth_start_seconds"])
                    >= TIMEOUT_ASSERTION_SECONDS
                ),
                timeout_seconds=OBSERVATION_TIMEOUT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["github_request_urls"] = list(runtime.github_request_urls)
            result["delayed_request_urls"] = list(runtime.delayed_request_urls)
            result["timeout_window_observation"] = _sample_payload(timeout_window)

            step_two_error: str | None = None
            if not timeout_reached:
                step_two_error = (
                    "Step 2 failed: the test never reached the post-timeout observation "
                    "window while watching the delayed GitHub `/user` probe.\n"
                    f"Observed timeout window:\n{json.dumps(_sample_payload(timeout_window), indent=2)}"
                )
            elif not bool(timeout_window["auth_pending"]):
                shell_ready_after_start_seconds = timeout_window.get(
                    "shell_ready_after_start_seconds",
                )
                auth_probe_released_after_start_seconds = timeout_window.get(
                    "auth_probe_released_after_start_seconds",
                )
                if (
                    isinstance(shell_ready_after_start_seconds, (int, float))
                    and isinstance(auth_probe_released_after_start_seconds, (int, float))
                    and shell_ready_after_start_seconds > SYNC_TIMEOUT_SECONDS
                    and shell_ready_after_start_seconds
                    >= auth_probe_released_after_start_seconds
                ):
                    step_two_error = (
                        "Step 2 failed: the delayed GitHub `/user` probe started, but the "
                        "app did not enter `shell_ready` within the 11-second timeout "
                        "window. Instead, the shell only became ready after the delayed "
                        "auth probe was released, so the TS-996 timeout fallback regressed.\n"
                        f"Observed timeout window:\n{json.dumps(_sample_payload(timeout_window), indent=2)}"
                    )
                else:
                    step_two_error = (
                        "Step 2 failed: by the time the timeout assertion ran, the delayed "
                        "GitHub `/user` probe was no longer pending, so the unresolved-auth "
                        "fallback state was not observed.\n"
                        f"Observed timeout window:\n{json.dumps(_sample_payload(timeout_window), indent=2)}"
                    )
            elif not bool(timeout_window["shell_observation"]["shell_ready"]):
                step_two_error = (
                    "Step 2 failed: after waiting beyond the 11-second startup timeout, "
                    "the live page still had not reached shell_ready.\n"
                    f"Observed timeout window:\n{json.dumps(_sample_payload(timeout_window), indent=2)}"
                )
            else:
                try:
                    _assert_interactive_shell(timeout_window)
                except AssertionError as error:
                    step_two_error = f"Step 2 failed: {error}"

            if step_two_error is None:
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"Waited {timeout_window['elapsed_since_auth_start_seconds']!r} "
                        "seconds from the delayed `/user` probe start, which is beyond "
                        f"the {SYNC_TIMEOUT_SECONDS}-second startup timeout. The auth "
                        "probe was still pending and the live app already exposed the "
                        "interactive shell.\n"
                        f"shell_ready_after_start_seconds={timeout_window['shell_ready_after_start_seconds']!r}; "
                        f"trigger={json.dumps(timeout_window['trigger'], ensure_ascii=True)}"
                    ),
                )
            else:
                failures.append(step_two_error)
                result["product_failure"] = True
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=step_two_error,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live shell after startup and compared the shell-ready "
                        "timing against the delayed GitHub `/user` probe lifecycle."
                    ),
                    observed=(
                        f"timeout_window={json.dumps(_sample_payload(timeout_window), ensure_ascii=True)}; "
                        f"github_request_urls={json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}; "
                        f"delayed_request_urls={json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}"
                    ),
                )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                _record_not_reached_steps(result, starting_step=3)
                raise AssertionError(step_two_error)

            current_trigger = timeout_window.get("trigger")
            already_hosted_fallback = (
                isinstance(current_trigger, dict)
                and current_trigger.get("display_name") == HOSTED_DISPLAY_NAME
                and current_trigger.get("workspace_type") == "Hosted"
                and current_trigger.get("state_label") == "Needs sign-in"
            )

            try:
                if already_hosted_fallback:
                    result["hosted_trigger_after_switch"] = current_trigger
                    result["trigger_observation"] = current_trigger
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "At the timeout checkpoint the hosted fallback workspace was "
                            "already active, so no workspace switch was required before "
                            "inspecting restricted-capability evidence.\n"
                            f"trigger={json.dumps(current_trigger, ensure_ascii=True)}"
                        ),
                    )
                else:
                    hosted_trigger = switcher_page.switch_to_workspace(
                        display_name=HOSTED_DISPLAY_NAME,
                        target_type_label="Hosted",
                        detail_contains=service.repository,
                        expected_state_label="Needs sign-in",
                        timeout_ms=20_000,
                    )
                    trigger_observation = switcher_page.observe_trigger(timeout_ms=10_000)
                    switcher_observation = switcher_page.open_and_observe(timeout_ms=10_000)
                    active_row = _active_row(switcher_observation)
                    result["hosted_trigger_after_switch"] = _trigger_payload(hosted_trigger)
                    result["trigger_observation"] = _trigger_payload(trigger_observation)
                    result["switcher_observation"] = _switcher_payload(switcher_observation)
                    result["active_row_observation"] = _row_payload(active_row)
                    _assert_fallback_workspace_state(
                        runtime=runtime,
                        trigger=trigger_observation,
                        active_row=active_row,
                    )
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            "Switched from the local startup shell into the hosted workspace "
                            "while the delayed auth probe was still unresolved. The workspace "
                            "trigger and the selected hosted row both exposed the exact "
                            "`Needs sign-in` fallback state.\n"
                            f"trigger_label={trigger_observation.semantic_label!r}; "
                            f"active_row={json.dumps(result['active_row_observation'], ensure_ascii=True)}"
                        ),
                    )
            except Exception as error:
                step_three_error = (
                    "Step 3 failed: the test could not switch into the hosted fallback "
                    "workspace state while authentication was still unresolved.\n"
                    f"error={error}\n"
                    f"hosted_trigger_after_switch="
                    f"{json.dumps(result.get('hosted_trigger_after_switch'), ensure_ascii=True)}\n"
                    f"trigger_observation={json.dumps(result.get('trigger_observation'), ensure_ascii=True)}\n"
                    f"switcher_observation={json.dumps(result.get('switcher_observation'), ensure_ascii=True)}"
                )
                failures.append(step_three_error)
                result["product_failure"] = True
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=step_three_error,
                )

            try:
                create_gate_page.wait_for_create_trigger(timeout_ms=10_000)
                create_gate_page.open_create_issue(timeout_ms=10_000)
                gate_observation = create_gate_page.wait_for_access_gate(
                    primary_action_label="Open settings",
                    timeout_ms=10_000,
                )
                result["create_issue_gate_observation"] = _create_gate_payload(gate_observation)
                _assert_write_gate(runtime=runtime, gate=gate_observation)
                workspace_profile_state = _read_workspace_profile_state(
                    tracker_page,
                    expected_hosted_workspace_id=expected_hosted_workspace_id,
                )
                result["workspace_profile_state"] = workspace_profile_state
                _assert_workspace_profile_state(
                    runtime=runtime,
                    observation=workspace_profile_state,
                )
                public_capability_surface = tracker_page.observe_public_capability_surface(
                    expected_workspace_id=expected_hosted_workspace_id,
                    expected_repository=service.repository,
                )
                result["public_capability_surface"] = public_capability_surface
                _assert_public_capability_surface(
                    runtime=runtime,
                    surface=public_capability_surface,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "Opened the user-visible Create issue action after the timeout, "
                        "confirmed the live app kept write operations blocked, and also "
                        "found a same-session public capability surface that explicitly "
                        "kept `canWrite=false` and `canCreateBranch=false` while the "
                        "delayed auth probe was still pending.\n"
                        f"gate={json.dumps(result['create_issue_gate_observation'], ensure_ascii=True)}\n"
                        f"workspace_profile_state={json.dumps(workspace_profile_state, ensure_ascii=True)}\n"
                        f"public_capability_surface={json.dumps(public_capability_surface, ensure_ascii=True)}"
                    ),
                )
            except Exception as error:
                step_four_error = (
                    "Step 4 failed: the live browser session did not expose a same-session "
                    "public capability surface that proves `canWrite=false` and "
                    "`canCreateBranch=false` while auth remained unresolved.\n"
                    f"error={error}\n"
                    f"create_issue_gate_observation="
                    f"{json.dumps(result.get('create_issue_gate_observation'), ensure_ascii=True)}\n"
                    f"workspace_profile_state="
                    f"{json.dumps(result.get('workspace_profile_state'), ensure_ascii=True)}\n"
                    f"public_capability_surface="
                    f"{json.dumps(result.get('public_capability_surface'), ensure_ascii=True)}\n"
                    f"body_text={tracker_page.body_text()}"
                )
                failures.append(step_four_error)
                error_text = str(error)
                if result.get("auth_probe_observed") and not any(
                    marker in error_text
                    for marker in (
                        "probe could not be analyzed",
                        "did not return a structured payload",
                        "did not expose the session payload",
                    )
                ):
                    result["product_failure"] = True
                _record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=step_four_error,
                )

            _record_human_verification(
                result,
                check=(
                    "Viewed the deployed page after the timeout like a user and checked "
                    "the visible shell, branding, navigation, and active hosted workspace state."
                ),
                observed=(
                    f"body_excerpt={_snippet(timeout_window['shell_observation']['body_text'])!r}; "
                    f"branding_visible={timeout_window['branding_visible']!r}; "
                    f"visible_navigation_labels={timeout_window['shell_observation']['visible_navigation_labels']!r}; "
                    f"workspace_trigger_state={(result.get('trigger_observation') or {}).get('state_label')!r}"
                ),
            )
            if result.get("create_issue_gate_observation"):
                gate_payload = result["create_issue_gate_observation"]
                _record_human_verification(
                    result,
                    check=(
                        "Opened the visible Create issue action and confirmed the user sees "
                        "a read-only recovery gate instead of an editable issue form."
                    ),
                    observed=(
                        f"gate_panel_text={gate_payload.get('gate_panel_text')!r}; "
                        f"open_settings_button_count={gate_payload.get('gate_open_settings_button_count')!r}; "
                        f"summary_field_count={gate_payload.get('summary_field_count')!r}; "
                        f"save_button_count={gate_payload.get('save_button_count')!r}"
                    ),
                )

            if failures:
                raise AssertionError("\n\n".join(failures))

            tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            _write_pass_outputs(result)
            print(f"{TICKET_KEY} passed")
            return
    except AssertionError as error:
        if tracker_page is not None:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        if tracker_page is not None:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _record_step(
    result: dict[str, Any],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    record_step(result, step=step, status=status, action=action, observed=observed)


def _record_human_verification(
    result: dict[str, Any],
    *,
    check: str,
    observed: str,
) -> None:
    record_human_verification(result, check=check, observed=observed)


def _record_not_reached_steps(result: dict[str, Any], *, starting_step: int) -> None:
    record_not_reached_steps(result, starting_step=starting_step, request_steps=REQUEST_STEPS)


def _workspace_state(repository: str) -> dict[str, object]:
    return build_workspace_state(
        repository,
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        local_display_name=LOCAL_DISPLAY_NAME,
        hosted_display_name=HOSTED_DISPLAY_NAME,
    )


def _prepare_local_workspace_repository() -> dict[str, object]:
    return prepare_local_workspace_repository(
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        marker_filename=".trackstate-ts1001-precondition.txt",
        marker_contents="Prepared for TS-1001 delayed startup fallback validation.\n",
        commit_author_name="TS-1001 Automation",
        commit_author_email="ts1001@example.com",
        commit_message="Prepare TS-1001 local workspace",
    )


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    return startup_surface_payload(tracker_page)


def _startup_surface_loaded(observation: dict[str, Any]) -> bool:
    body_text = str(observation.get("body_text", "")).strip()
    title = str(observation.get("title", "")).strip()
    button_labels = observation.get("button_labels", [])
    return bool(button_labels) or (len(body_text) > len(title) and body_text != title)


def _observe_timeout_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
) -> dict[str, Any]:
    return observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
        transition_tracker=transition_tracker,
    )


def _assert_interactive_shell(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "The timeout-window snapshot did not expose the full interactive shell "
            f"navigation. Missing labels: {missing_navigation}.",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "The timeout-window snapshot did not expose the header workspace trigger.",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "The timeout-window snapshot did not expose visible TrackState branding.",
        )


def _active_row(
    switcher_observation: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    return next(
        (row for row in switcher_observation.rows if row.selected),
        None,
    )


def _assert_fallback_workspace_state(
    *,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    trigger: WorkspaceSwitcherTriggerObservation,
    active_row: WorkspaceSwitcherRowObservation | None,
) -> None:
    if not runtime.auth_probe_pending:
        raise AssertionError(
            "The delayed auth probe was no longer pending while the fallback workspace "
            "state was being inspected.",
        )
    if trigger.state_label != "Needs sign-in":
        raise AssertionError(
            "The active workspace trigger did not expose the expected `Needs sign-in` "
            f"fallback state. Observed trigger state: {trigger.state_label!r}",
        )
    if active_row is None:
        raise AssertionError(
            "The workspace switcher did not expose a selected active workspace row.",
        )
    if active_row.target_type_label != "Hosted":
        raise AssertionError(
            "The selected active workspace row was not the hosted workspace expected by "
            f"the test. Observed row: {active_row!r}",
        )
    if active_row.state_label != "Needs sign-in":
        raise AssertionError(
            "The selected hosted workspace row did not expose the expected "
            f"`Needs sign-in` fallback state. Observed row: {active_row!r}",
        )


def _assert_write_gate(
    *,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    gate: CreateIssueGateObservation,
) -> None:
    if not runtime.auth_probe_pending:
        raise AssertionError(
            "The delayed auth probe was no longer pending while the blocked write gate "
            "was being inspected.",
        )
    if "GitHub write access is not connected" not in gate.gate_panel_text:
        raise AssertionError(
            "The Create issue gate did not show the expected disconnected write-access "
            f"title. Observed gate: {gate.gate_panel_text!r}",
        )
    if "Create, edit, comment, and status changes stay read-only" not in gate.gate_panel_text:
        raise AssertionError(
            "The Create issue gate did not show the expected read-only write restriction "
            f"message. Observed gate: {gate.gate_panel_text!r}",
        )
    if gate.summary_field_count != 0:
        raise AssertionError(
            "The Create issue gate still exposed an editable Summary field instead of a "
            f"blocked write-access surface. Observed summary_field_count={gate.summary_field_count!r}",
        )
    if gate.save_button_count != 0:
        raise AssertionError(
            "The Create issue gate still exposed a Save action even though the fallback "
            f"session should be write-blocked. Observed save_button_count={gate.save_button_count!r}",
        )
    if gate.gate_open_settings_button_count < 1:
        raise AssertionError(
            "The Create issue gate did not expose the expected `Open settings` recovery "
            f"action. Observed gate={gate!r}",
        )


def _read_workspace_profile_state(
    tracker_page: TrackStateTrackerPage,
    *,
    expected_hosted_workspace_id: str,
) -> dict[str, Any]:
    snapshot = tracker_page.snapshot_local_storage(WORKSPACE_PROFILE_STATE_KEYS)
    raw_state = next(
        (
            raw_value
            for key in WORKSPACE_PROFILE_STATE_KEYS
            if (raw_value := snapshot.get(key))
        ),
        None,
    )
    parsed_state: dict[str, Any] | None = None
    parse_error: str | None = None
    if raw_state is not None:
        try:
            candidate = json.loads(raw_state)
            if isinstance(candidate, dict):
                parsed_state = candidate
            else:
                parse_error = (
                    "Workspace profile storage did not deserialize to a JSON object. "
                    f"Observed type: {type(candidate).__name__}."
                )
        except json.JSONDecodeError as error:
            parse_error = f"{type(error).__name__}: {error}"

    active_workspace_id = (
        str(parsed_state.get("activeWorkspaceId"))
        if isinstance(parsed_state, dict) and parsed_state.get("activeWorkspaceId") is not None
        else None
    )
    hosted_profile: dict[str, Any] | None = None
    raw_profiles = parsed_state.get("profiles") if isinstance(parsed_state, dict) else None
    if isinstance(raw_profiles, list):
        hosted_profile = next(
            (
                profile
                for profile in raw_profiles
                if isinstance(profile, dict)
                and str(profile.get("id", "")).strip() == expected_hosted_workspace_id
            ),
            None,
        )
    return {
        "snapshot": snapshot,
        "raw_state": raw_state,
        "parse_error": parse_error,
        "active_workspace_id": active_workspace_id,
        "hosted_profile": hosted_profile,
        "hosted_access_mode": (
            None
            if hosted_profile is None
            else str(hosted_profile.get("hostedAccessMode"))
            if hosted_profile.get("hostedAccessMode") is not None
            else None
        ),
    }


def _assert_workspace_profile_state(
    *,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    observation: dict[str, Any],
) -> None:
    if not runtime.auth_probe_pending:
        raise AssertionError(
            "The delayed auth probe was no longer pending while the same-session hosted "
            "workspace access mode was being inspected.",
        )
    parse_error = observation.get("parse_error")
    if parse_error:
        raise AssertionError(
            "The browser session did not expose a parseable workspace profile state "
            f"snapshot in localStorage.\nobservation={json.dumps(observation, ensure_ascii=True)}",
        )
    active_workspace_id = observation.get("active_workspace_id")
    if not active_workspace_id:
        raise AssertionError(
            "The live browser session did not persist an active workspace id while the "
            "fallback state was visible.\n"
            f"observation={json.dumps(observation, ensure_ascii=True)}",
        )
    hosted_profile = observation.get("hosted_profile")
    if not isinstance(hosted_profile, dict):
        raise AssertionError(
            "The same-session workspace profile state did not expose the hosted "
            "workspace profile needed for fallback-state inspection.\n"
            f"observation={json.dumps(observation, ensure_ascii=True)}",
        )
    if observation.get("hosted_access_mode") != "disconnected":
        raise AssertionError(
            "The live browser session did not persist the hosted fallback workspace as "
            "`hostedAccessMode=disconnected` while auth was unresolved.\n"
            f"observation={json.dumps(observation, ensure_ascii=True)}",
        )
    if active_workspace_id != str(hosted_profile.get("id", "")):
        raise AssertionError(
            "The same-session workspace profile state did not keep the hosted workspace "
            "selected while the fallback surface was being inspected.\n"
            f"observation={json.dumps(observation, ensure_ascii=True)}",
        )


def _assert_public_capability_surface(
    *,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    surface: dict[str, Any],
) -> None:
    if not runtime.auth_probe_pending:
        raise AssertionError(
            "The delayed auth probe was no longer pending while the same-session public "
            "capability surface was being inspected.",
        )
    body_flag_values = surface.get("body_flag_values")
    if isinstance(body_flag_values, dict) and body_flag_values.get(
        "canWriteFalse",
    ) is True and body_flag_values.get("canCreateBranchFalse") is True:
        return
    storage_matches = surface.get("same_session_storage_matches", [])
    if isinstance(storage_matches, list):
        for match in storage_matches:
            if not isinstance(match, dict):
                continue
            if (
                match.get("canWrite") is False
                and match.get("canCreateBranch") is False
            ):
                return
    raise AssertionError(
        "The live browser session exposed only indirect fallback evidence (`Create issue` "
        "gate plus `hostedAccessMode=disconnected`) and did not expose any same-session "
        "public surface with explicit `canWrite=false` and `canCreateBranch=false` "
        "flags.\n"
        f"surface={json.dumps(surface, ensure_ascii=True)}",
    )


def _sample_payload(observation: dict[str, Any]) -> dict[str, Any]:
    trigger = observation.get("trigger")
    startup = observation.get("startup_observation", {})
    shell = observation.get("shell_observation", {})
    return {
        "auth_pending": observation.get("auth_pending"),
        "elapsed_since_auth_start_seconds": observation.get("elapsed_since_auth_start_seconds"),
        "auth_probe_started_after_start_seconds": observation.get(
            "auth_probe_started_after_start_seconds",
        ),
        "auth_probe_released_after_start_seconds": observation.get(
            "auth_probe_released_after_start_seconds",
        ),
        "shell_ready_after_start_seconds": observation.get("shell_ready_after_start_seconds"),
        "branding_visible": observation.get("branding_visible"),
        "location_pathname": startup.get("location_pathname"),
        "location_hash": startup.get("location_hash"),
        "title": startup.get("title"),
        "button_labels": list(startup.get("button_labels", [])),
        "visible_navigation_labels": list(shell.get("visible_navigation_labels", [])),
        "shell_ready": shell.get("shell_ready"),
        "trigger": trigger,
        "body_excerpt": _snippet(str(shell.get("body_text", ""))),
    }


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any] | None:
    return safe_trigger_payload(page)


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, Any]:
    return trigger_payload(trigger)


def _switcher_payload(
    switcher: WorkspaceSwitcherObservation,
) -> dict[str, Any]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _row_payload(
    row: WorkspaceSwitcherRowObservation | None,
) -> dict[str, Any] | None:
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


def _create_gate_payload(gate: CreateIssueGateObservation) -> dict[str, Any]:
    return {
        "body_text": gate.body_text,
        "gate_panel_text": gate.gate_panel_text,
        "callout_semantics_label": gate.callout_semantics_label,
        "create_heading_visible": gate.create_heading_visible,
        "summary_field_count": gate.summary_field_count,
        "create_button_count": gate.create_button_count,
        "save_button_count": gate.save_button_count,
        "open_settings_button_count": gate.open_settings_button_count,
        "gate_open_settings_button_count": gate.gate_open_settings_button_count,
        "gate_cta_center_x": gate.gate_cta_center_x,
        "gate_cta_center_y": gate.gate_cta_center_y,
    }


def _snippet(text: str, *, limit: int = 240) -> str:
    return snippet(text, limit=limit)


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")
    _write_review_replies(result)


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    _write_review_replies(result)
    if _should_write_bug_description(result):
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_text = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status_text}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"*Environment:* URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport:* {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked Bugs Considered:* {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was tested",
        "* Started from the active local workspace so the delayed GitHub {/user} startup probe is exercised deterministically, then switched into the hosted workspace after the shell rendered.",
        "* Waited beyond the 11-second timeout before asserting instead of checking immediately.",
        "* Checked the hosted fallback workspace state, the user-facing Create issue gate, and the same-browser hosted access mode persisted in workspace storage.",
        "",
        "h4. Result",
        f"* {_actual_result_summary(result, passed=passed)}",
        *_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *format_human_lines(result, jira=True),
        "",
        "h4. Test file",
        "{code}",
        "testing/tests/TS-1001/test_ts_1001.py",
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot:* {result['screenshot']}"])
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


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
    status_text = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status_text}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked Bugs Considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## Rework summary",
        *[f"- {item}" for item in REWORK_SUMMARY_ITEMS],
        "",
        "## What was automated",
        "- Delayed the live GitHub `/user` startup probe by 30 seconds and exercised it from the local-active startup path before switching into the hosted workspace.",
        "- Waited past the timeout before asserting the visible shell and fallback state.",
        "- Verified the active hosted workspace state and blocked Create issue flow, then searched same-session public browser surfaces for explicit `canWrite` / `canCreateBranch` flags instead of passing on indirect evidence alone.",
        "",
        "## Result",
        f"- {_actual_result_summary(result, passed=passed)}",
        *_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *format_human_lines(result, jira=False),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
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


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    lines = [
        "h3. Rework summary",
        "",
        *[f"* {item}" for item in REWORK_SUMMARY_ITEMS],
        "",
        "h3. Latest result",
        "",
        f"*Status:* {'✅ PASSED' if passed else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"*Run command:* {{code:bash}}{RUN_COMMAND}{{code}}",
        f"*Summary:* {'1 passed, 0 failed' if passed else '0 passed, 1 failed'}",
        f"*Observed:* {_actual_result_summary(result, passed=passed)}",
        "",
    ]
    if not passed:
        lines.extend(
            [
                "h4. Error",
                "{code}",
                str(result.get("error", "")),
                "{code}",
                "",
            ],
        )
    return "\n".join(lines) + "\n"


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    error = str(result.get("error", ""))
    if error.startswith("RuntimeError: TS-1001 requires GH_TOKEN or GITHUB_TOKEN"):
        return False
    if error.startswith("ModuleNotFoundError:"):
        return False
    return bool(result.get("product_failure"))


def _build_bug_description(result: dict[str, Any]) -> str:
    lines = [
        f"# {TICKET_KEY} bug report",
        "",
        "## Steps to reproduce",
        *build_annotated_steps(result, request_steps=REQUEST_STEPS),
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        f"- **Actual:** {_actual_result_summary(result, passed=False)}",
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Simulated delayed startup probe: GitHub `/user` delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Timeout observation: `{json.dumps(result.get('timeout_window_observation'), ensure_ascii=True)}`",
        f"- Hosted trigger after switch: `{json.dumps(result.get('hosted_trigger_after_switch'), ensure_ascii=True)}`",
        f"- Trigger observation: `{json.dumps(result.get('trigger_observation'), ensure_ascii=True)}`",
        f"- Switcher observation: `{json.dumps(result.get('switcher_observation'), ensure_ascii=True)}`",
        f"- Create issue gate observation: `{json.dumps(result.get('create_issue_gate_observation'), ensure_ascii=True)}`",
        f"- Workspace profile state: `{json.dumps(result.get('workspace_profile_state'), ensure_ascii=True)}`",
        f"- Public capability surface: `{json.dumps(result.get('public_capability_surface'), ensure_ascii=True)}`",
        "- Missing production capability: the live browser session does not currently expose any public same-session metadata surface with explicit `canWrite` / `canCreateBranch` flags for the fallback session.",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "After the 11-second startup timeout elapsed with the delayed auth probe "
            "still pending, the deployed app showed the interactive shell, the active "
            "hosted workspace exposed `Needs sign-in`, Create issue stayed blocked "
            "behind the visible `Open settings` recovery gate, and a same-session "
            "public capability surface explicitly kept `canWrite=false` and "
            "`canCreateBranch=false`."
        )
    if result.get("public_capability_surface") is not None:
        return (
            "After the 11-second startup timeout elapsed with the delayed auth probe "
            "still pending, the deployed app showed the interactive shell, the active "
            "hosted workspace exposed `Needs sign-in`, Create issue stayed blocked "
            "behind the visible `Open settings` recovery gate, and the same-session "
            "workspace profile state persisted `hostedAccessMode=disconnected` — but "
            "the live browser session still exposed no public same-session surface with "
            "explicit `canWrite=false` and `canCreateBranch=false` flags."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not expose the restricted fallback session expected "
            "after the delayed-auth startup timeout.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_step_lines(result, jira=jira)


def _write_review_replies(result: dict[str, Any]) -> None:
    layering_reply = (
        "Fixed: moved the Step 4 capability-surface scan out of the ticket test and into "
        "`TrackStateTrackerPage.observe_public_capability_surface(...)`, so the scenario "
        "now depends on a reusable page component instead of calling "
        "`tracker_page.session.evaluate(...)` directly."
    )
    scoping_reply = (
        "Fixed: Step 4 now scopes storage matches to the active hosted workspace contract "
        "before treating them as evidence. The page component derives the active hosted "
        "workspace id/repository from same-session workspace profile storage and only "
        "accepts `canWrite=false` / `canCreateBranch=false` matches tied to that hosted "
        "workspace; otherwise the rerun stays failed as a product gap."
    )
    payload = {
        "replies": [
            {
                **REVIEW_THREADS[0],
                "reply": layering_reply,
            },
            {
                **REVIEW_THREADS[1],
                "reply": scoping_reply,
            },
        ]
    }
    REVIEW_REPLIES_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
