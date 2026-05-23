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

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
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
    build_annotated_steps,
    build_workspace_state,
    elapsed_since,
    format_human_lines,
    format_step_lines,
    observe_live_startup_shell_window,
    prepare_local_workspace_repository,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    relative_event_seconds,
    relative_startup_event_seconds,
    safe_trigger_payload,
    snippet,
    startup_surface_payload,
    trigger_payload,
    try_observe_trigger,
    write_test_automation_result,
)

TICKET_KEY = "TS-984"
TEST_CASE_TITLE = (
    "Application startup with hanging synchronization probe — UI shell renders "
    "after 11s timeout"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-984/test_ts_984.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SYNC_TIMEOUT_SECONDS = 11
SIMULATED_SYNC_DELAY_SECONDS = 31
TIMEOUT_ASSERTION_SECONDS = SYNC_TIMEOUT_SECONDS
LINKED_BUGS = ["TS-973"]
REWORK_SUMMARY = (
    "Added a live startup regression for TS-984 that delays the initial GitHub "
    "`/user` probe beyond 30 seconds and verifies the deployed app still reaches "
    "shell_ready and renders the user-visible shell once the explicit 11-second "
    "timeout path takes over."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts984_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts984_failure.png"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Monitor the application startup sequence and the transition to the shell_ready state.",
    "Wait for the duration of the explicit 11-second synchronization timeout.",
    "Verify the visibility of interactive shell components such as the TopBar and branding.",
]
EXPECTED_RESULT = (
    "The application UI shell (TopBar, branding) becomes visible and interactive "
    "within the 11-second timeout window, confirming that the shell_ready state "
    "was triggered by the timeout fallback path rather than waiting for the "
    "hanging probe to complete."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-984 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = DelayedAuthWorkspaceProfilesRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=SIMULATED_SYNC_DELAY_SECONDS,
        delayed_paths=("/user",),
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
        "sync_timeout_seconds": SYNC_TIMEOUT_SECONDS,
        "simulated_sync_delay_seconds": SIMULATED_SYNC_DELAY_SECONDS,
        "timeout_assertion_seconds": TIMEOUT_ASSERTION_SECONDS,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                startup_started_at_monotonic = time.monotonic()
                tracker_page.open_entrypoint()
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["startup_observation_initial"] = _startup_surface_payload(
                    tracker_page,
                )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app in Chromium with a stored "
                        "GitHub token, a preloaded active local workspace plus hosted "
                        "fallback workspace profile, and an "
                        f"injected {SIMULATED_SYNC_DELAY_SECONDS}-second delay on the "
                        "initial GitHub `/user` startup probe."
                    ),
                )

                trigger_visible, initial_trigger = poll_until(
                    probe=lambda: _try_observe_trigger(page),
                    is_satisfied=lambda candidate: candidate is not None,
                    timeout_seconds=120,
                    interval_seconds=0.5,
                )
                result["runtime_state"] = "startup-shell-visible" if trigger_visible else "startup-pending"
                result["runtime_body_text"] = page.current_body_text()
                result["initial_trigger_observation"] = (
                    _trigger_payload(initial_trigger) if initial_trigger is not None else None
                )
                if not trigger_visible or initial_trigger is None:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The deployed app never exposed the interactive shell trigger "
                            "needed to confirm the shell_ready transition.\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: the deployed app never exposed the interactive "
                        "shell trigger needed to confirm the shell_ready transition.\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                if (
                    runtime.auth_probe_started_at_monotonic is None
                    and not runtime.wait_for_auth_probe_start(timeout_seconds=30)
                ):
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The shell trigger became visible, but the delayed GitHub "
                            "`/user` startup probe never began, so the timeout-driven "
                            "synchronization scenario was not exercised.\n"
                            f"Observed trigger: {json.dumps(_trigger_payload(initial_trigger), indent=2)}\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(
                        "Step 2 failed: the shell trigger became visible, but the delayed "
                        "GitHub `/user` startup probe never began, so the synchronization-"
                        "timeout scenario was not exercised.\n"
                        f"Observed trigger: {json.dumps(_trigger_payload(initial_trigger), indent=2)}\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                timeout_elapsed, timeout_window = poll_until(
                    probe=lambda: _observe_shell_window(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                    ),
                    is_satisfied=lambda observation: (
                        observation["elapsed_since_auth_start_seconds"] is not None
                        and float(observation["elapsed_since_auth_start_seconds"])
                        >= TIMEOUT_ASSERTION_SECONDS
                    ),
                    timeout_seconds=SIMULATED_SYNC_DELAY_SECONDS + 5,
                    interval_seconds=0.5,
                )
                result["timeout_window_observation"] = timeout_window
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)

                eventual_shell_ready, shell_ready_observation = poll_until(
                    probe=lambda: _observe_shell_window(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                    ),
                    is_satisfied=lambda observation: bool(
                        observation["shell_observation"]["shell_ready"]
                    ),
                    timeout_seconds=SIMULATED_SYNC_DELAY_SECONDS + 60,
                    interval_seconds=0.5,
                )
                result["shell_ready_observation"] = shell_ready_observation

                failures: list[str] = []
                if eventual_shell_ready:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The deployed app eventually transitioned into shell_ready "
                            "after the delayed `/user` startup probe sequence.\n"
                            f"initial_trigger={json.dumps(_trigger_payload(initial_trigger), ensure_ascii=True)}; "
                            f"shell_ready_after_start_seconds="
                            f"{shell_ready_observation['shell_ready_after_start_seconds']!r}; "
                            f"auth_probe_started_after_start_seconds="
                            f"{shell_ready_observation['auth_probe_started_after_start_seconds']!r}; "
                            f"auth_probe_released_after_start_seconds="
                            f"{shell_ready_observation['auth_probe_released_after_start_seconds']!r}"
                        ),
                    )
                else:
                    step_two_error = (
                        "Step 2 failed: the deployed app never transitioned into "
                        "shell_ready during the delayed startup-probe scenario.\n"
                        f"Observed shell window:\n{json.dumps(shell_ready_observation, indent=2)}"
                    )
                    failures.append(step_two_error)
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=step_two_error,
                    )

                step_three_error: str | None = None
                if not timeout_elapsed:
                    step_three_error = (
                        "Step 3 failed: the test never reached the explicit "
                        "11-second synchronization timeout window while observing the delayed "
                        "startup probe.\n"
                        f"Observed shell window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif (
                    not bool(timeout_window["auth_pending"])
                    and timeout_window["auth_probe_release_after_auth_start_seconds"] is not None
                    and float(timeout_window["auth_probe_release_after_auth_start_seconds"])
                    > TIMEOUT_ASSERTION_SECONDS
                ):
                    step_three_error = (
                        "Step 3 failed: the page only became observable after the delayed "
                        "startup probe released, so the shell was not available by the "
                        f"{TIMEOUT_ASSERTION_SECONDS}-second timeout window.\n"
                        f"Observed auth_probe_release_after_auth_start_seconds="
                        f"{timeout_window['auth_probe_release_after_auth_start_seconds']!r}; "
                        f"shell_ready_after_start_seconds="
                        f"{timeout_window['shell_ready_after_start_seconds']!r}\n"
                        f"Observed shell window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif not bool(timeout_window["auth_pending"]):
                    step_three_error = (
                        "Step 3 failed: the delayed startup probe was no longer pending by "
                        "the time the timeout assertion ran, so the test did not prove the "
                        "non-blocking timeout behavior.\n"
                        f"Observed shell window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif not bool(timeout_window["shell_observation"]["shell_ready"]):
                    step_three_error = (
                        "Step 3 failed: after waiting past the explicit synchronization "
                        "timeout, the page still had not reached shell_ready.\n"
                        f"Observed shell window:\n{json.dumps(timeout_window, indent=2)}"
                    )

                if step_three_error is None:
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=REQUEST_STEPS[2],
                        observed=(
                            f"Waited {timeout_window['elapsed_since_auth_start_seconds']!r} "
                            "seconds from the delayed `/user` probe start, which reaches the "
                            f"{SYNC_TIMEOUT_SECONDS}-second startup timeout window. The probe "
                            f"was still pending and shell_ready was {timeout_window['shell_observation']['shell_ready']!r}."
                        ),
                    )
                else:
                    failures.append(step_three_error)
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=step_three_error,
                    )

                step_four_error: str | None = None
                try:
                    _assert_shell_components(timeout_window)
                except AssertionError as error:
                    step_four_error = str(error)
                if (
                    step_three_error is not None
                    and step_four_error is None
                    and timeout_window["auth_probe_release_after_auth_start_seconds"] is not None
                    and float(timeout_window["auth_probe_release_after_auth_start_seconds"])
                    > TIMEOUT_ASSERTION_SECONDS
                ):
                    step_four_error = (
                        "Step 4 failed: the top bar and branding were only observable after "
                        "the delayed startup probe released, not by the expected "
                        f"{TIMEOUT_ASSERTION_SECONDS}-second timeout window.\n"
                        f"Observed auth_probe_release_after_auth_start_seconds="
                        f"{timeout_window['auth_probe_release_after_auth_start_seconds']!r}; "
                        f"shell_ready_after_start_seconds="
                        f"{timeout_window['shell_ready_after_start_seconds']!r}\n"
                        f"Observed shell window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                elif step_three_error is not None and step_four_error is None:
                    step_four_error = (
                        "Step 4 failed: at the timeout-window snapshot, the interactive "
                        "shell components were not all visible because the page had not "
                        "reached shell_ready.\n"
                        f"Observed shell window:\n{json.dumps(timeout_window, indent=2)}"
                    )
                if step_four_error is None:
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action=REQUEST_STEPS[3],
                        observed=(
                            "The timeout-window snapshot exposed the interactive shell rather "
                            "than the startup loading surface.\n"
                            f"title={timeout_window['startup_observation']['title']!r}; "
                            f"trigger={json.dumps(timeout_window['trigger'], ensure_ascii=True)}; "
                            f"branding_visible={timeout_window['branding_visible']!r}; "
                            f"visible_navigation_labels="
                            f"{json.dumps(timeout_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}"
                        ),
                    )
                else:
                    failures.append(step_four_error)
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
                        "Viewed the live app after waiting through the explicit 11-second "
                        "timeout and checked the page the way a user would: visible shell "
                        "navigation, a TopBar workspace trigger, and branding text instead "
                        "of a stalled startup surface."
                    ),
                    observed=(
                        f"body_text_snippet={_snippet(timeout_window['shell_observation']['body_text'])!r}; "
                        f"branding_text_visible={timeout_window['branding_visible']!r}; "
                        f"trigger_label="
                        f"{(timeout_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"visible_buttons="
                        f"{json.dumps(timeout_window['startup_observation']['button_labels'], ensure_ascii=True)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Kept watching the live page after the 11-second timeout checkpoint "
                        "to see whether the app ever recovered into the shell later."
                    ),
                    observed=(
                        f"eventual_shell_ready={eventual_shell_ready!r}; "
                        f"shell_ready_after_start_seconds="
                        f"{shell_ready_observation['shell_ready_after_start_seconds']!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{shell_ready_observation['auth_probe_released_after_start_seconds']!r}"
                    ),
                )

                if failures:
                    raise AssertionError("\n\n".join(failures))

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _write_pass_outputs(result)
                print(f"{TICKET_KEY} passed")
                return
            except Exception:
                try:
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                    result["screenshot_error"] = (
                        f"{type(screenshot_error).__name__}: {screenshot_error}"
                    )
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


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
        marker_filename=".trackstate-ts984-precondition.txt",
        marker_contents="Prepared for TS-984 startup synchronization timeout validation.\n",
        commit_author_name="TS-984 Automation",
        commit_author_email="ts984@example.com",
        commit_message="Prepare TS-984 local workspace",
    )


def _observe_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    startup_started_at_monotonic: float,
) -> dict[str, Any]:
    return observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
    )


def _elapsed_since(event_monotonic: float | None) -> float | None:
    return elapsed_since(event_monotonic)


def _relative_startup_event_seconds(
    startup_started_at_monotonic: float,
    event_monotonic: float | None,
) -> float | None:
    return relative_startup_event_seconds(startup_started_at_monotonic, event_monotonic)


def _relative_event_seconds(
    started_at_monotonic: float | None,
    event_monotonic: float | None,
) -> float | None:
    return relative_event_seconds(started_at_monotonic, event_monotonic)


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    return startup_surface_payload(tracker_page)


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any] | None:
    return safe_trigger_payload(page)


def _try_observe_trigger(
    page: LiveWorkspaceSwitcherPage,
) -> Any | None:
    return try_observe_trigger(page)


def _trigger_payload(trigger: Any) -> dict[str, Any]:
    return trigger_payload(trigger)


def _assert_shell_components(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "Step 4 failed: the timeout-window shell snapshot did not expose the full "
            "interactive navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "Step 4 failed: the timeout-window shell snapshot did not expose the "
            "TopBar workspace trigger needed to prove the top bar was interactive.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "Step 4 failed: the timeout-window shell snapshot did not expose the "
            "visible TrackState branding text.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    startup_buttons = set(observation["startup_observation"]["button_labels"])
    if startup_buttons == {"Sync issue"}:
        raise AssertionError(
            "Step 4 failed: after waiting past the startup timeout, the page still "
            "looked like the startup loading surface instead of the "
            "interactive shell.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )


def _snippet(text: str, *, limit: int = 240) -> str:
    return snippet(text, limit=limit)


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


def _record_not_reached_steps(
    result: dict[str, Any],
    *,
    starting_step: int,
) -> None:
    record_not_reached_steps(result, starting_step=starting_step, request_steps=REQUEST_STEPS)


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        f"*Observed timeout window*: {TIMEOUT_ASSERTION_SECONDS} seconds against a synthetic {SIMULATED_SYNC_DELAY_SECONDS}-second delayed `/user` startup probe",
        "",
        "h4. What was automated",
        "* Preloaded local and hosted workspace profiles plus a stored GitHub token for the deployed app.",
        "* Delayed the initial GitHub {/user} startup probe for 31 seconds so the startup synchronization path stayed pending beyond the explicit 11-second timeout.",
        "* Waited through the 11-second timeout before asserting so the test proved the deployed fallback behavior instead of checking too early.",
        "* Verified the live page showed shell navigation, a TopBar workspace trigger, and TrackState branding instead of remaining on the startup loading surface.",
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


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
    lines = [
        f"## {TICKET_KEY} passed" if passed else f"## {TICKET_KEY} failed",
        "",
        "## Rework summary",
        f"- {REWORK_SUMMARY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        f"**Observed timeout window:** `{TIMEOUT_ASSERTION_SECONDS}` seconds against a synthetic `{SIMULATED_SYNC_DELAY_SECONDS}`-second delayed `/user` startup probe",
        "",
        "## What was automated",
        "- Preloaded local and hosted workspace profiles plus a stored GitHub token for the deployed app.",
        "- Delayed the initial GitHub `/user` startup probe for 31 seconds so the startup synchronization path stayed pending beyond the explicit 11-second timeout.",
        "- Waited through the 11-second timeout before asserting so the test proved the deployed fallback behavior instead of checking immediately.",
        "- Verified the live page showed shell navigation, a TopBar workspace trigger, and TrackState branding instead of remaining on the startup loading surface.",
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


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "The delayed startup probe stayed pending past the 11-second timeout, but "
            "the deployed app still reached shell_ready and exposed the interactive "
            "shell, TopBar workspace trigger, and TrackState branding.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not prove the non-blocking startup timeout behavior.')}\n"
    )


def _build_bug_description(result: dict[str, Any]) -> str:
    annotated_steps = build_annotated_steps(result, request_steps=REQUEST_STEPS)
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
        f"- **Actual:** {_actual_result_summary(result, passed=False)}",
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Simulated delayed startup probe: GitHub `/user` delayed by {SIMULATED_SYNC_DELAY_SECONDS} seconds",
        f"- Timeout assertion window: {TIMEOUT_ASSERTION_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Timeout window observation: `{json.dumps(result.get('timeout_window_observation'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "After waiting past the startup timeout while the delayed `/user` probe was "
            "still pending, the deployed app exposed the full shell navigation, "
            "TopBar workspace trigger, and visible TrackState branding instead of "
            "staying on the startup loading surface."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not prove the non-blocking startup timeout behavior.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_step_lines(result, jira=jira)


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_human_lines(result, jira=jira)


if __name__ == "__main__":
    main()
