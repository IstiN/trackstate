from __future__ import annotations

from dataclasses import asdict
import json
import platform
import re
import sys
import traceback
from pathlib import Path
from typing import Any, Iterable

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
    build_annotated_steps,
    build_workspace_state,
    format_human_lines,
    format_step_lines,
    prepare_local_workspace_repository,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    relative_startup_event_seconds,
    snippet,
    startup_surface_payload,
    write_test_automation_result,
)
from testing.tests.support.ts1025_startup_diagnostics_runtime import (  # noqa: E402
    Ts1025ConsoleEvent,
    Ts1025StartupDiagnosticsRuntime,
)

TICKET_KEY = "TS-1035"
TEST_CASE_TITLE = (
    "Startup diagnostics — timing delta is recorded for successful initialization paths"
)
TEST_FILE_PATH = "testing/tests/TS-1035/test_ts_1035.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1035/test_ts_1035.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1035-local"
LOCAL_DISPLAY_NAME = "TS-1035 local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXTS = ("Git-native. Jira-compatible. Team-proven.", "TrackState.AI")
SUCCESS_TIMEOUT_SECONDS = 11.0
STARTUP_RENDER_WAIT_SECONDS = 120
AUTH_PROBE_START_WAIT_SECONDS = 90
SUCCESS_WINDOW_WAIT_SECONDS = 30
LOG_PROPAGATION_WAIT_SECONDS = 5.0
POLL_INTERVAL_SECONDS = 0.25
DELTA_TOLERANCE_SECONDS = 1.5
LINKED_BUGS = ["TS-1029"]
LINKED_BUG_NOTES = (
    "Reviewed TS-1029. Its merged fix restored the live GitHub `/user` startup probe, "
    "so this test does not assert immediately after launch: it waits for the real "
    "success-path auth probe to start, waits for it to finish, and then keeps polling "
    "for the startup diagnostic entry before evaluating the logs."
)
REWORK_SUMMARY = (
    "Added a live Playwright startup regression for the normal-latency path that "
    "captures browser-console diagnostics from the deployed app and compares the "
    "reported timing delta with the observed `/user` auth-probe lifecycle."
)
REQUEST_STEPS = [
    "Launch the TrackState application in an environment with normal network latency.",
    "Wait for the application to reach the interactive 'shell_ready' state (usually < 3 seconds).",
    "Access the browser console or telemetry logs.",
    "Inspect the diagnostic log entries for the initialization sequence.",
]
EXPECTED_RESULT = (
    "A startup diagnostic entry is present for the successful initialization path, "
    "recording the auth probe lifecycle with a calculated timing delta that matches "
    "the live run."
)
IGNORED_LOG_SNIPPETS = (
    "Installing/Activating first service worker.",
    "Activated new service worker.",
    "Injecting <script> tag. Using callback.",
    "GPU stall due to ReadPixels",
    "Failed to load resource: the server responded with a status of 404",
)
AUTH_LOG_FRAGMENTS = (
    "/user",
    "auth probe",
    "auth-probe",
    "authentication probe",
    "github auth",
    "startup probe",
)
SUCCESS_LOG_FRAGMENTS = (
    "startup diagnostic",
    "successful",
    "success path",
    "resolved",
    "resolve",
    "finished",
    "completed",
    "interactive",
    "shell_ready",
    "shell ready",
)
DELTA_LOG_FRAGMENTS = ("delta", "elapsed", "duration", "timing")

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1035_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1035_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1035 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    hosted_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts1025StartupDiagnosticsRuntime(
        repository=service.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=0,
        delayed_paths=("/user",),
        workspace_token_profile_ids=(hosted_workspace_id,),
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
        "success_timeout_seconds": SUCCESS_TIMEOUT_SECONDS,
        "log_propagation_wait_seconds": LOG_PROPAGATION_WAIT_SECONDS,
        "delta_tolerance_seconds": DELTA_TOLERANCE_SECONDS,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "steps": [],
        "human_verification": [],
        "product_failure": False,
    }

    tracker_page: TrackStateTrackerPage | None = None
    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            switcher_page = LiveWorkspaceSwitcherPage(tracker_page)
            switcher_page.set_viewport(**DESKTOP_VIEWPORT)
            startup_started_at_monotonic = _monotonic()
            failures: list[str] = []

            switcher_page.open_startup_entrypoint(wait_until="commit", timeout_ms=120_000)
            startup_rendered, startup_surface = poll_until(
                probe=lambda: startup_surface_payload(tracker_page),
                is_satisfied=_startup_surface_loaded,
                timeout_seconds=STARTUP_RENDER_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["startup_observation_initial"] = startup_surface_payload(tracker_page)
            result["startup_observation_after_render"] = startup_surface
            if not startup_rendered:
                step_one_error = (
                    "Step 1 failed: the deployed app never rendered beyond the bare startup "
                    "surface before the normal startup diagnostics scenario could begin.\n"
                    f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}"
                )
                result["product_failure"] = True
                record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=step_one_error,
                )
                record_not_reached_steps(
                    result,
                    starting_step=2,
                    request_steps=REQUEST_STEPS,
                )
                raise AssertionError(step_one_error)

            auth_probe_started = runtime.wait_for_auth_probe_start(
                timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
            )
            result["github_request_urls"] = list(runtime.github_request_urls)
            result["delayed_request_urls"] = list(runtime.delayed_request_urls)
            auth_probe_started_after_start_seconds = relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.auth_probe_started_at_monotonic,
            )
            result["auth_probe_started_after_start_seconds"] = (
                auth_probe_started_after_start_seconds
            )
            if not auth_probe_started or runtime.auth_probe_started_at_monotonic is None:
                result["console_events"] = [asdict(event) for event in runtime.console_events]
                result["page_errors"] = list(runtime.page_errors)
                step_one_error = (
                    "Step 1 failed: the live app never started the GitHub `/user` startup "
                    "auth probe within the observation window, so the success-path startup "
                    "diagnostics could not be evaluated.\n"
                    f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}\n"
                    f"GitHub requests seen:\n{json.dumps(result['github_request_urls'], indent=2)}\n"
                    f"Delayed requests seen:\n{json.dumps(result['delayed_request_urls'], indent=2)}\n"
                    f"Observed body text:\n{tracker_page.body_text()}"
                )
                result["product_failure"] = True
                record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=step_one_error,
                )
                record_human_verification(
                    result,
                    check=(
                        "Viewed the live startup surface and checked whether the hosted "
                        "session ever issued the GitHub `/user` auth probe that a user "
                        "depends on for startup readiness."
                    ),
                    observed=(
                        f"body_excerpt={snippet(tracker_page.body_text())!r}; "
                        f"github_request_urls={json.dumps(result['github_request_urls'], ensure_ascii=True)}; "
                        f"delayed_request_urls={json.dumps(result['delayed_request_urls'], ensure_ascii=True)}"
                    ),
                )
                record_not_reached_steps(
                    result,
                    starting_step=2,
                    request_steps=REQUEST_STEPS,
                )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise AssertionError(step_one_error)

            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app with a stored hosted GitHub token "
                    "and preloaded hosted workspace under normal network latency.\n"
                    f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
                    f"delayed_request_urls={json.dumps(result['delayed_request_urls'], ensure_ascii=True)}"
                ),
            )

            success_window_ready, success_window = poll_until(
                probe=lambda: _observe_success_window(
                    tracker_page=tracker_page,
                    runtime=runtime,
                    startup_started_at_monotonic=startup_started_at_monotonic,
                ),
                is_satisfied=lambda observation: (
                    observation["shell_probe_state"].get(
                        "first_shell_ready_after_launch_seconds",
                    )
                    is not None
                    and observation.get("auth_probe_released_after_start_seconds") is not None
                    and not bool(observation.get("auth_pending"))
                ),
                timeout_seconds=SUCCESS_WINDOW_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["success_window_observation"] = _success_window_payload(success_window)

            shell_probe_state = success_window["shell_probe_state"]
            shell_ready_after_launch_seconds = shell_probe_state.get(
                "first_shell_ready_after_launch_seconds",
            )
            auth_probe_released_after_start_seconds = success_window.get(
                "auth_probe_released_after_start_seconds",
            )
            observed_probe_duration_seconds = _observed_delta_seconds(
                start_seconds=auth_probe_started_after_start_seconds,
                end_seconds=auth_probe_released_after_start_seconds,
            )
            observed_shell_ready_delta_seconds = _observed_delta_seconds(
                start_seconds=auth_probe_started_after_start_seconds,
                end_seconds=shell_ready_after_launch_seconds,
            )
            result["shell_probe_state"] = shell_probe_state
            result["shell_ready_after_launch_seconds"] = shell_ready_after_launch_seconds
            result["auth_probe_released_after_start_seconds"] = (
                auth_probe_released_after_start_seconds
            )
            result["observed_probe_duration_seconds"] = observed_probe_duration_seconds
            result["observed_shell_ready_delta_seconds"] = observed_shell_ready_delta_seconds

            step_two_error: str | None = None
            if not success_window_ready:
                step_two_error = (
                    "Step 2 failed: the test never reached a completed success-path "
                    "observation window with both the GitHub `/user` auth probe finished "
                    "and the interactive shell visible.\n"
                    f"Observed window:\n{json.dumps(result['success_window_observation'], indent=2)}"
                )
            elif shell_ready_after_launch_seconds is None:
                step_two_error = (
                    "Step 2 failed: the page-side shell probe never recorded the first "
                    "interactive shell transition.\n"
                    f"Observed window:\n{json.dumps(result['success_window_observation'], indent=2)}"
                )
            elif auth_probe_released_after_start_seconds is None:
                step_two_error = (
                    "Step 2 failed: the GitHub `/user` startup auth probe did not finish "
                    "during the success-path observation window.\n"
                    f"Observed window:\n{json.dumps(result['success_window_observation'], indent=2)}"
                )
            elif (
                auth_probe_started_after_start_seconds is not None
                and shell_ready_after_launch_seconds < auth_probe_started_after_start_seconds
            ):
                step_two_error = (
                    "Step 2 failed: the shell became interactive before the startup auth "
                    "probe even started, so this run did not exercise the intended success "
                    "path.\n"
                    f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}\n"
                    f"shell_ready_after_launch_seconds={shell_ready_after_launch_seconds!r}\n"
                    f"Observed window:\n{json.dumps(result['success_window_observation'], indent=2)}"
                )
            elif shell_ready_after_launch_seconds >= SUCCESS_TIMEOUT_SECONDS:
                step_two_error = (
                    "Step 2 failed: the shell did not become interactive until after the "
                    "11-second timeout boundary, so this was not a successful initialization "
                    "path before fallback.\n"
                    f"shell_ready_after_launch_seconds={shell_ready_after_launch_seconds!r}\n"
                    f"Observed window:\n{json.dumps(result['success_window_observation'], indent=2)}"
                )
            elif auth_probe_released_after_start_seconds >= SUCCESS_TIMEOUT_SECONDS:
                step_two_error = (
                    "Step 2 failed: the GitHub `/user` auth probe did not resolve before "
                    "the 11-second timeout boundary, so the requested success path was not "
                    "observed.\n"
                    f"auth_probe_released_after_start_seconds={auth_probe_released_after_start_seconds!r}\n"
                    f"Observed window:\n{json.dumps(result['success_window_observation'], indent=2)}"
                )
            elif observed_probe_duration_seconds is None or observed_probe_duration_seconds <= 0:
                step_two_error = (
                    "Step 2 failed: the test could not calculate a positive auth-probe "
                    "duration for the live startup run.\n"
                    f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}\n"
                    f"auth_probe_released_after_start_seconds={auth_probe_released_after_start_seconds!r}\n"
                    f"Observed window:\n{json.dumps(result['success_window_observation'], indent=2)}"
                )

            if step_two_error is None:
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The live app reached the interactive shell on the normal startup "
                        "path before the timeout boundary, and the startup auth probe "
                        "completed successfully.\n"
                        f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds={auth_probe_released_after_start_seconds!r}; "
                        f"shell_ready_after_launch_seconds={shell_ready_after_launch_seconds!r}; "
                        f"observed_probe_duration_seconds={observed_probe_duration_seconds!r}; "
                        f"observed_shell_ready_delta_seconds={observed_shell_ready_delta_seconds!r}; "
                        f"visible_navigation_labels={json.dumps(success_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}"
                    ),
                )
            else:
                result["product_failure"] = True
                record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=step_two_error,
                )
                record_human_verification(
                    result,
                    check=(
                        "Viewed the live startup shell and confirmed whether the same run "
                        "became interactive before the 11-second timeout."
                    ),
                    observed=(
                        f"body_excerpt={snippet(success_window['shell_observation']['body_text'])!r}; "
                        f"shell_ready_after_launch_seconds={shell_ready_after_launch_seconds!r}; "
                        f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds={auth_probe_released_after_start_seconds!r}"
                    ),
                )
                record_not_reached_steps(
                    result,
                    starting_step=3,
                    request_steps=REQUEST_STEPS,
                )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise AssertionError(step_two_error)

            logs_observed, diagnostics_window = poll_until(
                probe=lambda: _observe_diagnostics_window(
                    runtime=runtime,
                    expected_probe_duration_seconds=observed_probe_duration_seconds,
                    expected_shell_ready_delta_seconds=observed_shell_ready_delta_seconds,
                ),
                is_satisfied=lambda observation: bool(observation["matching_entries"])
                or float(observation["elapsed_since_probe_release_seconds"]) >= LOG_PROPAGATION_WAIT_SECONDS,
                timeout_seconds=LOG_PROPAGATION_WAIT_SECONDS + 5.0,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            del logs_observed
            result["console_events"] = diagnostics_window["console_events"]
            result["interesting_console_events"] = diagnostics_window["interesting_console_events"]
            result["page_errors"] = diagnostics_window["page_errors"]
            result["matching_diagnostic_entries"] = diagnostics_window["matching_entries"]
            result["console_summary"] = diagnostics_window["console_summary"]
            result["elapsed_since_probe_release_seconds"] = diagnostics_window[
                "elapsed_since_probe_release_seconds"
            ]

            if diagnostics_window["interesting_console_events"] or diagnostics_window["page_errors"]:
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=diagnostics_window["console_summary"],
                )
            else:
                step_three_error = (
                    "Step 3 failed: Playwright captured no application-specific startup log "
                    "entries and no page errors from the live browser console after waiting "
                    "for the successful startup path to settle.\n"
                    f"{diagnostics_window['console_summary']}"
                )
                result["product_failure"] = True
                failures.append(step_three_error)
                record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=step_three_error,
                )

            if diagnostics_window["matching_entries"]:
                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "The live browser console exposed a startup diagnostic entry for the "
                        "successful initialization path with a timing delta that matched the "
                        "observed auth-probe lifecycle.\n"
                        f"matching_entries={json.dumps(diagnostics_window['matching_entries'], ensure_ascii=True)}"
                    ),
                )
            else:
                step_four_error = (
                    "Step 4 failed: the live browser console did not expose a startup "
                    "diagnostic entry for the successful initialization path with a timing "
                    "delta matching the observed auth-probe lifecycle.\n"
                    f"observed_probe_duration_seconds={observed_probe_duration_seconds!r}\n"
                    f"observed_shell_ready_delta_seconds={observed_shell_ready_delta_seconds!r}\n"
                    f"Interesting console events:\n"
                    f"{json.dumps(diagnostics_window['interesting_console_events'], indent=2)}\n"
                    f"Page errors:\n{json.dumps(diagnostics_window['page_errors'], indent=2)}"
                )
                result["product_failure"] = True
                failures.append(step_four_error)
                record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=step_four_error,
                )

            record_human_verification(
                result,
                check=(
                    "Viewed the deployed app as a user and confirmed the visible shell "
                    "showed TrackState branding plus Dashboard, Board, JQL Search, "
                    "Hierarchy, and Settings."
                ),
                observed=(
                    f"body_excerpt={snippet(success_window['shell_observation']['body_text'])!r}; "
                    f"visible_navigation_labels={json.dumps(success_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}; "
                    f"branding_visible={success_window['branding_visible']!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Reviewed the same live run's browser-console evidence like a human "
                    "tester would in DevTools and checked for a success-path startup timing log."
                ),
                observed=(
                    f"interesting_console_event_count={len(diagnostics_window['interesting_console_events'])!r}; "
                    f"matching_diagnostic_entries={json.dumps(diagnostics_window['matching_entries'], ensure_ascii=True)}; "
                    f"page_errors={json.dumps(diagnostics_window['page_errors'], ensure_ascii=True)}"
                ),
            )

            if failures:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
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


def _workspace_state(repository: str) -> dict[str, object]:
    return build_workspace_state(
        repository,
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        local_display_name=LOCAL_DISPLAY_NAME,
        hosted_display_name=HOSTED_DISPLAY_NAME,
        active_workspace="hosted",
    )


def _prepare_local_workspace_repository() -> dict[str, object]:
    return prepare_local_workspace_repository(
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        marker_filename=".trackstate-ts1035-precondition.txt",
        marker_contents="Prepared for TS-1035 startup success-path diagnostics validation.\n",
        commit_author_name="TS-1035 Automation",
        commit_author_email="ts1035@example.com",
        commit_message="Prepare TS-1035 local workspace",
    )


def _startup_surface_loaded(observation: dict[str, Any]) -> bool:
    body_text = str(observation.get("body_text", "")).strip()
    title = str(observation.get("title", "")).strip()
    button_labels = observation.get("button_labels", [])
    return bool(button_labels) or (len(body_text) > len(title) and body_text != title)


def _observe_success_window(
    *,
    tracker_page: TrackStateTrackerPage,
    runtime: Ts1025StartupDiagnosticsRuntime,
    startup_started_at_monotonic: float,
) -> dict[str, Any]:
    shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
        timeout_ms=1_000,
    )
    body_text = str(shell_observation.get("body_text", ""))
    return {
        "shell_observation": shell_observation,
        "startup_observation": startup_surface_payload(tracker_page),
        "shell_probe_state": runtime.read_shell_probe_state(),
        "branding_visible": any(branding_text in body_text for branding_text in BRANDING_TEXTS),
        "auth_pending": runtime.auth_probe_pending,
        "auth_probe_started_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_started_at_monotonic,
        ),
        "auth_probe_released_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_released_at_monotonic,
        ),
    }


def _success_window_payload(observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "shell_observation": observation.get("shell_observation"),
        "startup_observation": observation.get("startup_observation"),
        "shell_probe_state": observation.get("shell_probe_state"),
        "branding_visible": observation.get("branding_visible"),
        "auth_pending": observation.get("auth_pending"),
        "auth_probe_started_after_start_seconds": observation.get(
            "auth_probe_started_after_start_seconds",
        ),
        "auth_probe_released_after_start_seconds": observation.get(
            "auth_probe_released_after_start_seconds",
        ),
    }


def _observe_diagnostics_window(
    *,
    runtime: Ts1025StartupDiagnosticsRuntime,
    expected_probe_duration_seconds: float | None,
    expected_shell_ready_delta_seconds: float | None,
) -> dict[str, Any]:
    interesting_logs = _interesting_console_events(runtime.console_events)
    matching_entries = _diagnostic_console_events(
        interesting_logs=interesting_logs,
        page_errors=runtime.page_errors,
        expected_probe_duration_seconds=expected_probe_duration_seconds,
        expected_shell_ready_delta_seconds=expected_shell_ready_delta_seconds,
    )
    elapsed_since_probe_release_seconds = _elapsed_since(runtime.auth_probe_released_at_monotonic)
    return {
        "console_events": [asdict(event) for event in runtime.console_events],
        "interesting_console_events": [asdict(event) for event in interesting_logs],
        "page_errors": list(runtime.page_errors),
        "matching_entries": matching_entries,
        "console_summary": _console_summary(
            interesting_logs=interesting_logs,
            page_errors=runtime.page_errors,
        ),
        "elapsed_since_probe_release_seconds": elapsed_since_probe_release_seconds,
    }


def _monotonic() -> float:
    import time

    return time.monotonic()


def _elapsed_since(event_monotonic: float | None) -> float:
    if event_monotonic is None:
        return 0.0
    return round(_monotonic() - event_monotonic, 2)


def _observed_delta_seconds(
    *,
    start_seconds: float | None,
    end_seconds: float | None,
) -> float | None:
    if start_seconds is None or end_seconds is None:
        return None
    return round(float(end_seconds) - float(start_seconds), 2)


def _interesting_console_events(
    console_events: list[Ts1025ConsoleEvent],
) -> list[Ts1025ConsoleEvent]:
    return [
        event
        for event in console_events
        if not any(snippet in event.text for snippet in IGNORED_LOG_SNIPPETS)
    ]


def _diagnostic_console_events(
    *,
    interesting_logs: list[Ts1025ConsoleEvent],
    page_errors: list[str],
    expected_probe_duration_seconds: float | None,
    expected_shell_ready_delta_seconds: float | None,
) -> list[str]:
    matches: list[str] = []
    for text in _candidate_log_texts(interesting_logs, page_errors):
        lowered = text.lower()
        if not any(fragment in lowered for fragment in AUTH_LOG_FRAGMENTS):
            continue
        if not any(fragment in lowered for fragment in SUCCESS_LOG_FRAGMENTS):
            continue
        if "timeout fallback" in lowered:
            continue
        if not any(fragment in lowered for fragment in DELTA_LOG_FRAGMENTS) and not _contains_close_numeric_value(
            text,
            expected_values=_expected_delta_values(
                expected_probe_duration_seconds=expected_probe_duration_seconds,
                expected_shell_ready_delta_seconds=expected_shell_ready_delta_seconds,
            ),
        ):
            continue
        matches.append(text)
    return matches


def _candidate_log_texts(
    interesting_logs: Iterable[Ts1025ConsoleEvent],
    page_errors: Iterable[str],
) -> list[str]:
    return [event.text for event in interesting_logs] + [str(error) for error in page_errors]


def _expected_delta_values(
    *,
    expected_probe_duration_seconds: float | None,
    expected_shell_ready_delta_seconds: float | None,
) -> tuple[float, ...]:
    values: list[float] = []
    if expected_probe_duration_seconds is not None:
        values.append(float(expected_probe_duration_seconds))
    if expected_shell_ready_delta_seconds is not None:
        values.append(float(expected_shell_ready_delta_seconds))
    return tuple(values)


def _contains_close_numeric_value(text: str, *, expected_values: tuple[float, ...]) -> bool:
    if not expected_values:
        return False
    for match in re.finditer(r"(?<!\d)(\d+(?:\.\d+)?)(?!\d)", text):
        value = float(match.group(1))
        if any(abs(value - expected) <= DELTA_TOLERANCE_SECONDS for expected in expected_values):
            return True
    return False


def _console_summary(
    *,
    interesting_logs: list[Ts1025ConsoleEvent],
    page_errors: list[str],
) -> str:
    if not interesting_logs and not page_errors:
        return (
            "No application-specific startup diagnostics were captured. The browser "
            "emitted only generic service-worker / GPU noise, and no page errors were raised."
        )
    lines = ["Startup diagnostics captured:"]
    for event in interesting_logs:
        lines.append(f"- [{event.level}] {event.text}")
    if page_errors:
        lines.append("Page errors:")
        for error in page_errors:
            lines.append(f"- {error}")
    return "\n".join(lines)


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
        "h4. What was automated",
        "* Preloaded a hosted workspace plus fallback local workspace for the deployed app.",
        "* Exercised the normal GitHub {/user} startup auth probe with no synthetic delay and waited for the interactive shell to become visible.",
        "* Continued polling after the auth probe completed so any delayed success-path startup diagnostics had time to appear before asserting.",
        "* Required a startup diagnostic entry whose timing delta matches the live auth-probe lifecycle observed in the same browser session.",
        "",
        "h4. Result",
        f"* {_actual_result_summary(result, passed=passed)}",
        *format_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *format_human_lines(result, jira=True),
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
        f"- {REWORK_SUMMARY}",
        "",
        "## What was automated",
        "- Preloaded a hosted workspace plus fallback local workspace for the deployed app.",
        "- Exercised the normal GitHub `/user` startup auth probe with no synthetic delay and waited for the live shell to become interactive.",
        "- Kept polling the same browser session after the probe completed so delayed success-path diagnostics had time to surface.",
        "- Required a startup diagnostic entry whose timing delta matches the observed auth-probe lifecycle from the same run.",
        "",
        "## Result",
        f"- {_actual_result_summary(result, passed=passed)}",
        *format_step_lines(result, jira=False),
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
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "The live run reached the interactive shell on the normal startup path and "
            "the browser console exposed a matching success-path startup diagnostic entry.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not expose the expected success-path startup diagnostics.')}\n"
    )


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    error = str(result.get("error", ""))
    if error.startswith("RuntimeError: TS-1035 requires GH_TOKEN or GITHUB_TOKEN"):
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
        f"- Success timeout boundary: {SUCCESS_TIMEOUT_SECONDS} seconds",
        f"- Observed auth probe duration: {result.get('observed_probe_duration_seconds')!r}",
        f"- Observed shell_ready delta: {result.get('observed_shell_ready_delta_seconds')!r}",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Success window observation: `{json.dumps(result.get('success_window_observation'), ensure_ascii=True)}`",
        f"- Console events: `{json.dumps(result.get('console_events', []), ensure_ascii=True)}`",
        f"- Interesting console events: `{json.dumps(result.get('interesting_console_events', []), ensure_ascii=True)}`",
        f"- Matching diagnostic entries: `{json.dumps(result.get('matching_diagnostic_entries', []), ensure_ascii=True)}`",
        f"- Page errors: `{json.dumps(result.get('page_errors', []), ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "The live app reached the interactive shell before the timeout boundary, the "
            "GitHub `/user` startup auth probe completed, and the browser console exposed "
            "a success-path startup diagnostic entry whose timing delta matched the same run."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not expose the expected success-path startup diagnostic entry.",
        ),
    )


if __name__ == "__main__":
    main()
