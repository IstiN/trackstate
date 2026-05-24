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
    try_observe_trigger,
    write_test_automation_result,
)
from testing.tests.support.ts984_delayed_auth_probe_runtime import (  # noqa: E402
    Ts984DelayedAuthProbeRuntime,
)

TICKET_KEY = "TS-985"
TEST_CASE_TITLE = (
    "Application startup with successful probe — UI shell becomes interactive "
    "without waiting for timeout"
)
TEST_FILE_PATH = "testing/tests/TS-985/test_ts_985.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-985/test_ts_985.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
FULL_SYNC_TIMEOUT_SECONDS = 11
SIMULATED_PROBE_DELAY_SECONDS = 2
MAX_READY_AFTER_START_SECONDS = 6.5
MAX_READY_AFTER_RELEASE_SECONDS = 3.5
AUTH_PROBE_START_WAIT_SECONDS = 30
SHELL_READY_WAIT_SECONDS = FULL_SYNC_TIMEOUT_SECONDS + 8
POLL_INTERVAL_SECONDS = 0.25
LINKED_BUG_KEYS = (
    "TS-1014",
    "TS-1013",
    "TS-1012",
    "TS-996",
    "TS-992",
    "TS-973",
    "TS-971",
)
LINKED_BUG_NOTES = (
    "Reviewed TS-1014, TS-1013, TS-1012, TS-996, TS-992, TS-973, and TS-971. "
    "The startup-related fixes require observing the delayed live GitHub "
    "`/user` probe during startup, waiting for the real post-release shell "
    "transition, and proving the shell did not simply appear from the 11-second "
    "fallback or a late post-startup probe; TS-973 is workspace-switcher "
    "specific and adds no extra startup wait requirement."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts985_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts985_failure.png"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Observe the time taken for the interactive shell components (TopBar, branding) to become visible.",
]
EXPECTED_RESULT = (
    "The UI shell becomes interactive immediately after the probe completes "
    "(at approximately 2 seconds), confirming that the application does not "
    "wait for the full 11-second synchronization timeout when the probe is successful."
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
            "TS-985 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts984DelayedAuthProbeRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=SIMULATED_PROBE_DELAY_SECONDS,
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
        "full_sync_timeout_seconds": FULL_SYNC_TIMEOUT_SECONDS,
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
        "max_ready_after_start_seconds": MAX_READY_AFTER_START_SECONDS,
        "max_ready_after_release_seconds": MAX_READY_AFTER_RELEASE_SECONDS,
        "linked_bug_notes": LINKED_BUG_NOTES,
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

                transition_tracker = ShellReadyTransitionTracker()
                auth_probe_started = runtime.wait_for_auth_probe_start(
                    timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                )
                pending_shell_sample_observed = False
                pending_shell_window: dict[str, Any] | None = None
                if auth_probe_started:
                    _, pending_shell_window = poll_until(
                        probe=lambda: _observe_shell_window(
                            tracker_page=tracker_page,
                            page=page,
                            runtime=runtime,
                            startup_started_at_monotonic=startup_started_at_monotonic,
                            transition_tracker=transition_tracker,
                            poll_timeout_ms=25,
                        ),
                        is_satisfied=lambda observation: (
                            int(observation["observed_pending_shell_samples"] or 0) >= 1
                            or not bool(observation["auth_pending"])
                        ),
                        timeout_seconds=SIMULATED_PROBE_DELAY_SECONDS + 2,
                        interval_seconds=0.05,
                    )
                    pending_shell_sample_observed = (
                        int(pending_shell_window["observed_pending_shell_samples"] or 0) >= 1
                    )
                    result["pending_shell_window_observation"] = pending_shell_window
                shell_ready, shell_window = poll_until(
                    probe=lambda: _observe_shell_window(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                        transition_tracker=transition_tracker,
                        poll_timeout_ms=250,
                    ),
                    is_satisfied=lambda observation: (
                        observation["auth_probe_started_after_start_seconds"] is not None
                        and
                        observation["auth_probe_released_after_start_seconds"] is not None
                        and observation["shell_ready_after_start_seconds"] is not None
                        and not bool(observation["auth_pending"])
                    ),
                    timeout_seconds=SHELL_READY_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["shell_window_observation"] = shell_window
                auth_probe_started_after_start_seconds = shell_window[
                    "auth_probe_started_after_start_seconds"
                ]
                result["auth_probe_started_after_start_seconds"] = (
                    auth_probe_started_after_start_seconds
                )
                auth_probe_released_after_start_seconds = shell_window[
                    "auth_probe_released_after_start_seconds"
                ]
                result["auth_probe_released_after_start_seconds"] = (
                    auth_probe_released_after_start_seconds
                )
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)
                initial_trigger = _try_observe_trigger(page)
                if initial_trigger is not None:
                    result["initial_trigger_observation"] = _trigger_payload(initial_trigger)
                    result["trigger_observed_after_start_seconds"] = round(
                        time.monotonic() - startup_started_at_monotonic,
                        2,
                    )

                if auth_probe_started_after_start_seconds is None:
                    _record_human_verification(
                        result,
                        check=(
                            "Observed the live page immediately after launch to confirm what "
                            "a user actually saw during startup."
                        ),
                        observed=(
                            "The delayed GitHub `/user` startup probe never started, while "
                            "the visible page content was:\n"
                            f"{tracker_page.body_text()}"
                        ),
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never started the delayed GitHub `/user` "
                            "startup probe, so the short successful-probe scenario was "
                            "not exercised.\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the deployed app never started the delayed "
                        "GitHub `/user` startup probe needed for TS-985.\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )
                if auth_probe_started_after_start_seconds >= FULL_SYNC_TIMEOUT_SECONDS:
                    _record_human_verification(
                        result,
                        check=(
                            "Observed the visible startup experience like a user instead of "
                            "relying only on network timing."
                        ),
                        observed=(
                            "The interactive shell was already visible before the delayed "
                            "GitHub `/user` startup probe began, so the requested successful-"
                            "probe startup path was not what the user experienced.\n"
                            f"auth_probe_started_after_start_seconds="
                            f"{auth_probe_started_after_start_seconds!r}; "
                            f"auth_probe_released_after_start_seconds="
                            f"{auth_probe_released_after_start_seconds!r}; "
                            f"visible_body_excerpt={_snippet(tracker_page.body_text())!r}"
                        ),
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The delayed GitHub `/user` startup probe did not begin until "
                            "well after the startup window, so the successful-probe path "
                            "was not exercised during application startup.\n"
                            f"auth_probe_started_after_start_seconds="
                            f"{auth_probe_started_after_start_seconds!r}; "
                            f"auth_probe_released_after_start_seconds="
                            f"{auth_probe_released_after_start_seconds!r}; "
                            f"delayed_request_urls={runtime.delayed_request_urls!r}; "
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the delayed GitHub `/user` startup probe started "
                        "too late to exercise the successful startup-probe path.\n"
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"delayed_request_urls={runtime.delayed_request_urls!r}\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                if initial_trigger is None:
                    _record_human_verification(
                        result,
                        check=(
                            "Observed the top bar area after launch to confirm whether a "
                            "user could see the workspace trigger."
                        ),
                        observed=(
                            "The deployed page never exposed the header workspace trigger "
                            "needed for the requested startup-shell verification.\n"
                            f"visible_body_excerpt={_snippet(tracker_page.body_text())!r}"
                        ),
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The deployed app never exposed the header workspace trigger "
                            "needed to observe the startup shell timing.\n"
                            f"Observed body text:\n{tracker_page.body_text()}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the deployed app never exposed the header "
                        "workspace trigger needed to observe the startup shell timing.\n"
                        f"Observed body text:\n{tracker_page.body_text()}",
                    )

                if auth_probe_released_after_start_seconds is None:
                    _record_human_verification(
                        result,
                        check=(
                            "Observed the page after launch to verify whether the delayed "
                            "startup probe ever completed from a user's perspective."
                        ),
                        observed=(
                            "The app never completed the delayed GitHub `/user` startup "
                            "probe within the observation window.\n"
                            f"visible_body_excerpt={_snippet(tracker_page.body_text())!r}; "
                            f"observed_request_urls={runtime.github_request_urls!r}"
                        ),
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=(
                            "The delayed GitHub `/user` startup probe started, but it "
                            "never completed successfully within the observation window.\n"
                            f"Observed request URLs: {runtime.github_request_urls!r}"
                        ),
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(
                        "Step 1 failed: the delayed GitHub `/user` startup probe did "
                        "not complete successfully within the observation window.\n"
                        f"Observed request URLs: {runtime.github_request_urls!r}",
                    )

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app in Chromium with a stored "
                        "GitHub token, preloaded workspace state, and a synthetic "
                        f"{SIMULATED_PROBE_DELAY_SECONDS}-second delay on the GitHub "
                        "`/user` startup probe.\n"
                        f"trigger_observed_after_start_seconds="
                        f"{result['trigger_observed_after_start_seconds']!r}; "
                        f"trigger_label={initial_trigger.semantic_label!r}; "
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"delayed_request_urls={runtime.delayed_request_urls!r}"
                    ),
                )

                if not shell_ready:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=(
                            "The live app never exposed the shell_ready interactive shell "
                            "after the delayed startup probe completed.\n"
                            f"Observed shell window:\n{json.dumps(shell_window, indent=2)}"
                        ),
                    )
                    raise AssertionError(
                        "Step 2 failed: the live app never exposed the shell_ready "
                        "interactive shell after the delayed startup probe completed.\n"
                        f"Observed shell window:\n{json.dumps(shell_window, indent=2)}",
                    )

                _assert_interactive_shell(shell_window)

                shell_ready_after_start_seconds = shell_window["shell_ready_after_start_seconds"]
                probe_recorded_shell_ready_after_start_seconds = shell_window[
                    "probe_recorded_shell_ready_after_start_seconds"
                ]
                authoritative_shell_ready_after_start_seconds = (
                    probe_recorded_shell_ready_after_start_seconds
                    if probe_recorded_shell_ready_after_start_seconds is not None
                    else shell_ready_after_start_seconds
                )
                authoritative_shell_ready_after_probe_release_seconds = (
                    None
                    if (
                        authoritative_shell_ready_after_start_seconds is None
                        or auth_probe_released_after_start_seconds is None
                    )
                    else round(
                        authoritative_shell_ready_after_start_seconds
                        - auth_probe_released_after_start_seconds,
                        2,
                    )
                )
                shell_ready_after_probe_release_seconds = shell_window[
                    "shell_ready_after_probe_release_seconds"
                ]
                observed_pending_shell_samples = shell_window[
                    "observed_pending_shell_samples"
                ]

                timing_failures: list[str] = []
                if auth_probe_released_after_start_seconds is None:
                    timing_failures.append(
                        "The delayed startup probe release time could not be measured.",
                    )
                if (
                    shell_ready_after_start_seconds is None
                    and probe_recorded_shell_ready_after_start_seconds is None
                ):
                    timing_failures.append(
                        "The shell_ready transition time could not be measured by either "
                        "the Python observer or the page-side probe.",
                    )
                auth_probe_release_after_auth_start_seconds = shell_window[
                    "auth_probe_release_after_auth_start_seconds"
                ]
                if (
                    auth_probe_release_after_auth_start_seconds is None
                    or auth_probe_release_after_auth_start_seconds
                    < SIMULATED_PROBE_DELAY_SECONDS - 0.5
                ):
                    timing_failures.append(
                        "The delayed startup probe did not stay pending long enough to "
                        "prove the successful-probe timing path.\n"
                        f"Observed auth_probe_release_after_auth_start_seconds="
                        f"{auth_probe_release_after_auth_start_seconds!r}; expected about "
                        f"{SIMULATED_PROBE_DELAY_SECONDS} seconds.",
                    )
                if (
                    (observed_pending_shell_samples is None or int(observed_pending_shell_samples) < 1)
                    and probe_recorded_shell_ready_after_start_seconds is None
                ):
                    timing_failures.append(
                        "The observation loop never captured the app while the delayed "
                        "startup probe was still pending, and no page-side first "
                        "`shell_ready` transition timestamp was recorded either, so the "
                        "test cannot prove the causal timing relationship.\n"
                        f"Observed observed_pending_shell_samples="
                        f"{observed_pending_shell_samples!r}; "
                        f"probe_recorded_shell_ready_after_start_seconds="
                        f"{probe_recorded_shell_ready_after_start_seconds!r}."
                    )
                if (
                    not pending_shell_sample_observed
                    and probe_recorded_shell_ready_after_start_seconds is None
                ):
                    timing_failures.append(
                        "The focused pending-window sampler did not capture an in-flight "
                        "Python observation before the delayed startup probe finished, "
                        "and there was no page-side first-transition timestamp to use as "
                        "the equivalent proof.\n"
                        f"Observed pending_shell_window_observation="
                        f"{json.dumps(result.get('pending_shell_window_observation'), indent=2)}"
                    )
                if (
                    auth_probe_released_after_start_seconds is not None
                    and authoritative_shell_ready_after_start_seconds is not None
                    and authoritative_shell_ready_after_start_seconds
                    < auth_probe_released_after_start_seconds
                ):
                    timing_failures.append(
                        "The first authoritative shell_ready transition happened before "
                        "the delayed startup probe was released.",
                    )
                if (
                    authoritative_shell_ready_after_start_seconds is not None
                    and authoritative_shell_ready_after_start_seconds >= FULL_SYNC_TIMEOUT_SECONDS
                ):
                    timing_failures.append(
                        f"The shell became ready only after "
                        f"{authoritative_shell_ready_after_start_seconds!r} "
                        f"seconds, which is not before the full {FULL_SYNC_TIMEOUT_SECONDS}-second "
                        "timeout window.",
                    )
                if bool(shell_window["shell_ready_observed_while_auth_pending"]):
                    timing_failures.append(
                        "The first observed shell_ready transition happened while the "
                        "delayed startup probe was still pending.",
                    )
                if (
                    authoritative_shell_ready_after_probe_release_seconds is not None
                    and authoritative_shell_ready_after_probe_release_seconds
                    > MAX_READY_AFTER_RELEASE_SECONDS
                ):
                    timing_failures.append(
                        "The shell did not become interactive soon enough after the startup "
                        f"probe completed. Observed delay after release: "
                        f"{authoritative_shell_ready_after_probe_release_seconds!r} seconds; allowed "
                        f"threshold: {MAX_READY_AFTER_RELEASE_SECONDS} seconds.",
                    )

                if timing_failures:
                    observed = (
                        "The startup probe completed, but the live app did not prove the "
                        "expected immediate shell-ready behavior.\n"
                        f"shell_ready_after_start_seconds={shell_ready_after_start_seconds!r}; "
                        f"probe_recorded_shell_ready_after_start_seconds="
                        f"{probe_recorded_shell_ready_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"shell_ready_after_probe_release_seconds="
                        f"{shell_ready_after_probe_release_seconds!r}; "
                        f"authoritative_shell_ready_after_probe_release_seconds="
                        f"{authoritative_shell_ready_after_probe_release_seconds!r}; "
                        f"auth_probe_release_after_auth_start_seconds="
                        f"{auth_probe_release_after_auth_start_seconds!r}; "
                        f"observed_pending_shell_samples="
                        f"{observed_pending_shell_samples!r}; "
                        f"observed_shell_samples="
                        f"{shell_window['observed_shell_samples']!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}; "
                        f"trigger={(shell_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"branding_visible={shell_window['branding_visible']!r}\n"
                        + "\n".join(timing_failures)
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=observed,
                    )
                    raise AssertionError(f"Step 2 failed: {observed}")

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The live shell became interactive shortly after the delayed startup "
                        "probe completed, not after the full timeout window.\n"
                        f"shell_ready_after_start_seconds={shell_ready_after_start_seconds!r}; "
                        f"probe_recorded_shell_ready_after_start_seconds="
                        f"{probe_recorded_shell_ready_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"shell_ready_after_probe_release_seconds="
                        f"{shell_ready_after_probe_release_seconds!r}; "
                        f"authoritative_shell_ready_after_probe_release_seconds="
                        f"{authoritative_shell_ready_after_probe_release_seconds!r}; "
                        f"auth_probe_release_after_auth_start_seconds="
                        f"{auth_probe_release_after_auth_start_seconds!r}; "
                        f"observed_pending_shell_samples="
                        f"{observed_pending_shell_samples!r}; "
                        f"observed_shell_samples="
                        f"{shell_window['observed_shell_samples']!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}; "
                        f"trigger={(shell_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"branding_visible={shell_window['branding_visible']!r}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Watched the live startup sequence like a user and confirmed the "
                        "header/top-bar workspace trigger plus visible TrackState branding "
                        "appeared promptly after the delayed startup probe finished."
                    ),
                    observed=(
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_probe_release_seconds="
                        f"{authoritative_shell_ready_after_probe_release_seconds!r}; "
                        f"observed_pending_shell_samples="
                        f"{observed_pending_shell_samples!r}; "
                        f"observed_shell_samples={shell_window['observed_shell_samples']!r}; "
                        f"trigger_label={(shell_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"branding_visible={shell_window['branding_visible']!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Read the visible page content after the shell became interactive to "
                        "confirm the user saw the real navigation shell instead of waiting "
                        "through the full timeout."
                    ),
                    observed=(
                        f"body_excerpt={_snippet(shell_window['shell_observation']['body_text'])!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}; "
                        f"startup_buttons={shell_window['startup_observation']['button_labels']!r}"
                    ),
                )

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
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_bug=True)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_bug=False)
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
        marker_filename=".trackstate-ts985-precondition.txt",
        marker_contents="Prepared for TS-985 successful startup probe validation.\n",
        commit_author_name="TS-985 Automation",
        commit_author_email="ts985@example.com",
        commit_message="Prepare TS-985 local workspace",
    )


def _observe_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts984DelayedAuthProbeRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker | None = None,
    poll_timeout_ms: int = 1_000,
) -> dict[str, Any]:
    shell_window = observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
        transition_tracker=transition_tracker,
        poll_timeout_ms=poll_timeout_ms,
    )
    shell_probe_state = runtime.read_shell_probe_state()
    shell_window["shell_probe_state"] = shell_probe_state
    shell_window["probe_recorded_shell_ready_after_start_seconds"] = shell_probe_state[
        "first_shell_ready_after_launch_seconds"
    ]
    return shell_window


def _elapsed_between(
    start_monotonic: float | None,
    end_monotonic: float | None,
) -> float | None:
    if start_monotonic is None or end_monotonic is None:
        return None
    return round(end_monotonic - start_monotonic, 2)


def _relative_startup_event_seconds(
    startup_started_at_monotonic: float,
    event_monotonic: float | None,
) -> float | None:
    return relative_startup_event_seconds(startup_started_at_monotonic, event_monotonic)


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


def _assert_interactive_shell(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "The shell_ready snapshot did not expose the full interactive shell "
            "navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "The shell_ready snapshot did not expose the header workspace trigger "
            "needed to prove the top bar became interactive.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "The shell_ready snapshot did not expose visible TrackState branding.\n"
            f"Observed shell window:\n{json.dumps(observation, indent=2)}",
        )
    startup_buttons = set(observation["startup_observation"]["button_labels"])
    if startup_buttons == {"Sync issue"}:
        raise AssertionError(
            "The page still looked like the startup surface instead of the "
            "interactive shell when shell_ready was sampled.\n"
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


def _write_failure_outputs(result: dict[str, Any], *, product_bug: bool) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    if product_bug:
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    result_lines = [
        "* Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded workspace state.",
    ]
    if passed:
        result_lines.extend(
            [
                "* Delayed the live GitHub {/user} startup probe by 2 seconds, then waited for the real deployed shell to report {shell_ready} instead of asserting immediately.",
                "* Verified the visible shell became interactive before the full 11-second timeout and shortly after the delayed probe completed.",
                "* Confirmed the live page exposed shell navigation, the top-bar workspace trigger, and TrackState branding from the user's perspective.",
                "",
                "* Expected result matched.",
            ],
        )
    else:
        result_lines.extend(
            [
                "* Delayed the live GitHub {/user} startup probe by 2 seconds and observed the real deployed startup sequence.",
                f"* Failed while checking the requested startup behavior. Actual issue: {_actual_result_summary(result, passed=False)}",
            ],
        )
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status_icon} {status_word}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        f"* Live deployed app at {{ {result.get('app_url')} }} in {result.get('browser')} on {result.get('os')}",
        f"* Desktop viewport {{ {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']} }}",
        f"* Successful startup probe path with a synthetic {SIMULATED_PROBE_DELAY_SECONDS}-second delay on GitHub {{/user}}",
        f"* Linked bug review: {LINKED_BUG_NOTES}",
        "",
        "h4. Result",
        *result_lines,
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
    lines.extend(
        [
            "",
            "h4. Test file",
            "{code}",
            TEST_FILE_PATH,
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ],
    )
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
    result_lines = [
        "- Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded workspace state.",
    ]
    if passed:
        result_lines.append(
            "- Verified the visible shell became interactive before the full 11-second timeout and shortly after the delayed probe completed.",
        )
    else:
        result_lines.extend(
            [
                "- Delayed the live GitHub `/user` startup probe by 2 seconds and observed the real deployed startup sequence.",
                f"- Failed while verifying the requested startup behavior: {_actual_result_summary(result, passed=False)}",
            ],
        )
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        f"- Ran the live deployed app at `{result.get('app_url')}` in {result.get('browser')} on {result.get('os')}.",
        f"- Used the required desktop viewport `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`.",
        f"- Delayed the live GitHub `/user` startup probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds and waited for the real `shell_ready` transition instead of asserting immediately.",
        f"- Considered linked bugs {', '.join(LINKED_BUG_KEYS)} and kept the startup timing assertions coupled to the delayed probe completion.",
        "- Checked the user-visible shell navigation, top-bar workspace trigger, and TrackState branding after startup.",
        "",
        "## Result",
        *result_lines,
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
    lines.extend(
        [
            "",
            "## Test file",
            "```text",
            TEST_FILE_PATH,
            "```",
            "",
            "## How to run",
            "```bash",
            RUN_COMMAND,
            "```",
        ],
    )
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
            "Added a live Playwright startup regression that delays the initial GitHub "
            "`/user` probe by 2 seconds and proves the deployed shell becomes "
            "interactive shortly after the probe succeeds instead of waiting for the "
            "full timeout window.\n\n"
            "The live shell reached shell_ready before the full 11-second timeout and "
            "exposed navigation, the top-bar workspace trigger, and TrackState branding.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        "Added a live Playwright startup regression that delays the initial GitHub "
        "`/user` probe by 2 seconds and checks whether the deployed shell becomes "
        "interactive shortly after success.\n\n"
        f"{result.get('error', 'The deployed app did not prove the immediate post-probe shell-ready behavior.')}\n"
    )


def _build_bug_description(result: dict[str, Any]) -> str:
    annotated_steps = build_annotated_steps(result, request_steps=REQUEST_STEPS)
    shell_window = json.dumps(result.get("shell_window_observation"), ensure_ascii=True)
    lines = [
        f"h3. Bug report — {TICKET_KEY}",
        "",
        "h4. Environment",
        f"* URL: {result.get('app_url')}",
        f"* Browser: {result.get('browser')}",
        f"* OS: {result.get('os')}",
        f"* Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"* Repository: {result.get('repository')} @ {result.get('repository_ref')}",
        f"* Run command: {{code:bash}}{RUN_COMMAND}{{code}}",
        f"* Delayed startup probe: GitHub {{/user}} delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        f"* Full timeout window checked: {FULL_SYNC_TIMEOUT_SECONDS} seconds",
        "",
        "h4. Steps to Reproduce",
        *annotated_steps,
        "",
        "h4. Expected Result",
        EXPECTED_RESULT,
        "",
        "h4. Actual Result",
        _actual_result_summary(result, passed=False),
        "",
        "h4. Logs / Error Output",
        "{code}",
        str(result.get("traceback", result.get("error", ""))),
        "{code}",
        "",
        "h4. Notes",
        f"* GitHub requests seen: {{code}}{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}{{code}}",
        f"* Delayed requests seen: {{code}}{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}{{code}}",
        f"* Shell observation: {{code}}{shell_window}{{code}}",
    ]
    if result.get("screenshot"):
        lines.append(f"* Screenshot: {{code}}{result['screenshot']}{{code}}")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        shell_window = result.get("shell_window_observation", {})
        return (
            "After the delayed startup probe completed, the deployed app reached "
            f"shell_ready in {shell_window.get('shell_ready_after_start_seconds')!r} "
            "seconds from launch and "
            f"{shell_window.get('shell_ready_after_probe_release_seconds')!r} seconds "
            "after probe release, which is before the full 11-second timeout window, "
            "and the visible page showed the interactive shell with top-bar/workspace "
            "trigger and TrackState branding."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not prove the immediate post-probe shell-ready behavior.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_step_lines(result, jira=jira)


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_human_lines(result, jira=jira)


if __name__ == "__main__":
    main()
