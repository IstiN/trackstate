from __future__ import annotations

from dataclasses import asdict
import json
import platform
import re
import sys
import time
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
    snippet,
    startup_surface_payload,
    write_test_automation_result,
)
from testing.tests.support.ts1025_startup_diagnostics_runtime import (  # noqa: E402
    Ts1025ConsoleEvent,
    Ts1025StartupDiagnosticsRuntime,
)

TICKET_KEY = "TS-1025"
TEST_CASE_TITLE = (
    "Startup diagnostics — logs capture timing delta for authentication probe fallback"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1025/test_ts_1025.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1025-local"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SYNC_TIMEOUT_SECONDS = 11
SIMULATED_PROBE_DELAY_SECONDS = 30
AUTH_PROBE_START_WAIT_SECONDS = 90
TIMEOUT_ASSERTION_SECONDS = SYNC_TIMEOUT_SECONDS + 1
STARTUP_RENDER_WAIT_SECONDS = 120
OBSERVATION_TIMEOUT_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + AUTH_PROBE_START_WAIT_SECONDS
POLL_INTERVAL_SECONDS = 0.25
DELTA_TOLERANCE_SECONDS = 1.5
LINKED_BUGS = ["TS-1029", "TS-1027", "TS-1022"]
LINKED_BUG_NOTES = (
    "Reviewed TS-1029, TS-1027, and TS-1022. Their merged fixes require the delayed "
    "GitHub `/user` startup probe to begin from an authenticated hosted workspace, stay "
    "pending long enough to observe the timeout fallback, and expose a same-run "
    "diagnostic entry that records the auth-probe-to-`shell_ready` delta."
)
REWORK_SUMMARY = (
    "Seeded the hosted workspace token for the active hosted profile, kept the "
    "authoritative `shell_ready` timing check after the delayed `/user` probe is "
    "already pending, and now read same-run startup diagnostics from in-page plus "
    "Playwright console capture."
)
REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Wait for the 11-second synchronization timeout to expire and the UI shell to render (shell_ready=true).",
    "Access the application logs (for this automation, the live browser console captured by Playwright).",
    "Inspect the entries recorded during the initialization sequence.",
]
EXPECTED_RESULT = (
    "The logs contain a diagnostic entry that explicitly captures the initiation of "
    "the auth probe and the shell state transition, including a calculated delta of "
    "approximately 11 seconds."
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
    "probe start",
    "probe initiated",
)
SHELL_LOG_FRAGMENTS = (
    "shell_ready",
    "shell ready",
    "shellready",
    "forced transition",
    "transition",
    "interactive",
    "startup fallback",
)
DELTA_LOG_FRAGMENTS = ("delta", "elapsed", "timeout", "11", "11.0", "11.00")
_DIAGNOSTIC_KEYWORD_GROUPS: tuple[tuple[str, ...], ...] = (
    ("startup", "probe"),
    ("startup", "shell_ready"),
    ("startup", "shell ready"),
    ("auth", "probe"),
    ("/user", "startup"),
    ("timeout", "fallback"),
    ("hosted startup deferred", "/user"),
    ("shell can open while repository data keeps loading", "/user"),
)
_DELTA_PATTERNS = (
    re.compile(r"delta(?:_|)(?:ms|milliseconds)[=: ]+(\d{4,6})", re.IGNORECASE),
    re.compile(r"delta(?:_|)(?:seconds|sec|s)?[=: ]+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"elapsed(?:_|)(?:ms|milliseconds)[=: ]+(\d{4,6})", re.IGNORECASE),
    re.compile(r"elapsed(?:_|)(?:seconds|sec|s)?[=: ]+(\d+(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"delta[^0-9]*(\d+(?:\.\d+)?)\s*s(?:ec(?:onds)?)?", re.IGNORECASE),
    re.compile(r"after[^0-9]*(\d+(?:\.\d+)?)\s*s(?:ec(?:onds)?)?", re.IGNORECASE),
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
INPUT_DIR = REPO_ROOT / "input" / TICKET_KEY
DISCUSSIONS_RAW_PATH = INPUT_DIR / "pr_discussions_raw.json"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1025_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1025_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1025 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    hosted_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts1025StartupDiagnosticsRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        auth_delay_seconds=SIMULATED_PROBE_DELAY_SECONDS,
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
        "sync_timeout_seconds": SYNC_TIMEOUT_SECONDS,
        "timeout_assertion_seconds": TIMEOUT_ASSERTION_SECONDS,
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
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
            page = LiveWorkspaceSwitcherPage(tracker_page)
            page.set_viewport(**DESKTOP_VIEWPORT)
            startup_started_at_monotonic = time.monotonic()
            failures: list[str] = []

            page.open_startup_entrypoint(wait_until="commit", timeout_ms=120_000)
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
                    "Step 1 failed: the deployed app never rendered beyond the bare "
                    "startup surface before the delayed-auth scenario could be inspected.\n"
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
                diagnostic_state = _safe_read_diagnostic_state(runtime)
                result["console_events"] = [asdict(event) for event in runtime.console_events]
                interesting_logs = _interesting_console_events(runtime.console_events)
                result["interesting_console_events"] = [
                    asdict(event) for event in interesting_logs
                ]
                result["page_errors"] = list(runtime.page_errors)
                result["diagnostic_state"] = diagnostic_state
                result["interesting_diagnostic_entries"] = _interesting_diagnostic_entries(
                    diagnostic_state,
                )
                step_one_error = (
                    "Step 1 failed: the live app never started the delayed GitHub `/user` "
                    "startup auth probe within the observation window, so the startup "
                    "diagnostic fallback scenario could not be observed.\n"
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
                        "Viewed the startup shell as a user and checked whether the hosted "
                        "session ever triggered the delayed GitHub `/user` auth probe."
                    ),
                    observed=(
                        f"body_excerpt={snippet(tracker_page.body_text())!r}; "
                        f"github_request_urls={json.dumps(result['github_request_urls'], ensure_ascii=True)}; "
                        f"delayed_request_urls={json.dumps(result['delayed_request_urls'], ensure_ascii=True)}; "
                        f"matching_diagnostic_entries="
                        f"{json.dumps(result['interesting_diagnostic_entries'][:3], ensure_ascii=True)}"
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
                    "Opened the deployed TrackState app with a stored hosted GitHub token, "
                    "a preloaded hosted workspace, and a synthetic 30-second delay on the "
                    "GitHub `/user` auth probe.\n"
                    f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
                    f"delayed_request_urls={json.dumps(result['delayed_request_urls'], ensure_ascii=True)}"
                ),
            )

            transition_tracker = ShellReadyTransitionTracker()
            timeout_reached, timeout_window = poll_until(
                probe=lambda: _observe_timeout_window(
                    tracker_page=tracker_page,
                    page=page,
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
            result["timeout_window_observation"] = _timeout_window_payload(timeout_window)
            result["console_events"] = [asdict(event) for event in runtime.console_events]
            interesting_logs = _interesting_console_events(runtime.console_events)
            result["interesting_console_events"] = [
                asdict(event) for event in interesting_logs
            ]
            result["page_errors"] = list(runtime.page_errors)
            diagnostic_state = _safe_read_diagnostic_state(runtime)
            result["diagnostic_state"] = diagnostic_state

            shell_probe_state = timeout_window.get("shell_probe_state", {})
            shell_ready_after_launch_seconds = timeout_window.get(
                "shell_ready_after_start_seconds",
            )
            first_shell_ready_after_launch_seconds = shell_probe_state.get(
                "first_shell_ready_after_launch_seconds",
            )
            probe_recorded_shell_ready_after_start_seconds = timeout_window.get(
                "probe_recorded_shell_ready_after_start_seconds",
            )
            first_auth_probe_released_after_start_seconds = timeout_window.get(
                "first_auth_probe_released_after_start_seconds",
            )
            shell_ready_during_first_pending = (
                first_shell_ready_after_launch_seconds is not None
                and auth_probe_started_after_start_seconds is not None
                and (
                    first_auth_probe_released_after_start_seconds is None
                    or float(first_shell_ready_after_launch_seconds)
                    < float(first_auth_probe_released_after_start_seconds)
                )
            )
            authoritative_shell_ready_after_start_seconds = (
                probe_recorded_shell_ready_after_start_seconds
                if probe_recorded_shell_ready_after_start_seconds is not None
                else (
                    first_shell_ready_after_launch_seconds
                    if shell_ready_during_first_pending
                    else (
                        shell_ready_after_launch_seconds
                        if bool(timeout_window.get("shell_ready_observed_while_auth_pending"))
                        else None
                    )
                )
            )
            authoritative_shell_ready_source = (
                "python-pending-sample"
                if probe_recorded_shell_ready_after_start_seconds is not None
                else (
                    "page-shell-probe"
                    if shell_ready_during_first_pending
                    else None
                )
            )
            result["shell_probe_state"] = shell_probe_state
            result["shell_transition_tracker"] = {
                "first_auth_probe_released_after_start_seconds": (
                    first_auth_probe_released_after_start_seconds
                ),
                "first_shell_ready_after_launch_seconds": shell_ready_after_launch_seconds,
                "first_shell_ready_probe_after_launch_seconds": (
                    first_shell_ready_after_launch_seconds
                ),
                "probe_recorded_shell_ready_after_start_seconds": (
                    probe_recorded_shell_ready_after_start_seconds
                ),
                "authoritative_shell_ready_after_start_seconds": (
                    authoritative_shell_ready_after_start_seconds
                ),
                "authoritative_shell_ready_source": authoritative_shell_ready_source,
                "shell_ready_during_first_pending": shell_ready_during_first_pending,
                "shell_ready_observed_while_auth_pending": timeout_window.get(
                    "shell_ready_observed_while_auth_pending",
                ),
            }
            observed_delta_seconds = _observed_delta_seconds(
                auth_probe_started_after_start_seconds=auth_probe_started_after_start_seconds,
                shell_ready_after_launch_seconds=authoritative_shell_ready_after_start_seconds,
            )
            result["observed_delta_seconds"] = observed_delta_seconds

            step_two_error: str | None = None
            timeout_path_invalid = False
            if not timeout_reached:
                step_two_error = (
                    "Step 2 failed: the test never reached the post-timeout observation "
                    "window while the delayed auth probe was being monitored.\n"
                    f"Observed timeout window:\n{json.dumps(result['timeout_window_observation'], indent=2)}"
                )
            elif shell_ready_after_launch_seconds is None:
                step_two_error = (
                    "Step 2 failed: the app never recorded a `shell_ready` transition "
                    "during the delayed-auth startup run.\n"
                    f"Observed timeout window:\n{json.dumps(result['timeout_window_observation'], indent=2)}"
                )
            elif (
                auth_probe_started_after_start_seconds is not None
                and shell_ready_after_launch_seconds < auth_probe_started_after_start_seconds
            ):
                timeout_path_invalid = True
                step_two_error = (
                    "Step 2 failed: the shell was already visible before the delayed "
                    "GitHub `/user` auth probe started, so this run did not prove the "
                    "timeout-fallback transition.\n"
                    f"first_shell_ready_after_launch_seconds={shell_ready_after_launch_seconds!r}\n"
                    f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}\n"
                    f"probe_recorded_shell_ready_after_start_seconds="
                    f"{probe_recorded_shell_ready_after_start_seconds!r}\n"
                    f"Observed timeout window:\n{json.dumps(result['timeout_window_observation'], indent=2)}"
                )
            elif (
                not bool(timeout_window.get("auth_pending"))
                and not shell_ready_during_first_pending
            ):
                step_two_error = (
                    "Step 2 failed: the delayed GitHub `/user` auth probe was no longer "
                    "pending when the 11-second timeout window was inspected, so the live "
                    "timeout fallback state was not observed, and the page-side shell probe "
                    "did not capture an earlier `shell_ready` transition before the first "
                    "delayed auth request was released.\n"
                    f"Observed timeout window:\n{json.dumps(result['timeout_window_observation'], indent=2)}"
                )
            elif not bool(timeout_window["shell_observation"]["shell_ready"]):
                step_two_error = (
                    "Step 2 failed: after waiting past the 11-second synchronization timeout, "
                    "the visible shell was still not interactive.\n"
                    f"Observed timeout window:\n{json.dumps(result['timeout_window_observation'], indent=2)}"
                )
            elif authoritative_shell_ready_after_start_seconds is None:
                step_two_error = (
                    "Step 2 failed: the test could not capture an authoritative "
                    "`shell_ready` timestamp recorded after the delayed auth probe "
                    "became pending.\n"
                    f"first_shell_ready_after_launch_seconds={shell_ready_after_launch_seconds!r}\n"
                    f"probe_recorded_shell_ready_after_start_seconds="
                    f"{probe_recorded_shell_ready_after_start_seconds!r}\n"
                    f"Observed timeout window:\n{json.dumps(result['timeout_window_observation'], indent=2)}"
                )
            elif observed_delta_seconds is None:
                step_two_error = (
                    "Step 2 failed: the test could not calculate the delta between the "
                    "auth probe start and the authoritative `shell_ready` transition.\n"
                    f"Observed timeout window:\n{json.dumps(result['timeout_window_observation'], indent=2)}"
                )
            elif not _delta_is_approximately_timeout(observed_delta_seconds):
                step_two_error = (
                    "Step 2 failed: the authoritative `shell_ready` transition did not "
                    "happen at approximately the 11-second timeout boundary from the "
                    "delayed auth probe start.\n"
                    f"authoritative_shell_ready_after_start_seconds="
                    f"{authoritative_shell_ready_after_start_seconds!r}\n"
                    f"observed_delta_seconds={observed_delta_seconds!r}\n"
                    f"Observed timeout window:\n{json.dumps(result['timeout_window_observation'], indent=2)}"
                )

            if step_two_error is None:
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Waited beyond the 11-second timeout from the delayed `/user` auth "
                        "probe start while the probe remained pending, and the live shell "
                        "was already visible.\n"
                        f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
                        f"first_shell_ready_after_launch_seconds={shell_ready_after_launch_seconds!r}; "
                        f"first_shell_ready_probe_after_launch_seconds={first_shell_ready_after_launch_seconds!r}; "
                        f"first_auth_probe_released_after_start_seconds="
                        f"{first_auth_probe_released_after_start_seconds!r}; "
                        f"probe_recorded_shell_ready_after_start_seconds="
                        f"{probe_recorded_shell_ready_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"authoritative_shell_ready_source={authoritative_shell_ready_source!r}; "
                        f"observed_delta_seconds={observed_delta_seconds!r}; "
                        f"visible_navigation_labels={json.dumps(timeout_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}"
                    ),
                )
            else:
                if not timeout_path_invalid:
                    result["product_failure"] = True
                failures.append(step_two_error)
                record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=step_two_error,
                )
                record_not_reached_steps(
                    result,
                    starting_step=3,
                    request_steps=REQUEST_STEPS,
                )
                record_human_verification(
                    result,
                    check=(
                        "Viewed the live startup shell and compared the first visible "
                        "`shell_ready` evidence with the delayed GitHub `/user` probe start."
                    ),
                    observed=(
                        f"body_excerpt={snippet(timeout_window['shell_observation']['body_text'])!r}; "
                        f"first_shell_ready_after_launch_seconds={shell_ready_after_launch_seconds!r}; "
                        f"probe_recorded_shell_ready_after_start_seconds="
                        f"{probe_recorded_shell_ready_after_start_seconds!r}; "
                        f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
                        f"auth_pending_at_timeout_window={timeout_window.get('auth_pending')!r}"
                    ),
                )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise AssertionError(step_two_error)

            diagnostic_entries = _interesting_diagnostic_entries(diagnostic_state)
            result["interesting_diagnostic_entries"] = diagnostic_entries
            diagnostic_delta_seconds = _parse_diagnostic_delta_seconds(diagnostic_entries)
            result["diagnostic_delta_seconds"] = diagnostic_delta_seconds
            diagnostic_summary = _diagnostic_summary(
                diagnostic_state=diagnostic_state,
                interesting_entries=diagnostic_entries,
            )
            if diagnostic_entries:
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=diagnostic_summary,
                )
            else:
                step_three_error = (
                    "Step 3 failed: same-run in-page plus Playwright console capture found "
                    "no application-specific startup diagnostic entries.\n"
                    f"{diagnostic_summary}"
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

            matching_entries = _matching_diagnostic_entries(
                entries=diagnostic_entries,
                expected_delta_seconds=observed_delta_seconds,
            )
            result["matching_diagnostic_entries"] = matching_entries
            step_four_error = _step_four_error(
                entries=matching_entries or diagnostic_entries,
                diagnostic_delta_seconds=diagnostic_delta_seconds,
            )
            if step_four_error is None and matching_entries:
                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "The live browser console exposed a startup diagnostic entry that "
                        "linked the delayed auth probe to the shell transition and included "
                        "an approximately 11-second delta.\n"
                        f"matching_entries={json.dumps(matching_entries, ensure_ascii=True)}"
                    ),
                )
            else:
                if step_four_error is None:
                    step_four_error = (
                        "Step 4 failed: startup diagnostics were captured, but none of the "
                        "entries tied the delayed GitHub `/user` auth probe to the "
                        "`shell_ready` transition with the expected delta.\n"
                        f"observed_delta_seconds={observed_delta_seconds!r}\n"
                        f"Observed diagnostic entries:\n{json.dumps(diagnostic_entries, indent=2)}"
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
                    "Viewed the live startup shell the way a user would and confirmed the "
                    "page became interactive with visible TrackState branding and navigation."
                ),
                observed=(
                    f"body_excerpt={snippet(timeout_window['shell_observation']['body_text'])!r}; "
                    f"visible_navigation_labels={json.dumps(timeout_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}; "
                    f"branding_visible={timeout_window['branding_visible']!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Opened the same live run's browser-console evidence and inspected the "
                    "startup log entries a human tester would review in DevTools."
                ),
                observed=(
                    f"interesting_console_event_count={len(diagnostic_entries)!r}; "
                    f"matching_diagnostic_entries={json.dumps(matching_entries, ensure_ascii=True)}; "
                    f"page_errors={json.dumps(runtime.page_errors, ensure_ascii=True)}"
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
        marker_filename=".trackstate-ts1025-precondition.txt",
        marker_contents="Prepared for TS-1025 startup diagnostics validation.\n",
        commit_author_name="TS-1025 Automation",
        commit_author_email="ts1025@example.com",
        commit_message="Prepare TS-1025 local workspace",
    )


def _startup_surface_loaded(observation: dict[str, Any]) -> bool:
    body_text = str(observation.get("body_text", "")).strip()
    title = str(observation.get("title", "")).strip()
    button_labels = observation.get("button_labels", [])
    return bool(button_labels) or (len(body_text) > len(title) and body_text != title)


def _observe_timeout_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts1025StartupDiagnosticsRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
) -> dict[str, Any]:
    observation = observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
        transition_tracker=transition_tracker,
        poll_timeout_ms=500,
    )
    observation["shell_probe_state"] = runtime.read_shell_probe_state()
    observation["first_auth_probe_released_after_start_seconds"] = (
        relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.first_auth_probe_released_at_monotonic,
        )
    )
    return observation


def _timeout_window_payload(observation: dict[str, Any]) -> dict[str, Any]:
    return {
        "shell_observation": observation.get("shell_observation"),
        "startup_observation": observation.get("startup_observation"),
        "trigger": observation.get("trigger"),
        "branding_visible": observation.get("branding_visible"),
        "auth_pending": observation.get("auth_pending"),
        "auth_probe_started_after_start_seconds": observation.get(
            "auth_probe_started_after_start_seconds",
        ),
        "auth_probe_released_after_start_seconds": observation.get(
            "auth_probe_released_after_start_seconds",
        ),
        "first_auth_probe_released_after_start_seconds": observation.get(
            "first_auth_probe_released_after_start_seconds",
        ),
        "auth_probe_release_after_auth_start_seconds": observation.get(
            "auth_probe_release_after_auth_start_seconds",
        ),
        "elapsed_since_auth_start_seconds": observation.get(
            "elapsed_since_auth_start_seconds",
        ),
        "probe_recorded_shell_ready_after_start_seconds": observation.get(
            "probe_recorded_shell_ready_after_start_seconds",
        ),
        "shell_ready_after_start_seconds": observation.get(
            "shell_ready_after_start_seconds",
        ),
        "shell_ready_after_probe_release_seconds": observation.get(
            "shell_ready_after_probe_release_seconds",
        ),
        "shell_ready_observed_while_auth_pending": observation.get(
            "shell_ready_observed_while_auth_pending",
        ),
        "shell_probe_state": observation.get("shell_probe_state"),
    }


def _observed_delta_seconds(
    *,
    auth_probe_started_after_start_seconds: float | None,
    shell_ready_after_launch_seconds: float | None,
) -> float | None:
    if (
        auth_probe_started_after_start_seconds is None
        or shell_ready_after_launch_seconds is None
    ):
        return None
    return round(
        float(shell_ready_after_launch_seconds)
        - float(auth_probe_started_after_start_seconds),
        2,
    )


def _delta_is_approximately_timeout(delta_seconds: float) -> bool:
    return abs(delta_seconds - SYNC_TIMEOUT_SECONDS) <= DELTA_TOLERANCE_SECONDS


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
    expected_delta_seconds: float | None,
) -> list[str]:
    matches: list[str] = []
    for text in _candidate_log_texts(interesting_logs, page_errors):
        lowered = text.lower()
        if not any(fragment in lowered for fragment in AUTH_LOG_FRAGMENTS):
            continue
        if not any(fragment in lowered for fragment in SHELL_LOG_FRAGMENTS):
            continue
        if not any(fragment in lowered for fragment in DELTA_LOG_FRAGMENTS) and not _contains_close_numeric_value(
            text,
            expected_values=_expected_delta_values(expected_delta_seconds),
        ):
            continue
        matches.append(text)
    return matches


def _safe_read_diagnostic_state(
    runtime: Ts1025StartupDiagnosticsRuntime,
) -> dict[str, Any]:
    try:
        return runtime.read_startup_diagnostic_state()
    except Exception as error:  # pragma: no cover - diagnostics only
        return {
            "in_page_console_events": [],
            "in_page_page_errors": [f"{type(error).__name__}: {error}"],
            "in_page_unhandled_rejections": [],
            "playwright_console_messages": [],
            "playwright_page_errors": [],
        }


def _interesting_diagnostic_entries(diagnostic_state: dict[str, Any]) -> list[str]:
    raw_entries: list[str] = []
    for entry in diagnostic_state.get("in_page_console_events", []):
        if isinstance(entry, dict):
            raw_entries.append(str(entry.get("text", "")))
    for entry in diagnostic_state.get("playwright_console_messages", []):
        if isinstance(entry, dict):
            raw_entries.append(str(entry.get("text", "")))
    for entry in diagnostic_state.get("in_page_page_errors", []):
        if isinstance(entry, str):
            raw_entries.append(entry)
    for entry in diagnostic_state.get("playwright_page_errors", []):
        if isinstance(entry, str):
            raw_entries.append(entry)
    seen: set[str] = set()
    filtered: list[str] = []
    for entry in raw_entries:
        normalized = " ".join(entry.split())
        if not normalized:
            continue
        lowered = normalized.lower()
        if not any(
            all(keyword in lowered for keyword in group)
            for group in _DIAGNOSTIC_KEYWORD_GROUPS
        ):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        filtered.append(normalized)
    return filtered


def _matching_diagnostic_entries(
    *,
    entries: list[str],
    expected_delta_seconds: float | None,
) -> list[str]:
    matches: list[str] = []
    for entry in entries:
        lowered = entry.lower()
        if not any(fragment in lowered for fragment in AUTH_LOG_FRAGMENTS):
            continue
        if not any(fragment in lowered for fragment in SHELL_LOG_FRAGMENTS):
            continue
        if not any(fragment in lowered for fragment in DELTA_LOG_FRAGMENTS) and not _contains_close_numeric_value(
            entry,
            expected_values=_expected_delta_values(expected_delta_seconds),
        ):
            continue
        matches.append(entry)
    return matches


def _parse_diagnostic_delta_seconds(entries: list[str]) -> float | None:
    for entry in entries:
        for pattern in _DELTA_PATTERNS:
            match = pattern.search(entry)
            if not match:
                continue
            value = float(match.group(1))
            if value > 1000:
                value /= 1000.0
            return round(value, 2)
    return None


def _step_four_error(
    *,
    entries: list[str],
    diagnostic_delta_seconds: float | None,
) -> str | None:
    if not entries:
        return (
            "The live startup diagnostics did not expose any application-specific entry "
            "that tied the delayed GitHub `/user` auth probe to the `shell_ready` transition."
        )
    if diagnostic_delta_seconds is None:
        return (
            "The live startup diagnostics mentioned the delayed auth probe or the "
            "`shell_ready` transition, but none of the entries exposed a parseable timing delta.\n"
            f"Observed diagnostic entries:\n{json.dumps(entries, indent=2)}"
        )
    if not _delta_is_approximately_timeout(diagnostic_delta_seconds):
        return (
            "The live startup diagnostics exposed a timing delta, but it was outside the "
            "expected ~11-second timeout window.\n"
            f"diagnostic_delta_seconds={diagnostic_delta_seconds!r}\n"
            f"Observed diagnostic entries:\n{json.dumps(entries, indent=2)}"
        )
    return None


def _candidate_log_texts(
    interesting_logs: Iterable[Ts1025ConsoleEvent],
    page_errors: Iterable[str],
) -> list[str]:
    return [event.text for event in interesting_logs] + [str(error) for error in page_errors]


def _expected_delta_values(observed_delta_seconds: float | None) -> tuple[float, ...]:
    values = [float(SYNC_TIMEOUT_SECONDS)]
    if observed_delta_seconds is not None:
        values.append(float(observed_delta_seconds))
    return tuple(values)


def _contains_close_numeric_value(text: str, *, expected_values: tuple[float, ...]) -> bool:
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


def _diagnostic_summary(
    *,
    diagnostic_state: dict[str, Any],
    interesting_entries: list[str],
) -> str:
    if not interesting_entries:
        return (
            "No application-specific startup diagnostics were captured. "
            f"in_page_console_event_count={len(diagnostic_state.get('in_page_console_events', []))}; "
            f"playwright_console_message_count={len(diagnostic_state.get('playwright_console_messages', []))}; "
            f"in_page_page_error_count={len(diagnostic_state.get('in_page_page_errors', []))}; "
            f"playwright_page_error_count={len(diagnostic_state.get('playwright_page_errors', []))}"
        )
    return (
        "Captured same-run startup diagnostics from the live browser session.\n"
        f"in_page_console_event_count={len(diagnostic_state.get('in_page_console_events', []))}; "
        f"playwright_console_message_count={len(diagnostic_state.get('playwright_console_messages', []))}; "
        f"interesting_entries={json.dumps(interesting_entries, ensure_ascii=True)}"
    )


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")
    _write_review_replies(result, passed=True)


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    _write_review_replies(result, passed=False)
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
        "* Delayed the live GitHub {/user} auth probe by 30 seconds and waited beyond the 11-second timeout before asserting.",
        "* Verified the user-visible shell became interactive and then inspected the live browser console captured from the same run.",
        "* Required a diagnostic log entry that links the auth probe start to the shell_ready transition with an approximately 11-second delta.",
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
        "testing/tests/TS-1025/test_ts_1025.py",
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
        "- Delayed the live GitHub `/user` auth probe by 30 seconds and waited beyond the 11-second timeout instead of asserting immediately.",
        "- Verified the visible shell became interactive from the user's perspective and then inspected the live browser-console logs from the same run.",
        "- Required a startup diagnostic entry that links the auth probe start to the `shell_ready` transition with an approximately 11-second delta.",
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
            "The live run reached `shell_ready` after the delayed auth-probe timeout and "
            "the browser console exposed a matching startup diagnostic entry.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not expose the expected startup diagnostics.')}\n"
    )


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    error = str(result.get("error", ""))
    if error.startswith("RuntimeError: TS-1025 requires GH_TOKEN or GITHUB_TOKEN"):
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
        f"- Simulated delayed auth probe: GitHub `/user` delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        f"- Timeout assertion boundary: {TIMEOUT_ASSERTION_SECONDS} seconds from delayed `/user` probe start",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Timeout window observation: `{json.dumps(result.get('timeout_window_observation'), ensure_ascii=True)}`",
        f"- Console events: `{json.dumps(result.get('console_events', []), ensure_ascii=True)}`",
        f"- Interesting console events: `{json.dumps(result.get('interesting_console_events', []), ensure_ascii=True)}`",
        f"- Matching diagnostic entries: `{json.dumps(result.get('matching_diagnostic_entries', []), ensure_ascii=True)}`",
        f"- Page errors: `{json.dumps(result.get('page_errors', []), ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _write_review_replies(result: dict[str, Any], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(result=result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}, indent=2) + "\n",
        encoding="utf-8",
    )


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("resolved") is False
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(result: dict[str, Any], *, passed: bool) -> str:
    error_summary = str(result.get("error", "unknown error")).splitlines()[0]
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{error_summary}`."
    )
    return (
        "Fixed: the active hosted workspace now computes the hosted workspace id and "
        "passes it through `workspace_token_profile_ids=(hosted_workspace_id,)`, so "
        "startup exercises the authenticated hosted `/user` probe path instead of "
        "stalling in `Needs sign-in`. The test still keeps the authoritative "
        "`shell_ready` timing gate and now reads same-run startup diagnostics from "
        "in-page plus Playwright console capture. "
        f"{rerun_summary}"
    )


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "After the delayed GitHub `/user` auth probe started, the live shell reached "
            "`shell_ready` at approximately the 11-second timeout boundary and the browser "
            "console contained a diagnostic entry that linked the probe start to that "
            "transition with the expected delta."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not expose the expected startup diagnostic entry.",
        ),
    )


if __name__ == "__main__":
    main()
