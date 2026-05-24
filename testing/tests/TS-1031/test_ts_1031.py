from __future__ import annotations

import json
import platform
import sys
import time
import traceback
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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
from testing.tests.support.ts984_delayed_auth_probe_runtime import (  # noqa: E402
    Ts984DelayedAuthProbeRuntime,
)


class Ts1031PendingShellProbeRuntime(Ts984DelayedAuthProbeRuntime):
    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "Ts1031PendingShellProbeRuntime expected a browser context and page.",
            )
        script = _pending_shell_probe_script()
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        return session

    def read_pending_shell_probe_state(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError(
                "Ts1031PendingShellProbeRuntime expected a browser page before reading state.",
            )
        payload = self._page.evaluate(
            """
            () => {
              const state = window.__ts1031PendingShellProbeState;
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

TICKET_KEY = "TS-1031"
TEST_CASE_TITLE = (
    "Startup sequence — GitHub authentication probe is triggered immediately after bootstrap"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1031/test_ts_1031.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1031-local"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SIMULATED_PROBE_DELAY_SECONDS = 5
AUTH_PROBE_START_WAIT_SECONDS = 60
STARTUP_RENDER_WAIT_SECONDS = 60
SHELL_READY_WAIT_SECONDS = 20
PENDING_WINDOW_WAIT_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + 8
POLL_INTERVAL_SECONDS = 0.15
MIN_PENDING_WINDOW_SECONDS = 4.5
MIN_PENDING_SAMPLE_COUNT = 5
MIN_PENDING_OBSERVATION_SECONDS = 2.0
PENDING_SAMPLE_WINDOW_TOLERANCE_SECONDS = 0.25
LINKED_BUGS = ["TS-1027", "TS-1029"]
LINKED_BUG_NOTES = (
    "Reviewed TS-1027 and TS-1029. Their merged startup fixes depend on the live "
    "GitHub `/user` auth probe actually starting, so this test delays that probe by "
    "5 seconds, waits long enough to observe the pending window, and only passes when "
    "the deployed app exits the loading surface after the delayed probe is released."
)

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Monitor network traffic or the authentication service hooks during the initial loading window.",
    "Verify that a request to the GitHub /user endpoint is dispatched immediately after the bootstrap logic completes.",
]
EXPECTED_RESULT = (
    "The application explicitly triggers the GitHub API probe and the request remains "
    "in a pending state for the configured 5-second window, confirming the "
    "initialization sequence is no longer stuck in the bootstrap phase."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1031_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1031_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1031 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts1031PendingShellProbeRuntime(
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
        "linked_bugs": LINKED_BUGS,
        "linked_bug_notes": LINKED_BUG_NOTES,
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
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
            startup_started_at_monotonic = time.monotonic()

            tracker_page.open_entrypoint(wait_until="commit", timeout_ms=120_000)
            result["startup_observation_initial"] = startup_surface_payload(tracker_page)

            startup_rendered, startup_surface = poll_until(
                probe=lambda: startup_surface_payload(tracker_page),
                is_satisfied=_startup_surface_loaded,
                timeout_seconds=STARTUP_RENDER_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["startup_observation_after_render"] = startup_surface
            if not startup_rendered:
                observed = (
                    "The deployed app never rendered beyond the bare startup title before "
                    "the delayed-auth startup probe scenario could be observed.\n"
                    f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}"
                )
                result["product_failure"] = True
                record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=observed,
                )
                record_not_reached_steps(
                    result,
                    starting_step=2,
                    request_steps=REQUEST_STEPS,
                )
                raise AssertionError(f"Step 1 failed: {observed}")

            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app in Chromium with a stored GitHub "
                    "token, an active local workspace profile, a hosted fallback "
                    "workspace profile, and a 5-second delay on the live GitHub `/user` "
                    "startup probe."
                ),
            )

            auth_probe_started = runtime.wait_for_auth_probe_start(
                timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
            )
            github_request_paths = [
                _request_path(url) for url in runtime.github_request_urls if _request_path(url)
            ]
            delayed_request_paths = [
                _request_path(url) for url in runtime.delayed_request_urls if _request_path(url)
            ]
            auth_probe_started_after_start_seconds = relative_startup_event_seconds(
                startup_started_at_monotonic,
                runtime.auth_probe_started_at_monotonic,
            )
            result["github_request_urls"] = list(runtime.github_request_urls)
            result["github_request_paths"] = github_request_paths
            result["delayed_request_urls"] = list(runtime.delayed_request_urls)
            result["delayed_request_paths"] = delayed_request_paths
            result["auth_probe_started_after_start_seconds"] = (
                auth_probe_started_after_start_seconds
            )

            if not auth_probe_started or runtime.auth_probe_started_at_monotonic is None:
                observed = (
                    "The live app never started the delayed GitHub `/user` startup auth "
                    "probe during the initial loading window, so the bootstrap exit path "
                    "could not be verified.\n"
                    f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}\n"
                    f"GitHub requests seen:\n{json.dumps(result['github_request_urls'], indent=2)}\n"
                    f"Delayed requests seen:\n{json.dumps(result['delayed_request_urls'], indent=2)}\n"
                    f"Observed body text:\n{tracker_page.body_text()}"
                )
                result["product_failure"] = True
                record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=observed,
                )
                record_not_reached_steps(
                    result,
                    starting_step=3,
                    request_steps=REQUEST_STEPS,
                )
                raise AssertionError(f"Step 2 failed: {observed}")

            record_step(
                result,
                step=2,
                status="passed",
                action=REQUEST_STEPS[1],
                observed=(
                    "Captured the live startup network activity and observed the delayed "
                    "GitHub `/user` auth probe begin during the initial loading window.\n"
                    f"auth_probe_started_after_start_seconds="
                    f"{auth_probe_started_after_start_seconds!r}; "
                    f"github_request_paths={github_request_paths!r}; "
                    f"delayed_request_paths={delayed_request_paths!r}"
                ),
            )

            transition_tracker = ShellReadyTransitionTracker()
            runtime.wait_for_auth_probe_release(
                timeout_seconds=PENDING_WINDOW_WAIT_SECONDS,
            )
            shell_ready, final_observation = poll_until(
                probe=lambda: _observe_startup_window(
                    tracker_page=tracker_page,
                    switcher_page=switcher_page,
                    runtime=runtime,
                    startup_started_at_monotonic=startup_started_at_monotonic,
                    transition_tracker=transition_tracker,
                ),
                is_satisfied=lambda observation: (
                    bool(observation["shell_observation"]["shell_ready"])
                    and observation["trigger"] is not None
                    and not bool(observation["auth_pending"])
                ),
                timeout_seconds=SHELL_READY_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["shell_window_observation"] = _window_payload(final_observation)
            result["shell_probe_state"] = final_observation.get("shell_probe_state")

            pending_probe_state = final_observation["pending_shell_probe_state"]
            auth_probe_released_after_start_seconds = final_observation[
                "auth_probe_released_after_start_seconds"
            ]
            pending_samples = _pending_window_samples_from_probe_state(
                pending_probe_state=pending_probe_state,
                auth_probe_started_after_start_seconds=auth_probe_started_after_start_seconds,
                auth_probe_released_after_start_seconds=auth_probe_released_after_start_seconds,
            )
            pending_window_sampled_duration_seconds = _pending_window_duration_seconds(
                pending_samples,
            )
            pending_window_duration_seconds = pending_window_sampled_duration_seconds
            if pending_window_duration_seconds is None:
                pending_window_duration_seconds = final_observation.get(
                    "auth_probe_release_after_auth_start_seconds",
                )

            result["pending_shell_probe_state"] = pending_probe_state
            result["pending_window_samples"] = _sampled_pending_window_payloads(
                pending_samples,
            )
            result["pending_window_pending_sample_count"] = len(pending_samples)
            result["pending_window_sampled_duration_seconds"] = (
                pending_window_sampled_duration_seconds
            )
            result["pending_window_duration_seconds"] = pending_window_duration_seconds
            result["pending_shell_window_observation"] = (
                _pending_sample_payload(pending_samples[-1]) if pending_samples else None
            )

            authoritative_shell_ready_after_start_seconds = (
                _authoritative_shell_ready_after_start_seconds(final_observation)
            )
            authoritative_shell_ready_after_probe_release_seconds = (
                _authoritative_shell_ready_after_probe_release_seconds(final_observation)
            )
            result["authoritative_shell_ready_after_start_seconds"] = (
                authoritative_shell_ready_after_start_seconds
            )
            result["authoritative_shell_ready_after_probe_release_seconds"] = (
                authoritative_shell_ready_after_probe_release_seconds
            )

            pending_failures: list[str] = []
            pending_failures.extend(
                _pending_sample_coverage_failures(
                    pending_samples=pending_samples,
                    pending_window_sampled_duration_seconds=pending_window_sampled_duration_seconds,
                ),
            )
            pending_failures.extend(
                _pending_state_failures(
                    pending_samples=pending_samples,
                    pending_probe_state=pending_probe_state,
                    auth_probe_released_after_start_seconds=auth_probe_released_after_start_seconds,
                    shell_ready_observed_while_auth_pending=bool(
                        final_observation["shell_ready_observed_while_auth_pending"],
                    ),
                ),
            )
            pending_failures.extend(
                _pending_probe_state_coverage_failures(
                    pending_probe_state=pending_probe_state,
                    post_release_observation=final_observation,
                ),
            )
            if not delayed_request_paths:
                pending_failures.append(
                    "No delayed GitHub `/user` request was captured even though the "
                    "auth probe wait completed."
                )
            if auth_probe_started_after_start_seconds is None:
                pending_failures.append(
                    "The startup auth probe start time was never recorded."
                )
            elif authoritative_shell_ready_after_start_seconds is not None and (
                auth_probe_started_after_start_seconds
                >= authoritative_shell_ready_after_start_seconds
            ):
                pending_failures.append(
                    "The GitHub `/user` startup probe did not begin until after the "
                    "shell was already interactive."
                )
            if github_request_paths and "/user" not in github_request_paths:
                pending_failures.append(
                    "The startup GitHub traffic never included the required `/user` "
                    f"probe. github_request_paths={github_request_paths!r}"
                )
            if not shell_ready:
                pending_failures.append(
                    "The interactive shell never became ready after the delayed `/user` "
                    "probe was released."
                )
            else:
                try:
                    _assert_interactive_shell(final_observation)
                except AssertionError as error:
                    pending_failures.append(str(error))

            if pending_failures:
                observed = (
                    "The deployed startup flow did not expose the expected startup auth "
                    "probe behavior or did not exit the loading surface correctly.\n"
                    f"auth_probe_started_after_start_seconds="
                    f"{auth_probe_started_after_start_seconds!r}; "
                    f"auth_probe_released_after_start_seconds="
                    f"{auth_probe_released_after_start_seconds!r}; "
                    f"github_request_paths={github_request_paths!r}; "
                    f"delayed_request_paths={delayed_request_paths!r}; "
                    f"pending_sample_count={len(pending_samples)!r}; "
                    f"pending_window_duration_seconds={pending_window_duration_seconds!r}; "
                    f"authoritative_shell_ready_after_start_seconds="
                    f"{authoritative_shell_ready_after_start_seconds!r}; "
                    f"authoritative_shell_ready_after_probe_release_seconds="
                    f"{authoritative_shell_ready_after_probe_release_seconds!r}; "
                    f"shell_probe_state={json.dumps(final_observation.get('shell_probe_state'), ensure_ascii=True)}\n"
                    + "\n".join(pending_failures)
                )
                result["product_failure"] = True
                record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=observed,
                )
                raise AssertionError(f"Step 3 failed: {observed}")

            record_step(
                result,
                step=3,
                status="passed",
                action=REQUEST_STEPS[2],
                observed=(
                    "The delayed GitHub `/user` auth probe started during the initial "
                    "loading window, stayed pending through the configured observation "
                    "window, and the deployed app then rendered the interactive shell "
                    "instead of remaining stuck on the loading surface.\n"
                    f"auth_probe_started_after_start_seconds="
                    f"{auth_probe_started_after_start_seconds!r}; "
                    f"pending_sample_count={len(pending_samples)!r}; "
                    f"pending_window_duration_seconds={pending_window_duration_seconds!r}; "
                    f"shell_ready_after_launch_seconds="
                    f"{authoritative_shell_ready_after_start_seconds!r}"
                ),
            )

            first_pending = pending_samples[0] if pending_samples else final_observation
            record_human_verification(
                result,
                check=(
                    "Watched the startup screen like a user during the delayed `/user` "
                    "probe and checked whether the app stayed on the loading surface."
                ),
                observed=(
                    f"body_excerpt="
                    f"{snippet(str(first_pending['startup_observation']['body_text']))!r}; "
                    f"visible_navigation_labels="
                    f"{first_pending['shell_observation']['visible_navigation_labels']!r}; "
                    f"trigger_visible={first_pending['trigger'] is not None!r}; "
                    f"branding_visible={first_pending['branding_visible']!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Viewed the page again after the delayed probe released and verified "
                    "the user-visible shell became interactive."
                ),
                observed=(
                    f"visible_navigation_labels="
                    f"{final_observation['shell_observation']['visible_navigation_labels']!r}; "
                    f"trigger_label="
                    f"{(final_observation['trigger'] or {}).get('semantic_label')!r}; "
                    f"branding_visible={final_observation['branding_visible']!r}; "
                    f"body_excerpt="
                    f"{snippet(str(final_observation['shell_observation']['body_text']))!r}"
                ),
            )

            tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
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
        _write_failure_outputs(result)
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
        marker_filename=".trackstate-ts1031-precondition.txt",
        marker_contents="Prepared for TS-1031 startup auth probe validation.\n",
        commit_author_name="TS-1031 Automation",
        commit_author_email="ts1031@example.com",
        commit_message="Prepare TS-1031 local workspace",
    )


def _startup_surface_loaded(observation: dict[str, Any]) -> bool:
    body_text = str(observation.get("body_text", "")).strip()
    title = str(observation.get("title", "")).strip()
    button_labels = observation.get("button_labels", [])
    return bool(button_labels) or (len(body_text) > len(title) and body_text != title)


def _observe_startup_window(
    *,
    tracker_page: TrackStateTrackerPage,
    switcher_page: LiveWorkspaceSwitcherPage,
    runtime: Ts1031PendingShellProbeRuntime,
    startup_started_at_monotonic: float,
    transition_tracker: ShellReadyTransitionTracker,
) -> dict[str, Any]:
    observation = observe_live_startup_shell_window(
        tracker_page=tracker_page,
        page=switcher_page,
        runtime=runtime,
        startup_started_at_monotonic=startup_started_at_monotonic,
        shell_navigation_labels=SHELL_NAVIGATION_LABELS,
        branding_texts=(BRANDING_TEXT, "TrackState.AI"),
        transition_tracker=transition_tracker,
        poll_timeout_ms=250,
    )
    observation["shell_probe_state"] = runtime.read_shell_probe_state()
    observation["pending_shell_probe_state"] = runtime.read_pending_shell_probe_state()
    observation["dom_markers"] = _shell_dom_markers(tracker_page)
    return observation


def _window_payload(observation: dict[str, Any]) -> dict[str, Any]:
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
        "auth_probe_release_after_auth_start_seconds": observation.get(
            "auth_probe_release_after_auth_start_seconds",
        ),
        "elapsed_since_auth_start_seconds": observation.get(
            "elapsed_since_auth_start_seconds",
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
        "pending_shell_probe_state": observation.get("pending_shell_probe_state"),
        "dom_markers": observation.get("dom_markers"),
    }


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
  window.__ts1031PendingShellProbeState = state;

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
    if not isinstance(first_elapsed, (int, float)) or not isinstance(
        last_elapsed,
        (int, float),
    ):
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
            "The page-side pending-window sampler did not capture enough in-flight "
            "samples to prove the app was observed while the delayed `/user` probe was "
            f"still pending. Expected at least {MIN_PENDING_SAMPLE_COUNT} samples but "
            f"captured {len(pending_samples)}."
        )
    if (
        pending_window_sampled_duration_seconds is None
        or pending_window_sampled_duration_seconds < MIN_PENDING_OBSERVATION_SECONDS
    ):
        failures.append(
            "The page-side pending-window sampler did not observe the delayed startup "
            "probe for long enough to count as meaningful live inspection. Expected at "
            f"least {MIN_PENDING_OBSERVATION_SECONDS} seconds of coverage but captured "
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
                "elapsed_since_start_seconds": round(
                    float(observed_after_launch_seconds),
                    2,
                ),
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
            "Sidebar navigation labels became visible during the delayed startup "
            "window.\n"
            f"Observed sample:\n{json.dumps(_pending_sample_payload(first_visible_navigation), indent=2)}"
        )
    first_visible_trigger = next(
        (sample for sample in pending_samples if sample["trigger"] is not None),
        None,
    )
    if first_visible_trigger is not None:
        failures.append(
            "The top-bar workspace trigger became visible during the delayed startup "
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
            "Shell DOM markers were already mounted during the delayed startup "
            "window.\n"
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
        "body_excerpt": snippet(str(shell.get("body_text", ""))),
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
    authoritative_after_start = _authoritative_shell_ready_after_start_seconds(
        observation,
    )
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
    candidate_indexes = [
        0,
        1,
        2,
        len(pending_samples) // 2,
        len(pending_samples) - 3,
        len(pending_samples) - 2,
        len(pending_samples) - 1,
    ]
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
        and pending_probe_state.get("first_navigation_visible_after_launch_seconds")
        is None
    ):
        failures.append(
            "The page-side pending-shell observer never recorded when navigation first "
            "appeared, even though the post-release shell snapshot showed navigation.\n"
            f"pending_probe_state={json.dumps(pending_probe_state, indent=2)}"
        )
    if (
        post_release_observation["trigger"] is not None
        and pending_probe_state.get("first_trigger_visible_after_launch_seconds")
        is None
    ):
        failures.append(
            "The page-side pending-shell observer never recorded when the top-bar "
            "trigger first appeared, even though the post-release shell snapshot showed "
            f"it.\npending_probe_state={json.dumps(pending_probe_state, indent=2)}"
        )
    if (
        bool(post_release_observation["branding_visible"])
        and pending_probe_state.get("first_branding_visible_after_launch_seconds")
        is None
    ):
        failures.append(
            "The page-side pending-shell observer never recorded when branding first "
            "appeared, even though the post-release shell snapshot showed it.\n"
            f"pending_probe_state={json.dumps(pending_probe_state, indent=2)}"
        )
    return failures


def _assert_interactive_shell(observation: dict[str, Any]) -> None:
    shell = observation["shell_observation"]
    missing_navigation = [
        label
        for label in SHELL_NAVIGATION_LABELS
        if label not in shell["visible_navigation_labels"]
    ]
    if missing_navigation:
        raise AssertionError(
            "The post-release shell did not expose the full interactive navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell window:\n{json.dumps(_window_payload(observation), indent=2)}"
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "The post-release shell did not expose the workspace switcher trigger needed "
            "to prove the top bar became interactive.\n"
            f"Observed shell window:\n{json.dumps(_window_payload(observation), indent=2)}"
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "The post-release shell did not expose the visible TrackState branding "
            "tagline.\n"
            f"Observed shell window:\n{json.dumps(_window_payload(observation), indent=2)}"
        )


def _request_path(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path.rstrip("/") or "/"


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
        "* Preloaded an active local workspace plus hosted fallback workspace for the deployed app.",
        "* Delayed the live GitHub {/user} startup probe by 5 seconds and monitored the same browser session during the initial loading window.",
        "* Verified the {/user} request was dispatched promptly, stayed pending long enough to observe, and the app later rendered the interactive shell.",
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
        "testing/tests/TS-1031/test_ts_1031.py",
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
        "## What was automated",
        "- Preloaded an active local workspace plus hosted fallback workspace in the deployed app.",
        "- Delayed the live GitHub `/user` startup probe by 5 seconds and monitored the initial loading window in Chromium.",
        "- Required the `/user` request to begin promptly, remain pending long enough to observe, and then allow the user-visible shell to appear.",
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
            "The live run started the delayed GitHub `/user` startup probe promptly, "
            "kept it pending for the configured observation window, and then rendered "
            "the interactive shell instead of remaining stuck on the loading surface.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{result.get('error', 'The deployed app did not expose the expected startup auth probe behavior.')}\n"
    )


def _should_write_bug_description(result: dict[str, Any]) -> bool:
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
        f"- Delayed auth probe: GitHub `/user` delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Pending window samples: `{json.dumps(result.get('pending_window_samples', []), ensure_ascii=True)}`",
        f"- Final shell observation: `{json.dumps(result.get('shell_window_observation'), ensure_ascii=True)}`",
        f"- Shell probe state: `{json.dumps(result.get('shell_probe_state'), ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "The deployed app issued the GitHub `/user` startup probe "
            f"{result.get('auth_probe_started_after_start_seconds')!r} seconds after "
            f"launch, kept it pending for "
            f"{(result.get('shell_window_observation') or {}).get('auth_probe_release_after_auth_start_seconds')!r} "
            "seconds, and then exposed the interactive shell."
        )
    return str(result.get("error", "The deployed startup flow did not match the expected result."))


if __name__ == "__main__":
    main()
