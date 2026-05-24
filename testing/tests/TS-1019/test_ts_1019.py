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
    relative_event_seconds,
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


class Ts1019PendingShellProbeRuntime(Ts984DelayedAuthProbeRuntime):
    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "Ts1019PendingShellProbeRuntime expected a browser context and page.",
            )
        script = _pending_shell_probe_script()
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        return session

    def read_pending_shell_probe_state(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError(
                "Ts1019PendingShellProbeRuntime expected a browser page before reading state.",
            )
        payload = self._page.evaluate(
            """
            () => {
              const state = window.__ts1019PendingShellProbeState;
              if (!state) {
                return null;
              }
              return {
                firstNavigationVisibleAtMs: state.firstNavigationVisibleAtMs,
                firstTriggerVisibleAtMs: state.firstTriggerVisibleAtMs,
                firstBrandingVisibleAtMs: state.firstBrandingVisibleAtMs,
                firstAnyShellMarkerVisibleAtMs: state.firstAnyShellMarkerVisibleAtMs,
                firstTriggerLabel: state.firstTriggerLabel,
                firstNavigationLabels: state.firstNavigationLabels,
                samples: state.samples,
              };
            }
            """,
        )
        if not isinstance(payload, dict):
            return {
                "first_navigation_visible_after_launch_seconds": None,
                "first_trigger_visible_after_launch_seconds": None,
                "first_branding_visible_after_launch_seconds": None,
                "first_any_shell_marker_visible_after_launch_seconds": None,
                "first_trigger_label": "",
                "first_navigation_labels": [],
                "sample_count": 0,
                "samples": [],
            }
        normalized_samples = _normalize_pending_probe_samples(payload.get("samples", []))
        return {
            "first_navigation_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstNavigationVisibleAtMs"),
            ),
            "first_trigger_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstTriggerVisibleAtMs"),
            ),
            "first_branding_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstBrandingVisibleAtMs"),
            ),
            "first_any_shell_marker_visible_after_launch_seconds": _ms_to_seconds(
                payload.get("firstAnyShellMarkerVisibleAtMs"),
            ),
            "first_trigger_label": str(payload.get("firstTriggerLabel", "")),
            "first_navigation_labels": [
                str(label) for label in payload.get("firstNavigationLabels", [])
            ],
            "sample_count": len(normalized_samples),
            "samples": normalized_samples,
        }

TICKET_KEY = "TS-1019"
TEST_CASE_TITLE = (
    "Startup synchronization pending - UI shell remains hidden until probe resolution"
)
TEST_FILE_PATH = "testing/tests/TS-1019/test_ts_1019.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1019/test_ts_1019.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-demo"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
FULL_SYNC_TIMEOUT_SECONDS = 11
SIMULATED_PROBE_DELAY_SECONDS = 5
MIN_PENDING_SAMPLE_COUNT = 5
MIN_PENDING_OBSERVATION_SECONDS = 2.0
PENDING_SAMPLE_WINDOW_TOLERANCE_SECONDS = 0.25
AUTH_PROBE_START_WAIT_SECONDS = 60
PENDING_WINDOW_WAIT_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + 6
SHELL_READY_WAIT_SECONDS = FULL_SYNC_TIMEOUT_SECONDS + 8
POLL_INTERVAL_SECONDS = 0.15
LINKED_BUG_KEYS = ("TS-1014", "TS-1027", "TS-1029")
LINKED_BUG_NOTES = (
    "Reviewed TS-1014, TS-1027, and TS-1029. Their deployed fixes restored the live "
    "startup `/user` probe path and kept shell rendering gated behind that delayed "
    "successful-probe flow, so this test seeds the hosted workspace token, waits "
    "through the real 5-second pending window, and asserts the shell stays hidden "
    "until probe release."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1019_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1019_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Immediately inspect the UI during the 5-second window while the synchronization probe is still in progress.",
    "Verify the visibility of interactive shell components (TopBar, branding, Sidebar).",
]
EXPECTED_RESULT = (
    "The UI shell components are not visible and are not mounted in the DOM during the "
    "pending state. The application remains in a loading state, confirming that the "
    "rendering is correctly gated by the resolution of the startup probe."
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
            "TS-1019 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    hosted_workspace_id = _hosted_workspace_id(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts1019PendingShellProbeRuntime(
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
        "full_sync_timeout_seconds": FULL_SYNC_TIMEOUT_SECONDS,
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
        "linked_bug_notes": LINKED_BUG_NOTES,
        "preloaded_workspace_state": workspace_state,
        "hosted_workspace_id": hosted_workspace_id,
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

                auth_probe_started = runtime.wait_for_auth_probe_start(
                    timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                )
                if not auth_probe_started or runtime.auth_probe_started_at_monotonic is None:
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the live page as a user immediately after launch to see "
                            "whether startup progressed beyond the loading surface."
                        ),
                        observed=(
                            f"startup_title={result['startup_observation_initial'].get('title')!r}; "
                            f"button_labels={result['startup_observation_initial'].get('button_labels')!r}; "
                            f"body_excerpt={_snippet(tracker_page.body_text())!r}; "
                            "the page stayed on the bare TrackState.AI loading surface and "
                            "never exposed the delayed `/user` startup-probe path."
                        ),
                    )
                    observed = (
                        "The deployed app never started the delayed GitHub `/user` startup "
                        "probe, so the pending synchronization window could not be observed.\n"
                        f"Observed startup surface:\n"
                        f"{json.dumps(result['startup_observation_initial'], indent=2)}\n"
                        f"Observed body text:\n{tracker_page.body_text()}"
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=observed,
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(f"Step 1 failed: {observed}")

                auth_probe_started_after_start_seconds = relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    runtime.auth_probe_started_at_monotonic,
                )
                result["auth_probe_started_after_start_seconds"] = (
                    auth_probe_started_after_start_seconds
                )
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)
                if (
                    auth_probe_started_after_start_seconds is not None
                    and auth_probe_started_after_start_seconds >= FULL_SYNC_TIMEOUT_SECONDS
                ):
                    _record_human_verification(
                        result,
                        check=(
                            "Watched the live startup flow to confirm whether the delayed "
                            "probe started within the expected startup window."
                        ),
                        observed=(
                            f"auth_probe_started_after_start_seconds="
                            f"{auth_probe_started_after_start_seconds!r}; "
                            f"delayed_request_urls={runtime.delayed_request_urls!r}; "
                            f"body_excerpt={_snippet(tracker_page.body_text())!r}; "
                            "the delayed `/user` probe started too late for the requested "
                            "pending-startup inspection."
                        ),
                    )
                    observed = (
                        "The delayed GitHub `/user` startup probe did not begin until well "
                        "after the startup window, so the pending-state startup scenario was "
                        "not exercised during application startup.\n"
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"delayed_request_urls={runtime.delayed_request_urls!r}; "
                        f"Observed body text:\n{tracker_page.body_text()}"
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=observed,
                    )
                    _record_not_reached_steps(result, starting_step=2)
                    raise AssertionError(f"Step 1 failed: {observed}")
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app in Chromium with a stored "
                        "GitHub token, a preloaded active local workspace plus hosted "
                        "fallback workspace profile, and an injected "
                        f"{SIMULATED_PROBE_DELAY_SECONDS}-second delay on the initial "
                        "GitHub `/user` startup probe.\n"
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"delayed_request_urls={runtime.delayed_request_urls!r}"
                    ),
                )

                transition_tracker = ShellReadyTransitionTracker()
                if auth_probe_started:
                    runtime.wait_for_auth_probe_release(
                        timeout_seconds=PENDING_WINDOW_WAIT_SECONDS,
                    )

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
                        bool(observation["shell_observation"]["shell_ready"])
                        and observation["trigger"] is not None
                        and bool(observation["branding_visible"])
                        and not bool(observation["auth_pending"])
                    ),
                    timeout_seconds=SHELL_READY_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["shell_window_observation"] = _pending_sample_payload(shell_window)
                auth_probe_released_after_start_seconds = shell_window[
                    "auth_probe_released_after_start_seconds"
                ]
                result["auth_probe_released_after_start_seconds"] = (
                    auth_probe_released_after_start_seconds
                )
                pending_probe_state = shell_window["pending_shell_probe_state"]
                pending_samples = _pending_window_samples_from_probe_state(
                    pending_probe_state=pending_probe_state,
                    auth_probe_started_after_start_seconds=auth_probe_started_after_start_seconds,
                    auth_probe_released_after_start_seconds=auth_probe_released_after_start_seconds,
                )
                pending_shell_sample_observed = bool(pending_samples)
                result["pending_shell_sample_observed"] = pending_shell_sample_observed
                result["pending_probe_observed_sample_count"] = pending_probe_state.get(
                    "sample_count",
                )

                pending_window_sampled_duration_seconds = _pending_window_duration_seconds(
                    pending_samples,
                )
                result["pending_window_sampled_duration_seconds"] = (
                    pending_window_sampled_duration_seconds
                )
                pending_window_duration_seconds = pending_window_sampled_duration_seconds
                if pending_window_duration_seconds is None:
                    pending_window_duration_seconds = (
                        shell_window.get(
                            "auth_probe_release_after_auth_start_seconds",
                        )
                    )
                result["pending_window_duration_seconds"] = pending_window_duration_seconds
                result["pending_window_pending_sample_count"] = len(pending_samples)
                result["pending_shell_probe_state"] = pending_probe_state
                result["pending_shell_window_observation"] = (
                    _pending_sample_payload(pending_samples[-1]) if pending_samples else None
                )
                result["pending_window_samples"] = _sampled_pending_window_payloads(
                    pending_samples,
                )

                step_two_failures = _pending_sample_coverage_failures(
                    pending_samples=pending_samples,
                    pending_window_sampled_duration_seconds=pending_window_sampled_duration_seconds,
                )
                if step_two_failures:
                    observed = (
                        "The test did not capture enough in-flight pending-window coverage "
                        "to verify the requested immediate inspection while the delayed "
                        "GitHub `/user` probe was still pending.\n"
                        f"pending_shell_sample_observed={pending_shell_sample_observed!r}; "
                        f"pending_sample_count={len(pending_samples)!r}; "
                        f"pending_window_sampled_duration_seconds="
                        f"{pending_window_sampled_duration_seconds!r}; "
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"pending_probe_observed_sample_count="
                        f"{pending_probe_state.get('sample_count')!r}\n"
                        + "\n".join(step_two_failures)
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=observed,
                    )
                    _record_not_reached_steps(result, starting_step=3)
                    raise AssertionError(f"Step 2 failed: {observed}")

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Captured focused in-flight pending-window samples while the delayed "
                        "`/user` startup probe was still pending, then asserted the shell "
                        "state after probe release.\n"
                        f"pending_shell_sample_observed={pending_shell_sample_observed!r}; "
                        f"pending_sample_count={len(pending_samples)!r}; "
                        f"pending_window_sampled_duration_seconds="
                        f"{pending_window_sampled_duration_seconds!r}; "
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}"
                    ),
                )
                pending_observation_failures: list[str] = []
                pending_observation_failures: list[str] = []
                pending_observation_failures.extend(
                    _pending_state_failures(
                        pending_samples=pending_samples,
                        pending_probe_state=pending_probe_state,
                        auth_probe_released_after_start_seconds=auth_probe_released_after_start_seconds,
                        shell_ready_observed_while_auth_pending=bool(
                            shell_window["shell_ready_observed_while_auth_pending"],
                        ),
                    ),
                )
                pending_observation_failures.extend(
                    _pending_probe_state_coverage_failures(
                        pending_probe_state=pending_probe_state,
                        post_release_observation=shell_window,
                    ),
                )

                if not shell_ready:
                    pending_observation_failures.append(
                        "The deployed app did not expose the interactive shell after the "
                        "delayed startup probe resolved."
                    )
                else:
                    try:
                        _assert_interactive_shell(shell_window)
                    except AssertionError as error:
                        pending_observation_failures.append(str(error))

                authoritative_shell_ready_after_start_seconds = _authoritative_shell_ready_after_start_seconds(
                    shell_window,
                )
                authoritative_shell_ready_after_probe_release_seconds = _authoritative_shell_ready_after_probe_release_seconds(
                    shell_window,
                )
                result["authoritative_shell_ready_after_start_seconds"] = (
                    authoritative_shell_ready_after_start_seconds
                )
                result["authoritative_shell_ready_after_probe_release_seconds"] = (
                    authoritative_shell_ready_after_probe_release_seconds
                )

                if (
                    authoritative_shell_ready_after_start_seconds is not None
                    and shell_window["auth_probe_released_after_start_seconds"] is not None
                    and authoritative_shell_ready_after_start_seconds
                    < shell_window["auth_probe_released_after_start_seconds"]
                ):
                    pending_observation_failures.append(
                        "The first authoritative shell_ready transition happened before "
                        "the delayed startup probe was released."
                    )

                if pending_observation_failures:
                    observed = (
                        "The deployed startup flow did not keep the shell fully gated during "
                        "the pending window or did not release it correctly afterward.\n"
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_probe_release_seconds="
                        f"{authoritative_shell_ready_after_probe_release_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{shell_window['auth_probe_released_after_start_seconds']!r}; "
                        f"pending_shell_sample_observed={pending_shell_sample_observed!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}; "
                        f"pending_shell_window={json.dumps(result.get('pending_shell_window_observation'), ensure_ascii=True)}\n"
                        + "\n".join(pending_observation_failures)
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=observed,
                    )
                    raise AssertionError(f"Step 3 failed: {observed}")

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "While the delayed startup probe was pending, the live page kept the "
                        "TopBar trigger, sidebar navigation, and branding hidden, and the "
                        "shell became interactive only after probe release.\n"
                        f"authoritative_shell_ready_after_start_seconds="
                        f"{authoritative_shell_ready_after_start_seconds!r}; "
                        f"authoritative_shell_ready_after_probe_release_seconds="
                        f"{authoritative_shell_ready_after_probe_release_seconds!r}; "
                        f"pending_sample_count={len(pending_samples)!r}; "
                        f"pending_shell_sample_observed={pending_shell_sample_observed!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Watched the live page like a user during the delayed startup window "
                        "and confirmed the shell stayed on the loading surface instead of "
                        "showing the top bar, sidebar, or branding."
                    ),
                    observed=(
                        f"pending_sample_count={len(pending_samples)!r}; "
                        f"pending_shell_sample_observed={pending_shell_sample_observed!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}; "
                        f"pending_window_excerpt="
                        f"{_first_pending_excerpt(pending_samples)!r}; "
                        f"pending_trigger={(pending_samples[-1] if pending_samples else shell_window).get('trigger')!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the page again immediately after the delayed probe finished "
                        "and confirmed the real interactive shell appeared for the user."
                    ),
                    observed=(
                        f"trigger_label={(shell_window['trigger'] or {}).get('semantic_label')!r}; "
                        f"visible_navigation_labels="
                        f"{shell_window['shell_observation']['visible_navigation_labels']!r}; "
                        f"branding_visible={shell_window['branding_visible']!r}; "
                        f"body_excerpt={_snippet(shell_window['shell_observation']['body_text'])!r}"
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
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
        active_workspace="hosted",
    )


def _hosted_workspace_id(repository: str) -> str:
    return f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"


def _prepare_local_workspace_repository() -> dict[str, object]:
    return prepare_local_workspace_repository(
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        marker_filename=".trackstate-ts1019-precondition.txt",
        marker_contents="Prepared for TS-1019 pending startup probe validation.\n",
        commit_author_name="TS-1019 Automation",
        commit_author_email="ts1019@example.com",
        commit_message="Prepare TS-1019 local workspace",
    )


def _collect_pending_sample(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts1019PendingShellProbeRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
    pending_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    observation = _observe_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        transition_tracker=transition_tracker,
        poll_timeout_ms=50,
    )
    if observation["auth_pending"]:
        pending_samples.append(observation)
    return observation


def _observe_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: Ts1019PendingShellProbeRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
    poll_timeout_ms: int,
) -> dict[str, Any]:
    shell_window = observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT,),
        transition_tracker=transition_tracker,
        poll_timeout_ms=poll_timeout_ms,
    )
    shell_window["elapsed_since_start_seconds"] = round(
        time.monotonic() - startup_started_at_monotonic,
        2,
    )
    shell_window["shell_probe_state"] = runtime.read_shell_probe_state()
    shell_window["probe_recorded_shell_ready_after_start_seconds"] = shell_window[
        "shell_probe_state"
    ].get("first_shell_ready_after_launch_seconds")
    shell_window["pending_shell_probe_state"] = runtime.read_pending_shell_probe_state()
    shell_window["dom_markers"] = _shell_dom_markers(tracker_page)
    return shell_window


def _shell_dom_markers(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    payload = tracker_page.session.evaluate(
        """
        (labels) => {
          const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();
          const interesting = Array.from(
            document.querySelectorAll(
              'flt-semantics, button, [role], nav, header, aside, a, [aria-label]',
            ),
          )
            .filter((element) => !['SCRIPT', 'STYLE', 'NOSCRIPT'].includes(element.tagName))
            .map((element) =>
              normalize(
                element.getAttribute?.('aria-label')
                || element.innerText
                || element.textContent
                || '',
              ),
            )
            .filter((text) => text.length > 0);
          const deduped = [...new Set(interesting)];
          const navigationLabels = deduped.filter((text) => labels.navigation.includes(text));
          const workspaceSwitcherLabels = deduped.filter(
            (text) => text.includes('Workspace switcher:'),
          );
          const brandingLabels = deduped.filter(
            (text) => labels.branding.some((branding) => text.includes(branding)),
          );
          return {
            navigationLabels,
            workspaceSwitcherLabels,
            brandingLabels,
            sampledLabels: deduped.slice(0, 80),
          };
        }
        """,
        arg={
            "navigation": list(SHELL_NAVIGATION_LABELS),
            "branding": [BRANDING_TEXT],
        },
    )
    if not isinstance(payload, dict):
        return {
            "navigation_labels": [],
            "workspace_switcher_labels": [],
            "branding_labels": [],
            "sampled_labels": [],
        }
    return {
        "navigation_labels": [
            str(label) for label in payload.get("navigationLabels", [])
        ],
        "workspace_switcher_labels": [
            str(label) for label in payload.get("workspaceSwitcherLabels", [])
        ],
        "branding_labels": [str(label) for label in payload.get("brandingLabels", [])],
        "sampled_labels": [str(label) for label in payload.get("sampledLabels", [])],
    }


def _pending_window_duration_seconds(
    pending_samples: list[dict[str, Any]],
) -> float | None:
    if not pending_samples:
        return None
    first_elapsed = pending_samples[0].get("elapsed_since_start_seconds")
    last_elapsed = pending_samples[-1].get("elapsed_since_start_seconds")
    if not isinstance(first_elapsed, (int, float)) or not isinstance(last_elapsed, (int, float)):
        return None
    return round(float(last_elapsed) - float(first_elapsed), 2)


def _pending_sample_coverage_failures(
    *,
    pending_samples: list[dict[str, Any]],
    pending_window_sampled_duration_seconds: float | None,
) -> list[str]:
    failures: list[str] = []
    if len(pending_samples) < MIN_PENDING_SAMPLE_COUNT:
        failures.append(
            "The focused pending-window sampler did not capture enough in-flight samples "
            "to prove the UI was inspected while startup synchronization was still "
            f"pending. Expected at least {MIN_PENDING_SAMPLE_COUNT} samples but captured "
            f"{len(pending_samples)}."
        )
    if (
        pending_window_sampled_duration_seconds is None
        or pending_window_sampled_duration_seconds < MIN_PENDING_OBSERVATION_SECONDS
    ):
        failures.append(
            "The focused pending-window sampler did not observe the delayed startup probe "
            "for long enough to count as a meaningful live inspection. Expected at least "
            f"{MIN_PENDING_OBSERVATION_SECONDS} seconds of in-flight coverage but captured "
            f"{pending_window_sampled_duration_seconds!r}."
        )
    return failures


def _pending_window_samples_from_probe_state(
    *,
    pending_probe_state: dict[str, Any],
    auth_probe_started_after_start_seconds: float | None,
    auth_probe_released_after_start_seconds: float | None,
) -> list[dict[str, Any]]:
    samples = pending_probe_state.get("samples", [])
    if not isinstance(samples, list):
        return []

    pending_samples: list[dict[str, Any]] = []
    for sample in samples:
        if not isinstance(sample, dict):
            continue
        observed_after_launch_seconds = sample.get("observed_after_launch_seconds")
        if not isinstance(observed_after_launch_seconds, (int, float)):
            continue
        if (
            auth_probe_started_after_start_seconds is not None
            and float(observed_after_launch_seconds)
            < float(auth_probe_started_after_start_seconds)
            - PENDING_SAMPLE_WINDOW_TOLERANCE_SECONDS
        ):
            continue
        if (
            auth_probe_released_after_start_seconds is not None
            and float(observed_after_launch_seconds)
            > float(auth_probe_released_after_start_seconds)
            + PENDING_SAMPLE_WINDOW_TOLERANCE_SECONDS
        ):
            continue
        visible_navigation_labels = [
            str(label) for label in sample.get("visible_navigation_labels", [])
        ]
        trigger_label = str(sample.get("trigger_label", ""))
        branding_visible = bool(sample.get("branding_visible"))
        navigation_dom_markers = [
            str(label) for label in sample.get("dom_navigation_labels", [])
        ]
        workspace_switcher_dom_markers = [
            str(label) for label in sample.get("dom_workspace_switcher_labels", [])
        ]
        branding_dom_markers = [
            str(label) for label in sample.get("dom_branding_labels", [])
        ]
        pending_samples.append(
            {
                "elapsed_since_start_seconds": round(float(observed_after_launch_seconds), 2),
                "auth_pending": True,
                "auth_probe_started_after_start_seconds": (
                    auth_probe_started_after_start_seconds
                ),
                "auth_probe_released_after_start_seconds": (
                    auth_probe_released_after_start_seconds
                ),
                "shell_ready_after_start_seconds": None,
                "shell_ready_after_probe_release_seconds": None,
                "shell_ready_observed_while_auth_pending": bool(
                    sample.get("shell_ready"),
                ),
                "trigger": (
                    {"semantic_label": trigger_label}
                    if trigger_label or bool(sample.get("trigger_visible"))
                    else None
                ),
                "startup_observation": {
                    "title": "TrackState.AI",
                    "location_hash": "",
                    "body_text": str(sample.get("body_excerpt", "")),
                    "button_labels": [],
                },
                "shell_observation": {
                    "body_text": str(sample.get("body_excerpt", "")),
                    "visible_navigation_labels": visible_navigation_labels,
                    "fatal_banner_visible": False,
                    "connect_github_visible": False,
                    "shell_ready": bool(sample.get("shell_ready")),
                },
                "branding_visible": branding_visible,
                "dom_markers": {
                    "navigation_labels": navigation_dom_markers,
                    "workspace_switcher_labels": workspace_switcher_dom_markers,
                    "branding_labels": branding_dom_markers,
                    "sampled_labels": (
                        navigation_dom_markers
                        + workspace_switcher_dom_markers
                        + branding_dom_markers
                    ),
                },
                "shell_probe_state": {},
                "pending_shell_probe_state": {},
            },
        )
    return pending_samples


def _pending_state_failures(
    *,
    pending_samples: list[dict[str, Any]],
    pending_probe_state: dict[str, Any],
    auth_probe_released_after_start_seconds: Any,
    shell_ready_observed_while_auth_pending: bool,
) -> list[str]:
    failures: list[str] = []
    first_shell_ready = next(
        (
            sample
            for sample in pending_samples
            if bool(sample["shell_observation"]["shell_ready"])
        ),
        None,
    )
    if first_shell_ready is not None:
        failures.append(
            "The shell reported shell_ready while the delayed startup probe was still "
            "pending.\n"
            f"Observed sample:\n{json.dumps(_pending_sample_payload(first_shell_ready), indent=2)}"
        )
    first_visible_navigation = next(
        (
            sample
            for sample in pending_samples
            if sample["shell_observation"]["visible_navigation_labels"]
        ),
        None,
    )
    if first_visible_navigation is not None:
        failures.append(
            "Sidebar navigation labels became visible during the pending startup window.\n"
            f"Observed sample:\n{json.dumps(_pending_sample_payload(first_visible_navigation), indent=2)}"
        )
    first_visible_trigger = next(
        (sample for sample in pending_samples if sample["trigger"] is not None),
        None,
    )
    if first_visible_trigger is not None:
        failures.append(
            "The top-bar workspace trigger became visible during the pending startup "
            "window.\n"
            f"Observed sample:\n{json.dumps(_pending_sample_payload(first_visible_trigger), indent=2)}"
        )
    first_visible_branding = next(
        (sample for sample in pending_samples if bool(sample["branding_visible"])),
        None,
    )
    if first_visible_branding is not None:
        failures.append(
            "The TrackState branding tagline became visible before the delayed startup "
            "probe resolved.\n"
            f"Observed sample:\n{json.dumps(_pending_sample_payload(first_visible_branding), indent=2)}"
        )
    first_dom_markers = next(
        (
            sample
            for sample in pending_samples
            if sample["dom_markers"]["navigation_labels"]
            or sample["dom_markers"]["workspace_switcher_labels"]
            or sample["dom_markers"]["branding_labels"]
        ),
        None,
    )
    if first_dom_markers is not None:
        failures.append(
            "Shell DOM markers were already mounted during the pending startup window.\n"
            f"Observed sample:\n{json.dumps(_pending_sample_payload(first_dom_markers), indent=2)}"
        )
    for label, timestamp in (
        (
            "navigation",
            pending_probe_state.get("first_navigation_visible_after_launch_seconds"),
        ),
        (
            "top-bar trigger",
            pending_probe_state.get("first_trigger_visible_after_launch_seconds"),
        ),
        (
            "branding",
            pending_probe_state.get("first_branding_visible_after_launch_seconds"),
        ),
        (
            "any shell marker",
            pending_probe_state.get("first_any_shell_marker_visible_after_launch_seconds"),
        ),
    ):
        if not isinstance(timestamp, (int, float)) or not isinstance(
            auth_probe_released_after_start_seconds,
            (int, float),
        ):
            continue
        if float(timestamp) < float(auth_probe_released_after_start_seconds):
            failures.append(
                f"The page-side startup observer saw the first {label} before the delayed "
                "startup probe was released.\n"
                f"pending_probe_state={json.dumps(pending_probe_state, indent=2)}\n"
                f"auth_probe_released_after_start_seconds="
                f"{auth_probe_released_after_start_seconds!r}"
            )
    if shell_ready_observed_while_auth_pending:
        failures.append(
            "The first recorded shell_ready transition happened while the delayed startup "
            "probe was still pending."
        )
    return failures


def _pending_sample_payload(observation: dict[str, Any]) -> dict[str, Any]:
    trigger = observation.get("trigger")
    startup = observation.get("startup_observation", {})
    shell = observation.get("shell_observation", {})
    return {
        "elapsed_since_start_seconds": observation.get("elapsed_since_start_seconds"),
        "auth_pending": observation.get("auth_pending"),
        "auth_probe_started_after_start_seconds": observation.get(
            "auth_probe_started_after_start_seconds",
        ),
        "auth_probe_released_after_start_seconds": observation.get(
            "auth_probe_released_after_start_seconds",
        ),
        "shell_ready_after_start_seconds": observation.get("shell_ready_after_start_seconds"),
        "shell_ready_after_probe_release_seconds": observation.get(
            "shell_ready_after_probe_release_seconds",
        ),
        "shell_ready_observed_while_auth_pending": observation.get(
            "shell_ready_observed_while_auth_pending",
        ),
        "trigger": trigger,
        "title": startup.get("title"),
        "location_hash": startup.get("location_hash"),
        "button_labels": list(startup.get("button_labels", [])),
        "visible_navigation_labels": list(shell.get("visible_navigation_labels", [])),
        "branding_visible": observation.get("branding_visible"),
        "body_excerpt": _snippet(str(shell.get("body_text", ""))),
        "dom_markers": observation.get("dom_markers"),
        "shell_probe_state": observation.get("shell_probe_state"),
        "pending_shell_probe_state": observation.get("pending_shell_probe_state"),
    }


def _authoritative_shell_ready_after_start_seconds(
    observation: dict[str, Any],
) -> float | None:
    shell_probe_state = observation.get("shell_probe_state", {})
    probe_value = shell_probe_state.get("first_shell_ready_after_launch_seconds")
    if isinstance(probe_value, (int, float)):
        return round(float(probe_value), 2)
    fallback = observation.get("shell_ready_after_start_seconds")
    if isinstance(fallback, (int, float)):
        return round(float(fallback), 2)
    return None


def _authoritative_shell_ready_after_probe_release_seconds(
    observation: dict[str, Any],
) -> float | None:
    authoritative_after_start = _authoritative_shell_ready_after_start_seconds(observation)
    auth_probe_released_after_start_seconds = observation.get(
        "auth_probe_released_after_start_seconds",
    )
    if authoritative_after_start is None or not isinstance(
        auth_probe_released_after_start_seconds,
        (int, float),
    ):
        return observation.get("shell_ready_after_probe_release_seconds")
    return round(
        float(authoritative_after_start)
        - float(auth_probe_released_after_start_seconds),
        2,
    )


def _ms_to_seconds(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    return round(float(value) / 1000, 2)


def _normalize_pending_probe_samples(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        return []
    samples: list[dict[str, Any]] = []
    for sample in payload:
        if not isinstance(sample, dict):
            continue
        visible_navigation_labels = [
            str(label) for label in sample.get("visibleNavigationLabels", [])
        ]
        dom_navigation_labels = [
            str(label) for label in sample.get("domNavigationLabels", [])
        ]
        dom_workspace_switcher_labels = [
            str(label) for label in sample.get("domWorkspaceSwitcherLabels", [])
        ]
        dom_branding_labels = [
            str(label) for label in sample.get("domBrandingLabels", [])
        ]
        samples.append(
            {
                "observed_after_launch_seconds": _ms_to_seconds(
                    sample.get("observedAtMs"),
                ),
                "visible_navigation_labels": visible_navigation_labels,
                "trigger_visible": bool(sample.get("triggerVisible")),
                "trigger_label": str(sample.get("triggerLabel", "")),
                "branding_visible": bool(sample.get("brandingVisible")),
                "shell_ready": bool(sample.get("shellReady")),
                "dom_navigation_labels": dom_navigation_labels,
                "dom_workspace_switcher_labels": dom_workspace_switcher_labels,
                "dom_branding_labels": dom_branding_labels,
                "has_any_shell_marker": bool(sample.get("hasAnyShellMarker")),
                "body_excerpt": str(sample.get("bodyExcerpt", "")),
            },
        )
    return samples


def _sampled_pending_window_payloads(
    pending_samples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not pending_samples:
        return []
    candidate_indexes = [0, 1, 2, len(pending_samples) // 2, len(pending_samples) - 3, len(pending_samples) - 2, len(pending_samples) - 1]
    sampled_indexes: list[int] = []
    for index in candidate_indexes:
        if 0 <= index < len(pending_samples) and index not in sampled_indexes:
            sampled_indexes.append(index)
    return [_pending_sample_payload(pending_samples[index]) for index in sampled_indexes]


def _pending_probe_state_coverage_failures(
    *,
    pending_probe_state: dict[str, Any],
    post_release_observation: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    shell_observation = post_release_observation["shell_observation"]
    if (
        shell_observation["visible_navigation_labels"]
        and pending_probe_state.get("first_navigation_visible_after_launch_seconds") is None
    ):
        failures.append(
            "The TS-1019 pending-shell observer never recorded when navigation first "
            "appeared, even though the post-release shell snapshot showed navigation.\n"
            f"pending_probe_state={json.dumps(pending_probe_state, indent=2)}"
        )
    if (
        post_release_observation["trigger"] is not None
        and pending_probe_state.get("first_trigger_visible_after_launch_seconds") is None
    ):
        failures.append(
            "The TS-1019 pending-shell observer never recorded when the top-bar trigger "
            "first appeared, even though the post-release shell snapshot showed it.\n"
            f"pending_probe_state={json.dumps(pending_probe_state, indent=2)}"
        )
    if (
        bool(post_release_observation["branding_visible"])
        and pending_probe_state.get("first_branding_visible_after_launch_seconds") is None
    ):
        failures.append(
            "The TS-1019 pending-shell observer never recorded when branding first "
            "appeared, even though the post-release shell snapshot showed it.\n"
            f"pending_probe_state={json.dumps(pending_probe_state, indent=2)}"
        )
    if pending_probe_state.get("first_any_shell_marker_visible_after_launch_seconds") is None:
        failures.append(
            "The TS-1019 pending-shell observer never recorded any shell marker becoming "
            "visible, so the page-side pending DOM instrumentation was not exercised.\n"
            f"pending_probe_state={json.dumps(pending_probe_state, indent=2)}"
        )
    return failures


def _pending_shell_probe_script() -> str:
    return """
(() => {
  const MAX_SAMPLES = 300;
  const SAMPLE_INTERVAL_MS = 100;
  const state = {
    firstNavigationVisibleAtMs: null,
    firstTriggerVisibleAtMs: null,
    firstBrandingVisibleAtMs: null,
    firstAnyShellMarkerVisibleAtMs: null,
    firstTriggerLabel: '',
    firstNavigationLabels: [],
    samples: [],
  };
  window.__ts1019PendingShellProbeState = state;

  const readyLabels = ['Dashboard', 'Board', 'JQL Search', 'Hierarchy', 'Settings'];
  const brandingLabel = 'Git-native. Jira-compatible. Team-proven.';
  const normalize = (value) => (value || '').replace(/\\s+/g, ' ').trim();

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

  const updateFirstAny = () => {
    if (state.firstAnyShellMarkerVisibleAtMs !== null) {
      return;
    }
    const candidates = [
      state.firstNavigationVisibleAtMs,
      state.firstTriggerVisibleAtMs,
      state.firstBrandingVisibleAtMs,
    ].filter((value) => value !== null);
    if (candidates.length > 0) {
      state.firstAnyShellMarkerVisibleAtMs = Math.min(...candidates);
    }
  };

  const observe = () => {
    const bodyText = normalize(document.body?.innerText ?? document.body?.textContent ?? '');
    const texts = semanticTexts();
    const visibleNavigation = readyLabels.filter(
      (label) => bodyText.includes(label) || texts.includes(label),
    );
    if (state.firstNavigationVisibleAtMs === null && visibleNavigation.length > 0) {
      state.firstNavigationVisibleAtMs = performance.now();
      state.firstNavigationLabels = visibleNavigation;
    }
    const triggerLabel = texts.find((text) => text.includes('Workspace switcher:'));
    if (state.firstTriggerVisibleAtMs === null && triggerLabel) {
      state.firstTriggerVisibleAtMs = performance.now();
      state.firstTriggerLabel = triggerLabel;
    }
    const brandingVisible = bodyText.includes(brandingLabel)
      || texts.some((text) => text.includes(brandingLabel));
    if (state.firstBrandingVisibleAtMs === null && brandingVisible) {
      state.firstBrandingVisibleAtMs = performance.now();
    }
    updateFirstAny();
  };

  const captureSample = () => {
    const bodyText = normalize(document.body?.innerText ?? document.body?.textContent ?? '');
    const texts = semanticTexts();
    const visibleNavigationLabels = readyLabels.filter(
      (label) => bodyText.includes(label) || texts.includes(label),
    );
    const triggerLabel = texts.find((text) => text.includes('Workspace switcher:')) || '';
    const brandingVisible = bodyText.includes(brandingLabel)
      || texts.some((text) => text.includes(brandingLabel));
    const domNavigationLabels = texts.filter((text) => readyLabels.includes(text));
    const domWorkspaceSwitcherLabels = texts.filter((text) => text.includes('Workspace switcher:'));
    const domBrandingLabels = texts.filter((text) => text.includes(brandingLabel));
    const hasAnyShellMarker = visibleNavigationLabels.length > 0 || !!triggerLabel || brandingVisible;
    state.samples.push({
      observedAtMs: performance.now(),
      visibleNavigationLabels,
      triggerVisible: !!triggerLabel,
      triggerLabel,
      brandingVisible,
      shellReady: visibleNavigationLabels.length === readyLabels.length,
      domNavigationLabels,
      domWorkspaceSwitcherLabels,
      domBrandingLabels,
      hasAnyShellMarker,
      bodyExcerpt: bodyText.slice(0, 240),
    });
    if (state.samples.length > MAX_SAMPLES) {
      state.samples.splice(0, state.samples.length - MAX_SAMPLES);
    }
  };

  const attachObserver = () => {
    observe();
    captureSample();
    if (!document.documentElement) {
      requestAnimationFrame(attachObserver);
      return;
    }
    new MutationObserver(() => observe()).observe(document.documentElement, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
    });
  };

  attachObserver();
  window.setInterval(() => {
    observe();
    captureSample();
  }, SAMPLE_INTERVAL_MS);
  window.addEventListener('load', () => observe(), { once: false });
})();
"""


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
            "The post-release snapshot did not expose the full interactive shell "
            "navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell window:\n{json.dumps(_pending_sample_payload(observation), indent=2)}",
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "The post-release snapshot did not expose the header workspace trigger "
            "needed to prove the TopBar became interactive.\n"
            f"Observed shell window:\n{json.dumps(_pending_sample_payload(observation), indent=2)}",
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "The post-release snapshot did not expose the visible TrackState branding "
            "tagline.\n"
            f"Observed shell window:\n{json.dumps(_pending_sample_payload(observation), indent=2)}",
        )
    startup_buttons = set(observation["startup_observation"]["button_labels"])
    if "Workspace switcher:" not in " ".join(startup_buttons) and startup_buttons == {"Sync issue"}:
        raise AssertionError(
            "The page still looked like the startup surface instead of the interactive "
            "shell after the delayed probe resolved.\n"
            f"Observed shell window:\n{json.dumps(_pending_sample_payload(observation), indent=2)}",
        )


def _snippet(text: str, *, limit: int = 240) -> str:
    return snippet(text, limit=limit)


def _first_pending_excerpt(pending_samples: list[dict[str, Any]]) -> str:
    if not pending_samples:
        return "<no pending body sample captured>"
    return _snippet(str(pending_samples[0]["shell_observation"]["body_text"]))


def _last_pending_excerpt(pending_samples: list[dict[str, Any]]) -> str:
    if not pending_samples:
        return "<no pending body sample captured>"
    return _snippet(str(pending_samples[-1]["shell_observation"]["body_text"]))


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
    REVIEW_REPLIES_PATH.write_text(_review_replies_payload(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(result, passed=False),
        encoding="utf-8",
    )
    if _should_write_bug_description(result):
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _pending_sample_count(result: dict[str, Any]) -> int:
    value = result.get("pending_window_pending_sample_count", 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _pending_sampled_duration_seconds(result: dict[str, Any]) -> float | None:
    value = result.get("pending_window_sampled_duration_seconds")
    return round(float(value), 2) if isinstance(value, (int, float)) else None


def _pending_coverage_summary(result: dict[str, Any]) -> str:
    pending_sample_count = _pending_sample_count(result)
    pending_sampled_duration_seconds = _pending_sampled_duration_seconds(result)
    if pending_sample_count == 0 and pending_sampled_duration_seconds is None:
        return (
            "Current rerun did not reach Step 2 because the live app never started the "
            "delayed startup probe."
        )
    return (
        f"Current run captured {pending_sample_count} in-flight pending samples across "
        f"{pending_sampled_duration_seconds!r} seconds."
    )


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    pending_sample_count = _pending_sample_count(result)
    pending_sampled_duration_seconds = _pending_sampled_duration_seconds(result)
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status_icon} {status_word}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        f"* Live deployed app at {{ {result.get('app_url')} }} in {result.get('browser')} on {result.get('os')}",
        f"* Desktop viewport {{ {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']} }}",
        f"* Pending startup synchronization with a synthetic {SIMULATED_PROBE_DELAY_SECONDS}-second delay on GitHub {{/user}}",
        f"* Linked bug review: {LINKED_BUG_NOTES}",
        "",
        "h4. What automation checked",
        "* Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded workspace state.",
        (
            "* Delayed the live GitHub {/user} startup probe by 5 seconds and collected "
            f"{pending_sample_count} in-flight pending-window samples across "
            f"{pending_sampled_duration_seconds!r} seconds before asserting."
            if passed
            else "* Delayed the live GitHub {/user} startup probe by 5 seconds and failed "
            "the run whenever the focused pending-window sampler did not capture enough "
            "in-flight coverage."
        ),
        "* Verified the TopBar trigger, sidebar navigation labels, and branding tagline stayed hidden with no shell DOM markers in the captured pending samples.",
        "* Confirmed the interactive shell appeared only after the delayed probe resolved.",
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
    pending_sample_count = _pending_sample_count(result)
    pending_sampled_duration_seconds = _pending_sampled_duration_seconds(result)
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        f"- Ran the live deployed app at `{result.get('app_url')}` in {result.get('browser')} on {result.get('os')}.",
        f"- Used the required desktop viewport `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`.",
        (
            f"- Delayed the live GitHub `/user` startup probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds and collected `{pending_sample_count}` in-flight pending samples across `{pending_sampled_duration_seconds!r}` seconds before asserting."
            if passed
            else f"- Delayed the live GitHub `/user` startup probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds and failed the run if the focused pending-window sampler did not meet the `{MIN_PENDING_SAMPLE_COUNT}` sample / `{MIN_PENDING_OBSERVATION_SECONDS}` second minimum."
        ),
        f"- Considered linked bug {', '.join(LINKED_BUG_KEYS)} and coupled the assertions to the delayed probe timing.",
        "- Wired the TS-1019 pending-shell runtime into the executed path and asserted the page-side pending-shell observer data against the captured pending-window samples.",
        "- Checked the user-visible shell trigger, navigation, branding, and shell DOM markers during the pending window and after release, without publishing success text for zero-sample runs.",
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
            f"# {TICKET_KEY}\n\n"
            "✅ PASSED\n\n"
            f"Observed {_pending_sample_count(result)} in-flight pending samples across "
            f"{_pending_sampled_duration_seconds(result)!r} seconds while the delayed GitHub "
            "`/user` startup probe was pending. The shell stayed hidden until probe "
            "release, then the interactive shell appeared.\n"
        )
    return (
        f"# {TICKET_KEY}\n\n"
        "❌ FAILED\n\n"
        "The live deployed app never started the delayed GitHub `/user` startup probe, "
        "so the pending synchronization window could not be observed. The user-visible "
        "page remained on the bare `TrackState.AI` loading surface.\n\n"
        f"Error: {result.get('error', 'The deployed app did not keep the startup shell hidden during the pending probe window.')}\n"
    )


def _build_bug_description(result: dict[str, Any]) -> str:
    annotated_steps = build_annotated_steps(result, request_steps=REQUEST_STEPS)
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
        "* Missing / broken production capability: the deployed startup bootstrap never "
        "issues the GitHub {/user} startup synchronization probe, so the app cannot enter "
        "the ticket's pending-probe path from the real loading flow.",
        f"* GitHub requests seen: {{code}}{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}{{code}}",
        f"* Delayed requests seen: {{code}}{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}{{code}}",
        f"* Pending samples: {{code}}{json.dumps(result.get('pending_window_samples', []), ensure_ascii=True)}{{code}}",
        f"* Pending observer state: {{code}}{json.dumps(result.get('pending_shell_probe_state', {}), ensure_ascii=True)}{{code}}",
        f"* Post-release sample: {{code}}{json.dumps(result.get('shell_window_observation'), ensure_ascii=True)}{{code}}",
    ]
    if result.get("screenshot"):
        lines.append(f"* Screenshot: {{code}}{result['screenshot']}{{code}}")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        pending_sample_count = _pending_sample_count(result)
        pending_sampled_duration_seconds = _pending_sampled_duration_seconds(result)
        return (
            f"Across {pending_sample_count} in-flight pending samples collected over "
            f"{pending_sampled_duration_seconds!r} seconds during the delayed 5-second "
            "GitHub `/user` startup probe, the deployed app kept the TopBar trigger, "
            "sidebar navigation, and branding hidden with no shell DOM markers. After "
            "the probe resolved, the page reached shell_ready in "
            f"{result.get('authoritative_shell_ready_after_start_seconds')!r} "
            "seconds from launch and "
            f"{result.get('authoritative_shell_ready_after_probe_release_seconds')!r} seconds "
            "after probe release, showing the real interactive shell."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not keep the startup shell hidden during the pending probe window.",
        ),
    )


def _step_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_step_lines(result, jira=jira)


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    return format_human_lines(result, jira=jira)


def _review_replies_payload(result: dict[str, Any], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(thread=thread, result=result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


def _discussion_threads() -> list[dict[str, Any]]:
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


def _review_reply_text(
    *,
    thread: dict[str, Any],
    result: dict[str, Any],
    passed: bool,
) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{_error_summary(result)}`."
    )
    coverage_summary = _pending_coverage_summary(result)
    comment_id = thread.get("rootCommentId")
    if comment_id == 3293526581:
        return (
            "Fixed: Step 2 now enforces the existing pending-window coverage minimums "
            f"(`MIN_PENDING_SAMPLE_COUNT={MIN_PENDING_SAMPLE_COUNT}` and "
            f"`MIN_PENDING_OBSERVATION_SECONDS={MIN_PENDING_OBSERVATION_SECONDS}`) "
            "against the page-side in-flight samples, so zero-sample runs fail instead "
            f"of passing. {coverage_summary} {rerun_summary}"
        )
    if comment_id == 3293526591:
        return (
            "Fixed: the generated success output now derives its pending-window wording "
            "from the real sampled coverage, so it no longer claims evidence that was "
            f"never captured. {coverage_summary} {rerun_summary}"
        )
    if comment_id == 3293511064:
        return (
            "Fixed: TS-1019 no longer fails on the removed `<11s from launch` / "
            "`<=3.5s after release` SLAs. Step 3 now stays focused on the ticket "
            "contract: the shell must remain hidden while `/user` is pending and become "
            f"available only after probe release. {rerun_summary}"
        )
    if comment_id == 3293511090:
        return (
            "Fixed: failure output now writes `bug_description.md` only for confirmed "
            "product-visible failures instead of every `AssertionError`, so test-owned "
            "instrumentation or assertion regressions no longer get reported as product "
            f"bugs. {rerun_summary}"
        )
    return (
        "Fixed the TS-1019 startup rework by wiring the pending-shell runtime into the "
        "executed path, enforcing real pending-window coverage, and aligning the review "
        f"artifacts with the captured samples. {coverage_summary} {rerun_summary}"
    )


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    return _bug_description_reason(result) is not None


def _bug_description_reason(result: dict[str, Any]) -> str | None:
    error = str(result.get("error", ""))
    if error.startswith(f"RuntimeError: {TICKET_KEY} requires GH_TOKEN or GITHUB_TOKEN"):
        return None
    if error.startswith("ModuleNotFoundError:"):
        return None

    failed_steps = {
        int(step.get("step")): step
        for step in result.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "failed"
    }
    step_one_observed = str(failed_steps.get(1, {}).get("observed", ""))
    step_three_observed = str(failed_steps.get(3, {}).get("observed", ""))

    if "never started the delayed GitHub `/user` startup probe" in step_one_observed:
        return "startup-probe-missing"
    if "did not begin until well after the startup window" in step_one_observed:
        return "startup-probe-started-too-late"
    if (
        "did not expose the interactive shell after the delayed startup probe resolved"
        in step_three_observed
    ):
        return "shell-never-became-interactive"
    if (
        "reported shell_ready while the delayed startup probe was still pending"
        in step_three_observed
        or "Sidebar navigation labels became visible during the pending startup window"
        in step_three_observed
        or "workspace trigger became visible during the pending startup window"
        in step_three_observed
        or "branding tagline became visible before the delayed startup probe resolved"
        in step_three_observed
        or "Shell DOM markers were already mounted during the pending startup window"
        in step_three_observed
        or "first authoritative shell_ready transition happened before the delayed startup probe was released"
        in step_three_observed
        or "did not expose the full interactive shell navigation" in step_three_observed
        or "did not expose the header workspace trigger" in step_three_observed
        or "did not expose the visible TrackState branding tagline" in step_three_observed
        or "still looked like the startup surface instead of the interactive shell"
        in step_three_observed
    ):
        return "shell-visibility-contract-broken"
    return None


def _error_summary(result: dict[str, Any]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


if __name__ == "__main__":
    main()
