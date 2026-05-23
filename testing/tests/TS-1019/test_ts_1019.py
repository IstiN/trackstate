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
            }
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
MAX_READY_AFTER_RELEASE_SECONDS = 3.5
MIN_PENDING_SAMPLE_COUNT = 5
MIN_PENDING_OBSERVATION_SECONDS = 2.0
AUTH_PROBE_START_WAIT_SECONDS = 60
PENDING_WINDOW_WAIT_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + 6
SHELL_READY_WAIT_SECONDS = FULL_SYNC_TIMEOUT_SECONDS + 8
POLL_INTERVAL_SECONDS = 0.15
LINKED_BUG_KEYS = ("TS-1014",)
LINKED_BUG_NOTES = (
    "Reviewed TS-1014. Its deployed fix moved startup shell rendering behind the delayed "
    "GitHub `/user` successful-probe path, so this test waits through the real 5-second "
    "pending window before asserting the shell stays hidden and only becomes interactive "
    "after probe release."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1019_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1019_failure.png"

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

                auth_probe_started = runtime.wait_for_auth_probe_start(
                    timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                )
                if not auth_probe_started or runtime.auth_probe_started_at_monotonic is None:
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
                    result["pending_shell_window_observation"] = _pending_sample_payload(
                        pending_shell_window,
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
                result["pending_shell_sample_observed"] = pending_shell_sample_observed

                pending_window_duration_seconds = None
                if pending_shell_window is not None:
                    pending_window_duration_seconds = (
                        pending_shell_window["auth_probe_release_after_auth_start_seconds"]
                    )
                result["pending_window_duration_seconds"] = pending_window_duration_seconds

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Waited through the delayed `/user` startup probe window before "
                        "asserting the shell state.\n"
                        f"pending_shell_sample_observed={pending_shell_sample_observed!r}; "
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}"
                    ),
                )

                pending_observation_failures: list[str] = []
                if (
                    pending_shell_window is not None
                    and bool(pending_shell_window["auth_pending"])
                ):
                    if bool(pending_shell_window["shell_observation"]["shell_ready"]):
                        pending_observation_failures.append(
                            "The shell reported shell_ready during the pending startup window."
                        )
                    if pending_shell_window["trigger"] is not None:
                        pending_observation_failures.append(
                            "The top-bar workspace trigger was already visible during the "
                            "pending startup window."
                        )
                    if bool(pending_shell_window["branding_visible"]):
                        pending_observation_failures.append(
                            "The TrackState branding tagline was already visible during the "
                            "pending startup window."
                        )
                    if pending_shell_window["shell_observation"]["visible_navigation_labels"]:
                        pending_observation_failures.append(
                            "Sidebar navigation labels were already visible during the pending "
                            "startup window."
                        )
                if (
                    not pending_shell_sample_observed
                    and shell_window["probe_recorded_shell_ready_after_start_seconds"] is None
                ):
                    pending_observation_failures.append(
                        "The focused pending-window sampler did not capture an in-flight "
                        "startup sample and there was no page-side first shell-ready timestamp "
                        "to use as equivalent timing proof."
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

                if authoritative_shell_ready_after_start_seconds is None:
                    pending_observation_failures.append(
                        "The live run never produced an authoritative shell_ready "
                        "timestamp after launch."
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
                if (
                    authoritative_shell_ready_after_start_seconds is not None
                    and authoritative_shell_ready_after_start_seconds
                    >= FULL_SYNC_TIMEOUT_SECONDS
                ):
                    pending_observation_failures.append(
                        "The first authoritative shell_ready transition happened only after "
                        f"{authoritative_shell_ready_after_start_seconds!r} seconds, which is "
                        f"not before the full {FULL_SYNC_TIMEOUT_SECONDS}-second timeout."
                    )
                if (
                    authoritative_shell_ready_after_probe_release_seconds is not None
                    and authoritative_shell_ready_after_probe_release_seconds
                    > MAX_READY_AFTER_RELEASE_SECONDS
                ):
                    pending_observation_failures.append(
                        "The shell did not become interactive soon enough after the delayed "
                        f"probe completed (observed "
                        f"{authoritative_shell_ready_after_probe_release_seconds!r} seconds)."
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
                        f"pending_shell_sample_observed={pending_shell_sample_observed!r}; "
                        f"pending_window_duration_seconds={pending_window_duration_seconds!r}; "
                        f"pending_window_excerpt="
                        f"{_snippet((pending_shell_window or shell_window)['shell_observation']['body_text'])!r}; "
                        f"pending_trigger={(pending_shell_window or shell_window).get('trigger')!r}"
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


def _pending_shell_probe_script() -> str:
    return """
(() => {
  const state = {
    firstNavigationVisibleAtMs: null,
    firstTriggerVisibleAtMs: null,
    firstBrandingVisibleAtMs: null,
    firstAnyShellMarkerVisibleAtMs: null,
    firstTriggerLabel: '',
    firstNavigationLabels: [],
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

  const attachObserver = () => {
    observe();
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
        "* Delayed the live GitHub {/user} startup probe by 5 seconds and kept sampling the live page throughout that pending window instead of asserting immediately.",
        "* Verified the TopBar trigger, sidebar navigation labels, and branding tagline stayed hidden with no shell DOM markers while the probe was pending.",
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
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        f"- Ran the live deployed app at `{result.get('app_url')}` in {result.get('browser')} on {result.get('os')}.",
        f"- Used the required desktop viewport `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`.",
        f"- Delayed the live GitHub `/user` startup probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds and sampled the full pending window before asserting.",
        f"- Considered linked bug {', '.join(LINKED_BUG_KEYS)} and coupled the assertions to the delayed probe timing.",
        "- Checked the user-visible shell trigger, navigation, branding, and shell DOM markers during the pending window and after release.",
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
            "`/user` probe by 5 seconds and proves the deployed shell stays hidden during "
            "the pending window, then becomes interactive only after the probe resolves.\n\n"
            "The live pending samples showed no TopBar trigger, sidebar navigation, or "
            "branding, and the real shell appeared only after probe release.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        "Added a live Playwright startup regression that delays the initial GitHub "
        "`/user` probe by 5 seconds and checks whether the deployed shell stays hidden "
        "while startup synchronization is still pending.\n\n"
        f"{result.get('error', 'The deployed app did not keep the startup shell hidden during the pending probe window.')}\n"
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
        f"* GitHub requests seen: {{code}}{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}{{code}}",
        f"* Delayed requests seen: {{code}}{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}{{code}}",
        f"* Pending samples: {{code}}{json.dumps(result.get('pending_window_samples', []), ensure_ascii=True)}{{code}}",
        f"* Post-release sample: {{code}}{json.dumps(result.get('shell_window_observation'), ensure_ascii=True)}{{code}}",
    ]
    if result.get("screenshot"):
        lines.append(f"* Screenshot: {{code}}{result['screenshot']}{{code}}")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "During the delayed 5-second GitHub `/user` startup probe, the deployed app "
            "kept the TopBar trigger, sidebar navigation, and branding hidden with no shell "
            "DOM markers in the pending samples. After the probe resolved, the page reached "
            f"shell_ready in {result.get('authoritative_shell_ready_after_start_seconds')!r} "
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


if __name__ == "__main__":
    main()
