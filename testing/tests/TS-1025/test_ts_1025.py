from __future__ import annotations

import json
import platform
import re
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
    relative_event_seconds,
    relative_startup_event_seconds,
    safe_trigger_payload,
    snippet,
    startup_surface_payload,
    write_test_automation_result,
)
from testing.tests.support.ts1025_startup_diagnostic_runtime import (  # noqa: E402
    Ts1025StartupDiagnosticRuntime,
)

TICKET_KEY = "TS-1025"
TEST_CASE_TITLE = (
    "Startup diagnostics — logs capture timing delta for authentication probe fallback"
)
TEST_FILE_PATH = "testing/tests/TS-1025/test_ts_1025.py"
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
AUTH_PROBE_START_WAIT_SECONDS = 60
TIMEOUT_ASSERTION_SECONDS = 11.0
TIMEOUT_RENDER_GRACE_SECONDS = 1.5
OBSERVATION_TIMEOUT_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + 15
POLL_INTERVAL_SECONDS = 0.15
DIAGNOSTIC_DELTA_MIN_SECONDS = 10.0
DIAGNOSTIC_DELTA_MAX_SECONDS = 13.5
LINKED_BUGS = ("TS-1029", "TS-1027", "TS-1022")
LINKED_BUG_NOTES = (
    "Reviewed TS-1029, TS-1027, and TS-1022. Their fixes require the delayed GitHub "
    "`/user` startup probe to begin during startup, keep auth pending for long enough "
    "to observe the 11-second fallback, and then emit a same-run startup diagnostic "
    "entry that ties the auth-probe start to the `shell_ready` timeout transition."
)

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Wait for the 11-second synchronization timeout to expire and the UI shell to render (shell_ready=true).",
    "Access the application logs (e.g., via browser console or telemetry dashboard).",
    "Inspect the entries recorded during the initialization sequence.",
]
EXPECTED_RESULT = (
    "The logs contain a diagnostic entry that explicitly captures the initiation of the "
    "auth probe and the shell state transition, including a calculated delta of "
    "approximately 11 seconds."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1025_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1025_failure.png"

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
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts1025StartupDiagnosticRuntime(
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
        "linked_bugs": list(LINKED_BUGS),
        "linked_bug_notes": LINKED_BUG_NOTES,
        "sync_timeout_seconds": SYNC_TIMEOUT_SECONDS,
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "product_failure": False,
        "steps": [],
        "human_verification": [],
    }

    tracker_page: TrackStateTrackerPage | None = None
    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            switcher_page = LiveWorkspaceSwitcherPage(tracker_page)
            session.set_viewport_size(
                width=DESKTOP_VIEWPORT["width"],
                height=DESKTOP_VIEWPORT["height"],
            )
            startup_started_at_monotonic = time.monotonic()
            tracker_page.open_entrypoint()
            switcher_page.set_viewport(**DESKTOP_VIEWPORT)
            result["startup_observation_initial"] = _startup_surface_payload(tracker_page)

            auth_probe_started = runtime.wait_for_auth_probe_start(
                timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
            )
            result["github_request_urls"] = list(runtime.github_request_urls)
            result["delayed_request_urls"] = list(runtime.delayed_request_urls)

            if not auth_probe_started or runtime.auth_probe_started_at_monotonic is None:
                startup_surface = _startup_surface_payload(tracker_page)
                trigger = _safe_trigger_payload(switcher_page)
                diagnostic_state = _safe_read_diagnostic_state(runtime)
                result["startup_observation_missing_probe"] = startup_surface
                result["trigger_observation"] = trigger
                result["diagnostic_state"] = diagnostic_state
                result["interesting_diagnostic_entries"] = _interesting_diagnostic_entries(
                    diagnostic_state,
                )
                result["diagnostic_delta_seconds"] = _parse_diagnostic_delta_seconds(
                    result["interesting_diagnostic_entries"],
                )
                result["product_failure"] = True
                step_one_error = _missing_probe_error(
                    result=result,
                    startup_surface=startup_surface,
                    trigger=trigger,
                    body_text=tracker_page.body_text(),
                    diagnostic_entries=result["interesting_diagnostic_entries"],
                )
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
                        "Viewed the live startup shell like a user and checked whether the "
                        "current production build ever issued the delayed GitHub `/user` "
                        "startup auth probe needed for the timeout fallback."
                    ),
                    observed=(
                        f"github_request_urls={json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}; "
                        f"delayed_request_urls={json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}; "
                        f"trigger={json.dumps(trigger, ensure_ascii=True) if trigger else 'null'}; "
                        f"body_excerpt={snippet(tracker_page.body_text())!r}; "
                        f"matching_diagnostic_entries="
                        f"{json.dumps(result.get('interesting_diagnostic_entries', [])[:3], ensure_ascii=True)}"
                    ),
                )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                record_not_reached_steps(
                    result,
                    starting_step=2,
                    request_steps=REQUEST_STEPS,
                )
                raise AssertionError(f"Step 1 failed: {step_one_error}")

            auth_probe_started_after_start_seconds = relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.auth_probe_started_at_monotonic,
            )
            result["auth_probe_started_after_start_seconds"] = (
                auth_probe_started_after_start_seconds
            )
            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app in Chromium with a stored GitHub "
                    "token, preloaded hosted active workspace plus local fallback "
                    "workspace profile, and an injected "
                    f"{SIMULATED_PROBE_DELAY_SECONDS}-second delay on the GitHub `/user` "
                    "startup auth probe.\n"
                    f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
                    f"delayed_request_urls={result['delayed_request_urls']!r}"
                ),
            )

            transition_tracker = ShellReadyTransitionTracker()
            timeout_elapsed, timeout_window = poll_until(
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
            timeout_shell_ready, timeout_ready_window = poll_until(
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
                    and bool(observation["auth_pending"])
                    and bool(observation["shell_observation"]["shell_ready"])
                ),
                timeout_seconds=TIMEOUT_RENDER_GRACE_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            timeout_assertion_window = (
                timeout_ready_window if timeout_shell_ready else timeout_window
            )
            result["timeout_window_observation"] = timeout_assertion_window
            result["authoritative_shell_ready_after_start_seconds"] = (
                timeout_assertion_window.get("authoritative_shell_ready_after_start_seconds")
            )
            result["authoritative_shell_ready_after_auth_start_seconds"] = (
                timeout_assertion_window.get(
                    "authoritative_shell_ready_after_auth_start_seconds",
                )
            )

            step_two_error = _step_two_error(timeout_assertion_window)
            if step_two_error is not None:
                diagnostic_state = _safe_read_diagnostic_state(runtime)
                result["diagnostic_state"] = diagnostic_state
                result["interesting_diagnostic_entries"] = _interesting_diagnostic_entries(
                    diagnostic_state,
                )
                result["diagnostic_delta_seconds"] = _parse_diagnostic_delta_seconds(
                    result["interesting_diagnostic_entries"],
                )
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
                        "Viewed the live shell after the delayed auth probe began and compared "
                        "the visible shell state to the expected 11-second timeout fallback."
                    ),
                    observed=(
                        f"timeout_window={json.dumps(timeout_assertion_window, ensure_ascii=True)}; "
                        f"body_excerpt={snippet(timeout_assertion_window['shell_observation']['body_text'])!r}; "
                        f"delayed_request_urls={json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}"
                    ),
                )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                record_not_reached_steps(
                    result,
                    starting_step=3,
                    request_steps=REQUEST_STEPS,
                )
                raise AssertionError(f"Step 2 failed: {step_two_error}")

            record_step(
                result,
                step=2,
                status="passed",
                action=REQUEST_STEPS[1],
                observed=(
                    "Waited beyond the 11-second startup timeout while the delayed GitHub "
                    "`/user` probe was still pending, and the live app exposed the shell "
                    "during that timeout window.\n"
                    f"elapsed_since_auth_start_seconds={timeout_assertion_window['elapsed_since_auth_start_seconds']!r}; "
                    f"authoritative_shell_ready_after_auth_start_seconds="
                    f"{timeout_assertion_window['authoritative_shell_ready_after_auth_start_seconds']!r}; "
                    f"trigger={json.dumps(timeout_assertion_window['trigger'], ensure_ascii=True)}"
                ),
            )

            diagnostic_state = runtime.read_startup_diagnostic_state()
            interesting_entries = _interesting_diagnostic_entries(diagnostic_state)
            result["diagnostic_state"] = diagnostic_state
            result["interesting_diagnostic_entries"] = interesting_entries
            record_step(
                result,
                step=3,
                status="passed",
                action=REQUEST_STEPS[2],
                observed=(
                    "Captured the same-run startup console evidence from the live browser "
                    "session used for the delayed-probe scenario.\n"
                    f"in_page_console_event_count="
                    f"{len(diagnostic_state.get('in_page_console_events', []))}; "
                    f"playwright_console_message_count="
                    f"{len(diagnostic_state.get('playwright_console_messages', []))}; "
                    f"interesting_entry_count={len(interesting_entries)}"
                ),
            )

            diagnostic_delta_seconds = _parse_diagnostic_delta_seconds(interesting_entries)
            result["diagnostic_delta_seconds"] = diagnostic_delta_seconds
            step_four_error = _step_four_error(
                entries=interesting_entries,
                diagnostic_delta_seconds=diagnostic_delta_seconds,
            )
            if step_four_error is not None:
                result["product_failure"] = True
                record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=step_four_error,
                )
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise AssertionError(f"Step 4 failed: {step_four_error}")

            record_step(
                result,
                step=4,
                status="passed",
                action=REQUEST_STEPS[3],
                observed=(
                    "The live startup diagnostics included an entry that tied the delayed "
                    "GitHub `/user` auth probe to the `shell_ready` timeout transition.\n"
                    f"diagnostic_delta_seconds={diagnostic_delta_seconds!r}; "
                    f"matching_entry={interesting_entries[0]!r}"
                ),
            )

            record_human_verification(
                result,
                check=(
                    "Viewed the rendered startup shell the way a user would and confirmed the "
                    "page became interactive with visible TrackState branding and navigation "
                    "after the timeout-path shell render."
                ),
                observed=(
                    f"body_excerpt={snippet(timeout_assertion_window['shell_observation']['body_text'])!r}; "
                    f"visible_navigation_labels="
                    f"{timeout_assertion_window['shell_observation']['visible_navigation_labels']!r}; "
                    f"branding_visible={timeout_assertion_window['branding_visible']!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Opened the same live run's browser-console evidence and inspected the "
                    "startup diagnostic entries a human tester would review in DevTools."
                ),
                observed=(
                    f"interesting_console_event_count={len(interesting_entries)}; "
                    f"diagnostic_delta_seconds={diagnostic_delta_seconds!r}; "
                    f"matching_entries={json.dumps(interesting_entries[:5], ensure_ascii=True)}"
                ),
            )

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


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    return startup_surface_payload(tracker_page)


def _observe_timeout_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts1025StartupDiagnosticRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
) -> dict[str, Any]:
    shell_window = observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
        transition_tracker=transition_tracker,
    )
    shell_window["shell_probe_state"] = runtime.read_shell_probe_state()
    shell_window["elapsed_since_start_seconds"] = round(
        time.monotonic() - startup_started_at_monotonic,
        2,
    )
    authoritative_shell_ready_at_monotonic = (
        transition_tracker.first_shell_ready_after_auth_pending_at_monotonic
    )
    shell_window["authoritative_shell_ready_after_start_seconds"] = (
        relative_startup_event_seconds(
            startup_started_at_monotonic,
            authoritative_shell_ready_at_monotonic,
        )
    )
    shell_window["authoritative_shell_ready_after_auth_start_seconds"] = (
        relative_event_seconds(
            runtime.auth_probe_started_at_monotonic,
            authoritative_shell_ready_at_monotonic,
        )
    )
    return shell_window


def _missing_probe_error(
    *,
    result: dict[str, Any],
    startup_surface: dict[str, Any],
    trigger: dict[str, Any] | None,
    body_text: str,
    diagnostic_entries: list[str],
) -> str:
    diagnostic_suffix = ""
    if diagnostic_entries:
        diagnostic_suffix = (
            "\nSame-run startup diagnostics still reported:\n"
            f"{json.dumps(diagnostic_entries, indent=2)}"
        )
    if result.get("delayed_request_urls"):
        return (
            "The delayed GitHub `/user` request was observed, but it did not begin during "
            "the expected startup observation window for this scenario.\n"
            f"Observed delayed requests:\n{json.dumps(result['delayed_request_urls'], indent=2)}\n"
            f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}\n"
            f"Observed trigger:\n{json.dumps(trigger, indent=2) if trigger else 'null'}\n"
            f"Observed body text:\n{body_text}"
            f"{diagnostic_suffix}"
        )
    if result.get("github_request_urls"):
        return (
            "The deployed app never issued the required GitHub `/user` startup auth probe. "
            "Startup only requested other GitHub endpoints, so the TS-1025 delayed-auth "
            "diagnostic scenario could not be exercised on the live product.\n"
            f"Observed GitHub requests:\n{json.dumps(result['github_request_urls'], indent=2)}\n"
            f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}\n"
            f"Observed trigger:\n{json.dumps(trigger, indent=2) if trigger else 'null'}\n"
            f"Observed body text:\n{body_text}"
            f"{diagnostic_suffix}"
        )
    return (
        "The deployed app never started the delayed GitHub `/user` startup auth probe "
        "within the observation window, so the timeout-fallback diagnostic scenario could "
        "not be observed.\n"
        f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}\n"
        f"Observed trigger:\n{json.dumps(trigger, indent=2) if trigger else 'null'}\n"
        f"Observed body text:\n{body_text}"
        f"{diagnostic_suffix}"
    )


def _step_two_error(timeout_window: dict[str, Any]) -> str | None:
    if timeout_window["elapsed_since_auth_start_seconds"] is None:
        return (
            "The test never reached the post-timeout observation window while watching the "
            "delayed GitHub `/user` probe.\n"
            f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
        )
    if not bool(timeout_window["auth_pending"]):
        shell_ready_after_start_seconds = timeout_window.get(
            "authoritative_shell_ready_after_start_seconds",
        )
        auth_probe_released_after_start_seconds = timeout_window.get(
            "auth_probe_released_after_start_seconds",
        )
        if (
            isinstance(shell_ready_after_start_seconds, (int, float))
            and isinstance(auth_probe_released_after_start_seconds, (int, float))
            and shell_ready_after_start_seconds >= auth_probe_released_after_start_seconds
        ):
            return (
                "The delayed GitHub `/user` probe started, but the app did not expose the "
                "`shell_ready` timeout fallback while auth was still pending. The shell was "
                "only observed after the delayed auth probe had already been released.\n"
                f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
            )
        return (
            "By the time the 11-second timeout assertion ran, the delayed GitHub `/user` "
            "probe was no longer pending, so the live timeout fallback window was not "
            "observed.\n"
            f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
        )
    if not bool(timeout_window["shell_observation"]["shell_ready"]):
        return (
            "After waiting beyond the 11-second startup timeout, the live page still had "
            "not reached `shell_ready` while the delayed auth probe remained pending.\n"
            f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
        )
    authoritative_delta_seconds = timeout_window.get(
        "authoritative_shell_ready_after_auth_start_seconds",
    )
    if authoritative_delta_seconds is None:
        return (
            "The live page became interactive, but the test could not capture an "
            "authoritative `shell_ready` observation after the delayed auth probe was "
            "already pending.\n"
            f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
        )
    if not DIAGNOSTIC_DELTA_MIN_SECONDS <= float(authoritative_delta_seconds) <= DIAGNOSTIC_DELTA_MAX_SECONDS:
        return (
            "The live app exposed `shell_ready`, but not on the expected 11-second timeout "
            "fallback cadence after the delayed auth probe started.\n"
            f"authoritative_shell_ready_after_auth_start_seconds={authoritative_delta_seconds!r}\n"
            f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
        )
    return None


def _safe_read_diagnostic_state(
    runtime: Ts1025StartupDiagnosticRuntime,
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


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any] | None:
    return safe_trigger_payload(page)


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
        if not any(all(keyword in lowered for keyword in group) for group in _DIAGNOSTIC_KEYWORD_GROUPS):
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        filtered.append(normalized)
    return filtered


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
            "The live browser-console evidence did not expose any application-specific "
            "startup diagnostic entry that tied the delayed GitHub `/user` auth probe to "
            "the `shell_ready` transition."
        )
    if diagnostic_delta_seconds is None:
        return (
            "The live startup diagnostics mentioned the delayed auth probe or the "
            "`shell_ready` transition, but none of the entries exposed a parseable timing "
            "delta.\n"
            f"Observed diagnostic entries:\n{json.dumps(entries, indent=2)}"
        )
    if not DIAGNOSTIC_DELTA_MIN_SECONDS <= diagnostic_delta_seconds <= DIAGNOSTIC_DELTA_MAX_SECONDS:
        return (
            "The live startup diagnostics exposed a timing delta, but it was outside the "
            "expected ~11-second timeout window.\n"
            f"diagnostic_delta_seconds={diagnostic_delta_seconds!r}\n"
            f"Observed diagnostic entries:\n{json.dumps(entries, indent=2)}"
        )
    return None


def _write_pass_outputs(result: dict[str, Any]) -> None:
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")
    write_test_automation_result(RESULT_PATH, passed=True)
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _write_failure_outputs(result: dict[str, Any]) -> None:
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    write_test_automation_result(RESULT_PATH, passed=False, error=str(result.get("error", "")))
    if _should_write_bug_description(result):
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if passed else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"*Environment:* URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport:* {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked Bugs Considered:* {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was automated",
        "* Opened the live deployed TrackState app with a stored GitHub token and preloaded hosted active plus local fallback workspace profiles.",
        f"* Delayed the live GitHub {{/user}} startup probe by {SIMULATED_PROBE_DELAY_SECONDS} seconds and waited beyond the 11-second fallback window before asserting.",
        "* Gated the authoritative {{shell_ready}} timing so it is accepted only after the delayed auth probe is already pending, matching the linked-bug timing requirements.",
        "* Captured same-run browser-console diagnostics from the live session and required an auth-probe-to-{{shell_ready}} delta near 11 seconds.",
        "",
        "h4. Automation checks",
        *format_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *format_human_lines(result, jira=True),
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        _actual_result_summary(result, passed=passed),
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
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked Bugs Considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Opened the live deployed TrackState app with a stored GitHub token and preloaded hosted active plus local fallback workspace profiles.",
        f"- Delayed the live GitHub `/user` startup probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds and waited beyond the required timeout window before asserting.",
        "- Accepted the authoritative `shell_ready` timing only after the delayed auth probe was already pending, so early shell-ready noise does not count as the timeout fallback.",
        "- Captured same-run browser-console diagnostics and required a startup diagnostic entry that ties the delayed auth probe to `shell_ready` with an approximately 11-second delta.",
        "",
        "## Automation checks",
        *format_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *format_human_lines(result, jira=False),
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
    lines = [
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
        f"- Simulated delayed startup probe: GitHub `/user` delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Timeout observation: `{json.dumps(result.get('timeout_window_observation'), ensure_ascii=True)}`",
        f"- Diagnostic state: `{json.dumps(result.get('diagnostic_state'), ensure_ascii=True)}`",
        f"- Matching diagnostic entries: `{json.dumps(result.get('interesting_diagnostic_entries', []), ensure_ascii=True)}`",
        f"- Diagnostic delta seconds: `{json.dumps(result.get('diagnostic_delta_seconds'), ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "The delayed GitHub `/user` startup probe began during startup, the live app "
            "reached `shell_ready` while auth was still pending after roughly "
            f"{result.get('authoritative_shell_ready_after_auth_start_seconds')!r} seconds "
            "from auth-probe start, and the same-run startup diagnostics reported an "
            f"auth-probe-to-`shell_ready` delta of {result.get('diagnostic_delta_seconds')!r} seconds."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not expose the delayed-auth startup diagnostic expected "
            "for TS-1025.",
        ),
    )


if __name__ == "__main__":
    main()
