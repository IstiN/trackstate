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
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    build_annotated_steps,
    build_workspace_state,
    format_human_lines,
    format_step_lines,
    prepare_local_workspace_repository,
    record_human_verification,
    record_step,
    safe_trigger_payload,
    snippet,
    startup_surface_payload,
    write_test_automation_result,
)
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-1034"
TEST_CASE_TITLE = (
    "Startup state guard — shell transition stays blocked without auth terminal events"
)
TEST_FILE_PATH = "testing/tests/TS-1034/test_ts_1034.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1034/test_ts_1034.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1034-local"
LOCAL_DISPLAY_NAME = "TS-1034 local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
LOADING_TEXT_FRAGMENTS = ("TrackState.AI", "Git-native. Jira-compatible. Team-proven.")
MONITOR_WINDOW_SECONDS = 15.0
MONITOR_INTERVAL_SECONDS = 0.25
AUTH_PROBE_START_WINDOW_SECONDS = 15.0
MIN_MONITOR_SAMPLES = 10
LINKED_BUGS = ("TS-1029",)
LINKED_BUG_NOTES = (
    "Reviewed TS-1029. Its deployed fix restored the live startup auth-probe path, so "
    "this regression waits through a full 15-second observation window after launch and "
    "does not assert immediately."
)
REQUEST_STEPS = [
    "Mock the AuthenticationService to suppress all resolution and timeout signals (simulating a logic failure or hang without event emission).",
    "Launch the TrackState application.",
    "Monitor the application state and UI for 15 seconds (exceeding the standard 11s timeout).",
    "Verify the visibility of interactive shell components (TopBar, Sidebar).",
]
EXPECTED_RESULT = (
    "The application remains on the loading surface and does not transition to "
    "'shell_ready=true'. Interactive components are not rendered, confirming that "
    "the transition is blocked in the absence of a terminal lifecycle event from "
    "the auth service."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
INITIAL_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1034_initial.png"
FINAL_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1034_final.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1034_failure.png"


class Ts1034StartupGuardRuntime(StoredWorkspaceProfilesRuntime):
    def __init__(
        self,
        *,
        repository: str,
        token: str,
        workspace_state: dict[str, object],
        workspace_token_profile_ids: tuple[str, ...] = (),
    ):
        super().__init__(
            repository=repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=workspace_token_profile_ids,
        )
        self.console_events: list[str] = []
        self.page_errors: list[str] = []

    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "Ts1034StartupGuardRuntime expected a browser context and page.",
            )
        script = _startup_guard_script()
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        self._page.on("console", lambda message: self.console_events.append(str(message.text)))
        self._page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        return session

    def read_guard_state(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError(
                "Ts1034StartupGuardRuntime expected a browser page before reading state.",
            )
        payload = self._page.evaluate(
            """
            () => {
              const state = window.__ts1034StartupGuardState;
              if (!state) {
                return null;
              }
              return {
                authProbeRequests: state.authProbeRequests,
                suppressedTimeouts: state.suppressedTimeouts,
                firstNavigationVisibleAtMs: state.firstNavigationVisibleAtMs,
                firstTriggerVisibleAtMs: state.firstTriggerVisibleAtMs,
                firstShellReadyObservedAtMs: state.firstShellReadyObservedAtMs,
                firstLoadingSurfaceObservedAtMs: state.firstLoadingSurfaceObservedAtMs,
                samples: state.samples,
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            return {
                "auth_probe_request_count": 0,
                "completed_auth_probe_request_count": 0,
                "auth_probe_pending": False,
                "first_user_probe_started_after_launch_seconds": None,
                "suppressed_timeout_count": 0,
                "suppressed_timeouts": [],
                "first_navigation_visible_after_launch_seconds": None,
                "first_trigger_visible_after_launch_seconds": None,
                "first_shell_ready_after_launch_seconds": None,
                "first_loading_surface_after_launch_seconds": None,
                "sample_count": 0,
                "latest_sample_after_launch_seconds": None,
                "latest_sample": {},
                "samples": [],
            }

        auth_probe_requests = payload.get("authProbeRequests", [])
        suppressed_timeouts = payload.get("suppressedTimeouts", [])
        samples = payload.get("samples", [])
        normalized_samples = _normalize_guard_samples(samples)
        first_started = _first_started_after_launch_seconds(auth_probe_requests)
        completed_count = _completed_auth_probe_request_count(auth_probe_requests)
        return {
            "auth_probe_request_count": _safe_len(auth_probe_requests),
            "completed_auth_probe_request_count": completed_count,
            "auth_probe_pending": bool(first_started is not None and completed_count == 0),
            "first_user_probe_started_after_launch_seconds": first_started,
            "suppressed_timeout_count": _safe_len(suppressed_timeouts),
            "suppressed_timeouts": _normalize_suppressed_timeouts(suppressed_timeouts),
            "first_navigation_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstNavigationVisibleAtMs"),
            ),
            "first_trigger_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstTriggerVisibleAtMs"),
            ),
            "first_shell_ready_after_launch_seconds": _ms_to_seconds(
                payload.get("firstShellReadyObservedAtMs"),
            ),
            "first_loading_surface_after_launch_seconds": _ms_to_seconds(
                payload.get("firstLoadingSurfaceObservedAtMs"),
            ),
            "sample_count": len(normalized_samples),
            "latest_sample_after_launch_seconds": (
                normalized_samples[-1]["observed_after_launch_seconds"]
                if normalized_samples
                else None
            ),
            "latest_sample": normalized_samples[-1] if normalized_samples else {},
            "samples": normalized_samples,
        }


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    INITIAL_SCREENSHOT_PATH.unlink(missing_ok=True)
    FINAL_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1034 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    hosted_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
    runtime = Ts1034StartupGuardRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
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
        "monitor_window_seconds": MONITOR_WINDOW_SECONDS,
        "linked_bugs": list(LINKED_BUGS),
        "linked_bug_notes": LINKED_BUG_NOTES,
        "hosted_workspace_id": hosted_workspace_id,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "steps": [],
        "human_verification": [],
    }

    tracker_page: TrackStateTrackerPage | None = None
    try:
        with runtime as session:
            tracker_page = TrackStateTrackerPage(session, config.app_url)
            switcher_page = LiveWorkspaceSwitcherPage(tracker_page)
            switcher_page.set_viewport(**DESKTOP_VIEWPORT)

            startup_started_at_monotonic = time.monotonic()
            switcher_page.open_startup_entrypoint(wait_until="commit", timeout_ms=120_000)

            startup_surface = _startup_surface_payload(tracker_page)
            result["startup_surface_after_render"] = startup_surface
            tracker_page.screenshot(str(INITIAL_SCREENSHOT_PATH))
            result["initial_screenshot"] = str(INITIAL_SCREENSHOT_PATH)

            monitor_samples = _collect_monitor_samples(
                tracker_page=tracker_page,
                switcher_page=switcher_page,
                runtime=runtime,
                startup_started_at_monotonic=startup_started_at_monotonic,
            )
            guard_state = runtime.read_guard_state()
            result["guard_state"] = guard_state
            result["monitor_samples"] = [_sample_payload(sample) for sample in monitor_samples]
            result["monitor_sample_count"] = len(monitor_samples)
            result["monitored_duration_seconds"] = (
                monitor_samples[-1]["elapsed_since_start_seconds"] if monitor_samples else None
            )
            result["console_events"] = list(runtime.console_events)
            result["page_errors"] = list(runtime.page_errors)
            startup_surface_visible_during_window = bool(
                _looks_like_loading_surface(startup_surface)
                or any(sample.get("loading_surface_visible") for sample in monitor_samples)
            )

            step_failures: list[str] = []

            step1_failures = _startup_guard_failures(guard_state)
            if step1_failures:
                observed = "\n".join(step1_failures)
                record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=observed,
                )
                step_failures.append(f"Step 1 failed: {observed}")
            else:
                record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Injected a browser-side startup guard that kept the GitHub `/user` "
                        "auth probe unresolved and suppressed the ~10-second startup timeout "
                        "callback.\n"
                        f"guard_state={json.dumps(_guard_state_summary(guard_state), indent=2)}"
                    ),
                )

            step2_failures = _startup_surface_failures(
                startup_surface_visible_during_window=startup_surface_visible_during_window,
                startup_surface=startup_surface,
            )
            if step2_failures:
                observed = "\n".join(step2_failures)
                record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=observed,
                )
                step_failures.append(f"Step 2 failed: {observed}")
            else:
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Opened the deployed TrackState app and reached the visible loading "
                        "surface in Chromium.\n"
                        f"startup_surface={json.dumps(_startup_surface_summary(startup_surface), indent=2)}"
                    ),
                )

            step3_failures = _monitor_window_failures(monitor_samples)
            if step3_failures:
                observed = "\n".join(step3_failures)
                record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=observed,
                )
                step_failures.append(f"Step 3 failed: {observed}")
            else:
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Sampled the live startup surface across the full 15-second window "
                        "before asserting the result.\n"
                        f"sample_count={len(monitor_samples)!r}; "
                        f"monitored_duration_seconds={result['monitored_duration_seconds']!r}"
                    ),
                )

            step4_failures = _visibility_guard_failures(
                monitor_samples=monitor_samples,
                guard_state=guard_state,
            )
            if step4_failures:
                observed = "\n".join(step4_failures)
                record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=observed,
                )
                step_failures.append(f"Step 4 failed: {observed}")
            else:
                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "Across the monitored window, the TopBar workspace switcher trigger "
                        "and sidebar navigation labels never became visible, and the page "
                        "never reached `shell_ready=true`.\n"
                        f"guard_state={json.dumps(_guard_state_summary(guard_state), indent=2)}"
                    ),
                )

            final_sample = monitor_samples[-1] if monitor_samples else {}
            record_human_verification(
                result,
                check=(
                    "Viewed the live startup page like a user and confirmed the loading "
                    "surface remained visible with TrackState branding."
                ),
                observed=(
                    f"title={startup_surface.get('title')!r}; "
                    f"body_excerpt={snippet(str(final_sample.get('startup_body_text', '')))!r}; "
                    f"initial_screenshot={str(INITIAL_SCREENSHOT_PATH)!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Watched the page for the full 15-second window and verified that no "
                    "Dashboard, Board, JQL Search, Hierarchy, Settings, or workspace "
                    "switcher trigger became visible."
                ),
                observed=(
                    f"final_sample={json.dumps(_sample_payload(final_sample), ensure_ascii=True)}; "
                    f"final_screenshot={str(FINAL_SCREENSHOT_PATH)!r}"
                ),
            )

            tracker_page.screenshot(str(FINAL_SCREENSHOT_PATH))
            result["screenshot"] = str(FINAL_SCREENSHOT_PATH)

            if step_failures:
                raise AssertionError("\n\n".join(step_failures))

            _write_pass_outputs(result)
            print(f"{TICKET_KEY} passed")
            return
    except AssertionError as error:
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        if tracker_page is not None:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _write_failure_outputs(result, product_bug=_should_write_bug_description(result))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        if tracker_page is not None:
            try:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:  # pragma: no cover - diagnostics only
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _write_failure_outputs(result, product_bug=False)
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
        marker_filename=".trackstate-ts1034-precondition.txt",
        marker_contents="Prepared for TS-1034 startup guard validation.\n",
        commit_author_name="TS-1034 Automation",
        commit_author_email="ts1034@example.com",
        commit_message="Prepare TS-1034 local workspace",
    )


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    observation = startup_surface_payload(tracker_page)
    return {
        "title": observation["title"],
        "location_href": observation["location_href"],
        "location_hash": observation["location_hash"],
        "location_pathname": observation["location_pathname"],
        "body_text": observation["body_text"],
        "button_labels": list(observation["button_labels"]),
    }


def _collect_monitor_samples(
    *,
    tracker_page: TrackStateTrackerPage,
    switcher_page: LiveWorkspaceSwitcherPage,
    runtime: Ts1034StartupGuardRuntime,
    startup_started_at_monotonic: float,
) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    deadline = startup_started_at_monotonic + MONITOR_WINDOW_SECONDS
    while True:
        samples.append(
            _observe_monitor_window(
                tracker_page=tracker_page,
                switcher_page=switcher_page,
                runtime=runtime,
                startup_started_at_monotonic=startup_started_at_monotonic,
            ),
        )
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        time.sleep(min(MONITOR_INTERVAL_SECONDS, remaining))
    return samples


def _startup_surface_summary(startup_surface: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": startup_surface.get("title"),
        "location_pathname": startup_surface.get("location_pathname"),
        "button_labels": list(startup_surface.get("button_labels", [])),
        "body_excerpt": snippet(str(startup_surface.get("body_text", ""))),
    }


def _observe_monitor_window(
    *,
    tracker_page: TrackStateTrackerPage,
    switcher_page: LiveWorkspaceSwitcherPage,
    runtime: Ts1034StartupGuardRuntime,
    startup_started_at_monotonic: float,
) -> dict[str, Any]:
    guard_state = runtime.read_guard_state()
    latest_guard_sample = guard_state.get("latest_sample", {})
    startup_observation = _startup_surface_payload(tracker_page)
    shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
        timeout_ms=250,
    )
    trigger = safe_trigger_payload(switcher_page, timeout_ms=250)
    return {
        "elapsed_since_start_seconds": round(
            time.monotonic() - startup_started_at_monotonic,
            2,
        ),
        "startup_observation": startup_observation,
        "shell_observation": shell_observation,
        "trigger": trigger,
        "guard_state": _guard_state_summary(guard_state),
        "startup_body_text": str(startup_observation.get("body_text", "")),
        "shell_body_text": str(shell_observation.get("body_text", "")),
        "loading_surface_visible": bool(latest_guard_sample.get("loading_surface_visible"))
        or _looks_like_loading_surface(startup_observation),
        "visible_navigation_labels": list(shell_observation.get("visible_navigation_labels", [])),
        "shell_ready": bool(shell_observation.get("shell_ready")),
    }


def _startup_guard_failures(guard_state: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not isinstance(guard_state.get("first_user_probe_started_after_launch_seconds"), (int, float)):
        failures.append(
            "The live app never attempted the GitHub `/user` startup auth probe within the "
            "15-second observation window.\n"
            f"guard_state={json.dumps(_guard_state_summary(guard_state), indent=2)}"
        )
    if int(guard_state.get("suppressed_timeout_count", 0)) < 1:
        failures.append(
            "The startup guard did not observe and suppress the ~10-second startup timeout "
            "callback, so the no-timeout-event condition was not established.\n"
            f"guard_state={json.dumps(_guard_state_summary(guard_state), indent=2)}"
        )
    if int(guard_state.get("completed_auth_probe_request_count", 0)) != 0:
        failures.append(
            "The intercepted GitHub `/user` startup probe unexpectedly completed instead of "
            "remaining unresolved.\n"
            f"guard_state={json.dumps(_guard_state_summary(guard_state), indent=2)}"
        )
    if not bool(guard_state.get("auth_probe_pending")):
        failures.append(
            "The intercepted GitHub `/user` startup probe was not still pending at the end of "
            "the monitored window.\n"
            f"guard_state={json.dumps(_guard_state_summary(guard_state), indent=2)}"
        )
    return failures


def _startup_surface_failures(
    *,
    startup_surface_visible_during_window: bool,
    startup_surface: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if not startup_surface_visible_during_window:
        failures.append(
            "The deployed app never exposed the expected loading surface during the monitored "
            "startup window.\n"
            f"startup_surface={json.dumps(startup_surface, indent=2)}"
        )
    return failures


def _monitor_window_failures(monitor_samples: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    if len(monitor_samples) < MIN_MONITOR_SAMPLES:
        failures.append(
            f"Only {len(monitor_samples)} startup samples were collected; at least "
            f"{MIN_MONITOR_SAMPLES} samples were expected over the 15-second window."
        )
    if not monitor_samples:
        failures.append("No startup samples were collected during the monitoring window.")
        return failures
    monitored_duration = monitor_samples[-1].get("elapsed_since_start_seconds")
    if not isinstance(monitored_duration, (int, float)) or monitored_duration < 14.75:
        failures.append(
            "The monitored startup window ended too early and did not cover the requested "
            "15-second observation period.\n"
            f"monitored_duration_seconds={monitored_duration!r}"
        )
    return failures


def _visibility_guard_failures(
    *,
    monitor_samples: list[dict[str, Any]],
    guard_state: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    first_shell_ready = next((sample for sample in monitor_samples if sample["shell_ready"]), None)
    if first_shell_ready is not None:
        failures.append(
            "The page reached `shell_ready=true` even though the auth probe never resolved "
            "and the startup timeout callback was suppressed.\n"
            f"Observed sample:\n{json.dumps(_sample_payload(first_shell_ready), indent=2)}"
        )
    first_navigation = next(
        (sample for sample in monitor_samples if sample["visible_navigation_labels"]),
        None,
    )
    if first_navigation is not None:
        failures.append(
            "Sidebar navigation labels became visible during the blocked startup window.\n"
            f"Observed sample:\n{json.dumps(_sample_payload(first_navigation), indent=2)}"
        )
    first_trigger = next((sample for sample in monitor_samples if sample["trigger"] is not None), None)
    if first_trigger is not None:
        failures.append(
            "The TopBar workspace switcher trigger became visible during the blocked startup "
            "window.\n"
            f"Observed sample:\n{json.dumps(_sample_payload(first_trigger), indent=2)}"
        )
    final_sample = monitor_samples[-1] if monitor_samples else {}
    if not bool(final_sample.get("loading_surface_visible")):
        failures.append(
            "After 15 seconds, the page no longer looked like the loading surface.\n"
            f"Observed sample:\n{json.dumps(_sample_payload(final_sample), indent=2)}"
        )
    for label, timestamp in (
        ("navigation", guard_state.get("first_navigation_visible_after_launch_seconds")),
        ("TopBar trigger", guard_state.get("first_trigger_visible_after_launch_seconds")),
        ("shell_ready", guard_state.get("first_shell_ready_after_launch_seconds")),
    ):
        if isinstance(timestamp, (int, float)) and timestamp <= MONITOR_WINDOW_SECONDS:
            failures.append(
                f"The page-side startup guard recorded the first {label} marker at "
                f"{timestamp!r} seconds, inside the blocked 15-second observation window.\n"
                f"guard_state={json.dumps(_guard_state_summary(guard_state), indent=2)}"
            )
    return failures


def _looks_like_loading_surface(startup_surface: dict[str, Any]) -> bool:
    text = " ".join(
        [
            str(startup_surface.get("title", "")),
            str(startup_surface.get("body_text", "")),
        ],
    )
    return any(fragment in text for fragment in LOADING_TEXT_FRAGMENTS)


def _sample_payload(sample: dict[str, Any]) -> dict[str, Any]:
    startup_observation = sample.get("startup_observation", {})
    shell_observation = sample.get("shell_observation", {})
    trigger = sample.get("trigger")
    return {
        "elapsed_since_start_seconds": sample.get("elapsed_since_start_seconds"),
        "loading_surface_visible": sample.get("loading_surface_visible"),
        "title": startup_observation.get("title"),
        "button_labels": list(startup_observation.get("button_labels", [])),
        "visible_navigation_labels": list(shell_observation.get("visible_navigation_labels", [])),
        "shell_ready": shell_observation.get("shell_ready"),
        "trigger": trigger,
        "startup_body_excerpt": snippet(str(sample.get("startup_body_text", ""))),
        "shell_body_excerpt": snippet(str(sample.get("shell_body_text", ""))),
        "guard_state": sample.get("guard_state"),
    }


def _guard_state_summary(guard_state: dict[str, Any]) -> dict[str, Any]:
    return {
        "auth_probe_request_count": guard_state.get("auth_probe_request_count"),
        "completed_auth_probe_request_count": guard_state.get(
            "completed_auth_probe_request_count",
        ),
        "auth_probe_pending": guard_state.get("auth_probe_pending"),
        "first_user_probe_started_after_launch_seconds": guard_state.get(
            "first_user_probe_started_after_launch_seconds",
        ),
        "suppressed_timeout_count": guard_state.get("suppressed_timeout_count"),
        "suppressed_timeouts": guard_state.get("suppressed_timeouts"),
        "first_navigation_visible_after_launch_seconds": guard_state.get(
            "first_navigation_visible_after_launch_seconds",
        ),
        "first_trigger_visible_after_launch_seconds": guard_state.get(
            "first_trigger_visible_after_launch_seconds",
        ),
        "first_shell_ready_after_launch_seconds": guard_state.get(
            "first_shell_ready_after_launch_seconds",
        ),
        "first_loading_surface_after_launch_seconds": guard_state.get(
            "first_loading_surface_after_launch_seconds",
        ),
        "sample_count": guard_state.get("sample_count"),
        "latest_sample_after_launch_seconds": guard_state.get(
            "latest_sample_after_launch_seconds",
        ),
        "latest_sample": guard_state.get("latest_sample"),
    }


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
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status_icon} {status_word}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        f"*Environment:* URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport:* {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked Bugs Considered:* {', '.join(LINKED_BUGS)}",
        "",
        "h4. What was tested",
        "* Opened the live deployed TrackState app with stored workspace state and GitHub authentication.",
        "* Injected a browser-side guard that hung the GitHub {/user} startup auth probe and suppressed the ~10-second startup timeout callback.",
        "* Watched the page for the full 15-second window before asserting whether the interactive shell became visible.",
        f"* Linked bug review: {LINKED_BUG_NOTES}",
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
    ]
    for key, label in (
        ("initial_screenshot", "*Initial screenshot*"),
        ("screenshot", "*Final screenshot*"),
    ):
        if result.get(key):
            lines.extend(["", f"{label}: {result[key]}"])
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
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked Bugs Considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## What was automated",
        "- Opened the live deployed TrackState app with preloaded workspace state and GitHub auth.",
        "- Injected a browser-side startup guard that kept the GitHub `/user` probe unresolved and suppressed the ~10-second startup timeout callback.",
        "- Observed the loading flow for the full 15-second window and required the interactive shell to stay hidden.",
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
    for key, label in (
        ("initial_screenshot", "Initial screenshot"),
        ("screenshot", "Final screenshot"),
    ):
        if result.get(key):
            lines.extend(["", f"- **{label}:** `{result[key]}`"])
    lines.extend(["", "## Run command", "", "```bash", RUN_COMMAND, "```"])
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Status:** {'passed' if passed else 'failed'}",
        f"**App URL:** `{result.get('app_url')}`",
        "",
        "## Summary",
        _actual_result_summary(result, passed=passed),
        "",
        "## Automation checks",
        *format_step_lines(result, jira=False),
        "",
        "## Real user-style verification",
        *format_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Assertion / error",
                "",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_bug_description(result: dict[str, Any]) -> str:
    lines = [
        f"# Bug Report - {TICKET_KEY}",
        "",
        f"**Summary:** {_actual_result_summary(result, passed=False)}",
        "",
        "## Steps to reproduce",
        *build_annotated_steps(result, request_steps=REQUEST_STEPS),
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Actual result",
        _actual_result_summary(result, passed=False),
        "",
        "## Exact assertion / error",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result.get('app_url')}`",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"- Repository: `{result.get('repository')} @ {result.get('repository_ref')}`",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Observation window: `{MONITOR_WINDOW_SECONDS}` seconds",
        "",
        "## Logs and screenshots",
        f"- Initial screenshot: `{result.get('initial_screenshot')}`",
        f"- Failure screenshot: `{result.get('screenshot')}`",
        "- Guard state:",
        "```json",
        json.dumps(result.get("guard_state", {}), indent=2),
        "```",
        "- Final monitor sample:",
        "```json",
        json.dumps(
            result.get("monitor_samples", [])[-1] if result.get("monitor_samples") else {},
            indent=2,
        ),
        "```",
        "- Console events:",
        "```json",
        json.dumps(result.get("console_events", []), indent=2),
        "```",
        "- Page errors:",
        "```json",
        json.dumps(result.get("page_errors", []), indent=2),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    guard_state = result.get("guard_state", {})
    if passed:
        return (
            "The live deployed app stayed on the loading surface for the full "
            f"{MONITOR_WINDOW_SECONDS:g}-second window while the GitHub `/user` startup probe "
            "remained unresolved and the startup timeout callback stayed suppressed. No "
            "TopBar workspace trigger, sidebar navigation labels, or `shell_ready=true` "
            "transition became visible."
        )
    error = result.get("error", "")
    if error:
        return (
            "The live deployed startup flow did not satisfy the blocked-shell contract "
            f"under missing auth terminal events. guard_state={json.dumps(_guard_state_summary(guard_state), ensure_ascii=True)}; "
            f"error={error}"
        )
    return (
        "The live deployed startup flow did not satisfy the blocked-shell contract "
        f"under missing auth terminal events. guard_state={json.dumps(_guard_state_summary(guard_state), ensure_ascii=True)}"
    )


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    error = str(result.get("error", ""))
    if error.startswith("RuntimeError: TS-1034 requires GH_TOKEN or GITHUB_TOKEN"):
        return False
    if error.startswith("ModuleNotFoundError:"):
        return False
    return True


def _safe_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _ms_to_seconds(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value) / 1000, 2)


def _first_started_after_launch_seconds(requests: Any) -> float | None:
    if not isinstance(requests, list):
        return None
    started_values = [
        _ms_to_seconds(request.get("startedAtMs"))
        for request in requests
        if isinstance(request, dict)
    ]
    filtered = [value for value in started_values if isinstance(value, (int, float))]
    return min(filtered) if filtered else None


def _completed_auth_probe_request_count(requests: Any) -> int:
    if not isinstance(requests, list):
        return 0
    return sum(
        1
        for request in requests
        if isinstance(request, dict) and bool(request.get("completed"))
    )


def _normalize_suppressed_timeouts(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    return [
        {
            "registered_after_launch_seconds": _ms_to_seconds(
                item.get("registeredAtMs") if isinstance(item, dict) else None,
            ),
            "delay_ms": (
                float(item.get("delayMs")) if isinstance(item, dict) and isinstance(item.get("delayMs"), (int, float)) else None
            ),
            "callback_type": (
                str(item.get("callbackType", "")) if isinstance(item, dict) else ""
            ),
        }
        for item in payload
        if isinstance(item, dict)
    ]


def _normalize_guard_samples(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "observed_after_launch_seconds": _ms_to_seconds(item.get("observedAtMs")),
                "loading_surface_visible": bool(item.get("loadingSurfaceVisible")),
                "visible_navigation_labels": [
                    str(label) for label in item.get("visibleNavigationLabels", [])
                ],
                "trigger_visible": bool(item.get("triggerVisible")),
                "trigger_label": str(item.get("triggerLabel", "")),
                "shell_ready": bool(item.get("shellReady")),
                "title": str(item.get("title", "")),
                "button_labels": [str(label) for label in item.get("buttonLabels", [])],
                "body_excerpt": str(item.get("bodyExcerpt", "")),
            },
        )
    return normalized


def _startup_guard_script() -> str:
    return """
(() => {
  if (window.__ts1034StartupGuardState) {
    return;
  }

  const READY_LABELS = ['Dashboard', 'Board', 'JQL Search', 'Hierarchy', 'Settings'];
  const LOADING_TEXTS = ['TrackState.AI', 'Git-native. Jira-compatible. Team-proven.'];
  const MAX_SAMPLES = 400;
  const SAMPLE_INTERVAL_MS = 100;
  const state = {
    authProbeRequests: [],
    suppressedTimeouts: [],
    firstNavigationVisibleAtMs: null,
    firstTriggerVisibleAtMs: null,
    firstShellReadyObservedAtMs: null,
    firstLoadingSurfaceObservedAtMs: null,
    samples: [],
  };
  window.__ts1034StartupGuardState = state;

  const originalFetch = window.fetch.bind(window);
  const originalSetTimeout = window.setTimeout.bind(window);
  const originalClearTimeout = window.clearTimeout.bind(window);
  const fakeTimeoutHandles = new Set();
  let fakeTimeoutHandle = -1;

  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
  const toUrlString = (input) => {
    if (typeof input === 'string') {
      return input;
    }
    if (input && typeof input.url === 'string') {
      return input.url;
    }
    return String(input || '');
  };
  const matchesUserProbe = (url) => {
    try {
      const parsed = new URL(url, window.location.href);
      return parsed.hostname === 'api.github.com'
        && (parsed.pathname.replace(/\\/+$/, '') || '/') === '/user';
    } catch (_) {
      return url.includes('api.github.com') && /\\/user(?:$|[?#])/.test(url);
    }
  };
  const semanticTexts = () => Array.from(
    document.querySelectorAll('flt-semantics, button, [role], nav, header, aside, a, [aria-label]'),
  )
    .filter((element) => !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(element.tagName))
    .map((element) => normalize(
      element.getAttribute?.('aria-label')
      || element.innerText
      || element.textContent
      || '',
    ))
    .filter((text) => text.length > 0);
  const buttonLabels = () => Array.from(
    document.querySelectorAll('button, flt-semantics[role="button"], [role="button"]'),
  )
    .map((element) => normalize(
      element.getAttribute?.('aria-label')
      || element.innerText
      || element.textContent
      || '',
    ))
    .filter((label) => label.length > 0);
  const currentBodyText = () => normalize(
    document.body?.innerText
    || document.body?.textContent
    || '',
  );
  const loadingSurfaceVisible = (bodyText) => LOADING_TEXTS.some((label) => bodyText.includes(label));
  const capture = () => {
    const bodyText = currentBodyText();
    const texts = semanticTexts();
    const triggerLabel = texts.find((text) => text.includes('Workspace switcher:')) || '';
    const visibleNavigationLabels = READY_LABELS.filter(
      (label) => bodyText.includes(label) || texts.includes(label),
    );
    const shellReady = visibleNavigationLabels.length === READY_LABELS.length;
    const loadingVisible = loadingSurfaceVisible(bodyText);
    if (state.firstNavigationVisibleAtMs === null && visibleNavigationLabels.length > 0) {
      state.firstNavigationVisibleAtMs = performance.now();
    }
    if (state.firstTriggerVisibleAtMs === null && triggerLabel) {
      state.firstTriggerVisibleAtMs = performance.now();
    }
    if (state.firstShellReadyObservedAtMs === null && shellReady) {
      state.firstShellReadyObservedAtMs = performance.now();
    }
    if (state.firstLoadingSurfaceObservedAtMs === null && loadingVisible) {
      state.firstLoadingSurfaceObservedAtMs = performance.now();
    }
    state.samples.push({
      observedAtMs: performance.now(),
      loadingSurfaceVisible: loadingVisible,
      visibleNavigationLabels,
      triggerVisible: !!triggerLabel,
      triggerLabel,
      shellReady,
      title: document.title || '',
      buttonLabels: buttonLabels(),
      bodyExcerpt: bodyText.slice(0, 240),
    });
    if (state.samples.length > MAX_SAMPLES) {
      state.samples.splice(0, state.samples.length - MAX_SAMPLES);
    }
  };

  window.fetch = (input, init) => {
    const url = toUrlString(input);
    if (matchesUserProbe(url)) {
      state.authProbeRequests.push({
        url,
        method: normalize(init?.method || input?.method || 'GET'),
        startedAtMs: performance.now(),
        completed: false,
      });
      return new Promise(() => {});
    }
    return originalFetch(input, init);
  };

  window.setTimeout = (callback, delay, ...args) => {
    const numericDelay = Number(delay ?? 0);
    if (Number.isFinite(numericDelay) && numericDelay >= 9500 && numericDelay <= 10500) {
      const handle = fakeTimeoutHandle--;
      fakeTimeoutHandles.add(handle);
      state.suppressedTimeouts.push({
        delayMs: numericDelay,
        registeredAtMs: performance.now(),
        callbackType: typeof callback,
      });
      return handle;
    }
    return originalSetTimeout(callback, delay, ...args);
  };

  window.clearTimeout = (handle) => {
    if (fakeTimeoutHandles.has(handle)) {
      fakeTimeoutHandles.delete(handle);
      return;
    }
    return originalClearTimeout(handle);
  };

  const attachObserver = () => {
    capture();
    if (!document.documentElement) {
      requestAnimationFrame(attachObserver);
      return;
    }
    new MutationObserver(() => capture()).observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
    });
  };

  attachObserver();
  window.setInterval(() => capture(), SAMPLE_INTERVAL_MS);
  window.addEventListener('load', () => capture(), { once: false });
})();
"""


if __name__ == "__main__":
    main()
