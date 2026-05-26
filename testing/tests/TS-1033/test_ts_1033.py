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
    record_step,
    relative_startup_event_seconds,
    snippet,
    startup_surface_payload,
    write_test_automation_result,
)
from testing.tests.support.ts984_delayed_auth_probe_runtime import (  # noqa: E402
    Ts984DelayedAuthProbeRuntime,
)

TICKET_KEY = "TS-1033"
TEST_CASE_TITLE = (
    "Startup with cached session — bootstrap sequence does not bypass "
    "authentication probe"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1033/test_ts_1033.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1033-local"
LOCAL_DISPLAY_NAME = "Fallback local workspace"
HOSTED_DISPLAY_NAME = "Cached hosted workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
SIMULATED_PROBE_DELAY_SECONDS = 5
AUTH_PROBE_START_WAIT_SECONDS = 60
STARTUP_RENDER_WAIT_SECONDS = 60
PENDING_WINDOW_WAIT_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + 8
SHELL_READY_WAIT_SECONDS = 25
POLL_INTERVAL_SECONDS = 0.2
MIN_PENDING_WINDOW_SECONDS = 4.5
MAX_PENDING_WINDOW_SECONDS = SIMULATED_PROBE_DELAY_SECONDS + 1.5
MIN_PENDING_SAMPLE_COUNT = 5
SHELL_MARKER_TOLERANCE_SECONDS = 0.25
LINKED_BUGS = ["TS-1029"]
LINKED_BUG_NOTES = (
    "Reviewed TS-1029. Its merged startup fix depends on the delayed GitHub "
    "`/user` probe actually beginning, so this test seeds a cached hosted "
    "session, delays that probe by 5 seconds, and waits long enough to confirm "
    "the live app still starts the network verification during bootstrap."
)

REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Open the network inspection tool.",
    "Monitor network traffic during the initial bootstrap sequence.",
    "Observe the application initialization lifecycle.",
]
EXPECTED_RESULT = (
    "A network request to the GitHub /user endpoint is dispatched immediately "
    "during the bootstrap phase despite the presence of a cached session, "
    "confirming the probe is treated as a mandatory task."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1033_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1033_failure.png"


class Ts1033CachedSessionProbeRuntime(Ts984DelayedAuthProbeRuntime):
    def __enter__(self):
        session = super().__enter__()
        if self._context is None or self._page is None:
            raise RuntimeError(
                "Ts1033CachedSessionProbeRuntime expected a browser context and page.",
            )
        script = _pending_shell_probe_script()
        self._context.add_init_script(script=script)
        self._page.add_init_script(script=script)
        return session

    def read_pending_shell_probe_state(self) -> dict[str, Any]:
        if self._page is None:
            raise RuntimeError(
                "Ts1033CachedSessionProbeRuntime expected a browser page before reading state.",
            )
        payload = self._page.evaluate(
            """
            () => {
              const state = window.__ts1033PendingShellProbeState;
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


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1033 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    hosted_workspace_id = _hosted_workspace_id(service.repository)
    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    runtime = Ts1033CachedSessionProbeRuntime(
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
        "simulated_probe_delay_seconds": SIMULATED_PROBE_DELAY_SECONDS,
        "preloaded_workspace_state": workspace_state,
        "prepared_local_workspace": prepared_local_workspace,
        "cached_hosted_workspace_id": hosted_workspace_id,
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
            startup_rendered, startup_surface = poll_until(
                probe=lambda: startup_surface_payload(tracker_page),
                is_satisfied=_startup_surface_loaded,
                timeout_seconds=STARTUP_RENDER_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["startup_observation_initial"] = startup_surface_payload(tracker_page)
            result["startup_observation_after_render"] = startup_surface
            if not startup_rendered:
                observed = (
                    "The deployed app never rendered beyond the bare startup title before "
                    "the cached-session startup scenario could be inspected.\n"
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
                _record_missing_steps(result, starting_step=2)
                raise AssertionError(f"Step 1 failed: {observed}")

            cached_session_state = _read_cached_session_state(
                tracker_page=tracker_page,
                repository=service.repository,
                hosted_workspace_id=hosted_workspace_id,
            )
            result["cached_session_state"] = cached_session_state
            if not _has_cached_hosted_session(
                cached_session_state,
                hosted_workspace_id=hosted_workspace_id,
            ):
                raise RuntimeError(
                    "TS-1033 setup failed: the browser did not expose the expected cached "
                    "hosted session state before bootstrap.\n"
                    f"Observed cached session state:\n{json.dumps(cached_session_state, indent=2)}"
                )

            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app in Chromium with a cached hosted "
                    "workspace selected and stored GitHub token state already seeded in "
                    "browser storage.\n"
                    f"cached_session_state={json.dumps(cached_session_state, ensure_ascii=True)}"
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
            result["delayed_request_timings"] = _relative_delayed_request_timings(
                delayed_request_timings=runtime.delayed_request_timings,
                startup_started_at_monotonic=startup_started_at_monotonic,
            )
            result["auth_probe_started_after_start_seconds"] = (
                auth_probe_started_after_start_seconds
            )

            if result["github_request_urls"]:
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Playwright network interception captured bootstrap GitHub traffic "
                        "for the live session.\n"
                        f"github_request_paths={github_request_paths!r}; "
                        f"delayed_request_paths={delayed_request_paths!r}"
                    ),
                )
            else:
                observed = (
                    "The network inspection hook never captured any GitHub API traffic "
                    "during bootstrap, so the cached-session verification path could not "
                    "be observed.\n"
                    f"Observed startup surface:\n{json.dumps(startup_surface, indent=2)}\n"
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

            first_auth_probe_released = (
                runtime.wait_for_first_auth_probe_release(
                    timeout_seconds=PENDING_WINDOW_WAIT_SECONDS,
                )
                if auth_probe_started
                else False
            )
            transition_tracker = ShellReadyTransitionTracker()
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
                ),
                timeout_seconds=SHELL_READY_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["shell_window_observation"] = _window_payload(final_observation)
            result["shell_probe_state"] = final_observation.get("shell_probe_state")
            result["pending_shell_probe_state"] = final_observation.get(
                "pending_shell_probe_state",
            )
            result["first_auth_probe_released_after_start_seconds"] = (
                relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    runtime.first_auth_probe_released_at_monotonic,
                )
            )
            result["first_auth_probe_pending_duration_seconds"] = _first_probe_duration_seconds(
                result.get("delayed_request_timings", []),
            )
            result["authoritative_shell_ready_after_start_seconds"] = (
                _authoritative_shell_ready_after_start_seconds(final_observation)
            )
            result["first_shell_marker_after_start_seconds"] = (
                _earliest_shell_marker_after_start_seconds(
                    result["pending_shell_probe_state"],
                )
            )

            bootstrap_failures = _bootstrap_failures(
                result=result,
                auth_probe_started=auth_probe_started,
                first_auth_probe_released=first_auth_probe_released,
            )
            if bootstrap_failures:
                result["product_failure"] = True
                record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed="\n".join(bootstrap_failures),
                )
            else:
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The delayed GitHub `/user` request began during bootstrap before "
                        "the cached session could carry the app into visible shell state.\n"
                        f"auth_probe_started_after_start_seconds="
                        f"{result['auth_probe_started_after_start_seconds']!r}; "
                        f"first_shell_marker_after_start_seconds="
                        f"{result['first_shell_marker_after_start_seconds']!r}; "
                        f"first_auth_probe_pending_duration_seconds="
                        f"{result['first_auth_probe_pending_duration_seconds']!r}; "
                        f"sample_count="
                        f"{result['pending_shell_probe_state'].get('sample_count')!r}"
                    ),
                )

            lifecycle_failures = _lifecycle_failures(
                shell_ready=shell_ready,
                observation=final_observation,
            )
            if lifecycle_failures:
                result["product_failure"] = True
                record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed="\n".join(lifecycle_failures),
                )
            else:
                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "After the delayed `/user` probe released, the cached-session "
                        "startup flow rendered the interactive shell instead of bypassing "
                        "verification or remaining stuck on the startup surface.\n"
                        f"shell_ready_after_start_seconds="
                        f"{result['authoritative_shell_ready_after_start_seconds']!r}; "
                        f"trigger_label="
                        f"{(final_observation['trigger'] or {}).get('semantic_label')!r}; "
                        f"visible_navigation_labels="
                        f"{final_observation['shell_observation']['visible_navigation_labels']!r}"
                    ),
                )

            pending_state = result["pending_shell_probe_state"]
            record_human_verification(
                result,
                check=(
                    "Viewed the startup experience like a user while the delayed `/user` "
                    "verification was still pending."
                ),
                observed=(
                    f"body_excerpt={snippet(str(startup_surface.get('body_text', '')))!r}; "
                    f"first_navigation_labels={pending_state.get('first_navigation_labels')!r}; "
                    f"first_trigger_label={pending_state.get('first_trigger_label')!r}; "
                    f"sample_count={pending_state.get('sample_count')!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Viewed the screen again after startup completed and verified the "
                    "visible desktop shell state."
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

            if bootstrap_failures or lifecycle_failures or len(result["steps"]) < 4:
                raise AssertionError(
                    "\n".join(
                        [
                            *bootstrap_failures,
                            *lifecycle_failures,
                            *(
                                []
                                if len(result["steps"]) >= 4
                                else ["The run did not record all requested step outcomes."]
                            ),
                        ],
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
        active_workspace="hosted",
    )


def _prepare_local_workspace_repository() -> dict[str, object]:
    return prepare_local_workspace_repository(
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        marker_filename=".trackstate-ts1033-precondition.txt",
        marker_contents="Prepared for TS-1033 cached-session startup validation.\n",
        commit_author_name="TS-1033 Automation",
        commit_author_email="ts1033@example.com",
        commit_message="Prepare TS-1033 local workspace",
    )


def _hosted_workspace_id(repository: str) -> str:
    return f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"


def _startup_surface_loaded(observation: dict[str, Any]) -> bool:
    body_text = str(observation.get("body_text", "")).strip()
    title = str(observation.get("title", "")).strip()
    button_labels = observation.get("button_labels", [])
    return bool(button_labels) or (len(body_text) > len(title) and body_text != title)


def _observe_startup_window(
    *,
    tracker_page: TrackStateTrackerPage,
    switcher_page: LiveWorkspaceSwitcherPage,
    runtime: Ts1033CachedSessionProbeRuntime,
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
        "shell_ready_after_start_seconds": observation.get("shell_ready_after_start_seconds"),
        "shell_probe_state": observation.get("shell_probe_state"),
        "pending_shell_probe_state": observation.get("pending_shell_probe_state"),
    }


def _read_cached_session_state(
    *,
    tracker_page: TrackStateTrackerPage,
    repository: str,
    hosted_workspace_id: str,
) -> dict[str, Any]:
    payload = tracker_page.session.evaluate(
        """
        ({ repository, hostedWorkspaceId }) => {
          const repoKeys = [
            repository.replace('/', '.'),
            repository.toLowerCase().replace('/', '.'),
          ];
          const stateKeys = [
            'trackstate.workspaceProfiles.state',
            'flutter.trackstate.workspaceProfiles.state',
          ];
          const parseState = () => {
            for (const key of stateKeys) {
              const raw = window.localStorage.getItem(key);
              if (!raw) {
                continue;
              }
              try {
                return JSON.parse(raw);
              } catch (_) {
                return { parseError: true, raw };
              }
            }
            return null;
          };
          const repositoryTokenKeys = repoKeys.flatMap((value) => [
            `trackstate.githubToken.${value}`,
            `flutter.trackstate.githubToken.${value}`,
          ]);
          const encodedWorkspaceId = encodeURIComponent(hostedWorkspaceId);
          const workspaceTokenKeys = [
            `trackstate.githubToken.workspace.${encodedWorkspaceId}`,
            `flutter.trackstate.githubToken.workspace.${encodedWorkspaceId}`,
          ];
          const workspaceState = parseState();
          const profiles = Array.isArray(workspaceState?.profiles)
            ? workspaceState.profiles
                .filter((entry) => entry && typeof entry === 'object')
                .map((entry) => String(entry.id ?? ''))
                .filter((value) => value.length > 0)
            : [];
          return {
            repositoryTokenKeysPresent: repositoryTokenKeys.filter((key) => !!window.localStorage.getItem(key)),
            workspaceTokenKeysPresent: workspaceTokenKeys.filter((key) => !!window.localStorage.getItem(key)),
            activeWorkspaceId: workspaceState?.activeWorkspaceId ?? null,
            profileIds: profiles,
            workspaceState,
          };
        }
        """,
        arg={"repository": repository, "hostedWorkspaceId": hosted_workspace_id},
    )
    if not isinstance(payload, dict):
        return {
            "repository_token_keys_present": [],
            "workspace_token_keys_present": [],
            "active_workspace_id": None,
            "profile_ids": [],
            "workspace_state": None,
        }
    return {
        "repository_token_keys_present": [
            str(value) for value in payload.get("repositoryTokenKeysPresent", [])
        ],
        "workspace_token_keys_present": [
            str(value) for value in payload.get("workspaceTokenKeysPresent", [])
        ],
        "active_workspace_id": payload.get("activeWorkspaceId"),
        "profile_ids": [str(value) for value in payload.get("profileIds", [])],
        "workspace_state": payload.get("workspaceState"),
    }


def _has_cached_hosted_session(
    cached_session_state: dict[str, Any],
    *,
    hosted_workspace_id: str,
) -> bool:
    token_present = bool(cached_session_state.get("repository_token_keys_present")) or bool(
        cached_session_state.get("workspace_token_keys_present"),
    )
    profile_ids = cached_session_state.get("profile_ids", [])
    return (
        token_present
        and cached_session_state.get("active_workspace_id") == hosted_workspace_id
        and isinstance(profile_ids, list)
        and hosted_workspace_id in profile_ids
    )


def _bootstrap_failures(
    *,
    result: dict[str, Any],
    auth_probe_started: bool,
    first_auth_probe_released: bool,
) -> list[str]:
    github_request_paths = result.get("github_request_paths", [])
    delayed_request_paths = result.get("delayed_request_paths", [])
    auth_probe_started_after_start_seconds = result.get(
        "auth_probe_started_after_start_seconds",
    )
    first_shell_marker_after_start_seconds = result.get(
        "first_shell_marker_after_start_seconds",
    )
    pending_probe_state = result.get("pending_shell_probe_state", {})
    first_probe_duration_seconds = result.get("first_auth_probe_pending_duration_seconds")
    authoritative_shell_ready_after_start_seconds = result.get(
        "authoritative_shell_ready_after_start_seconds",
    )

    failures: list[str] = []
    if not auth_probe_started:
        failures.append(
            "The live app never started the delayed GitHub `/user` startup auth probe "
            "within the bootstrap observation window.\n"
            f"GitHub requests seen: {json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}\n"
            f"Delayed requests seen: {json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}"
        )
        return failures

    if github_request_paths and "/user" not in github_request_paths:
        failures.append(
            "The monitored startup traffic never included the required GitHub `/user` "
            f"probe. github_request_paths={github_request_paths!r}"
        )
    if not delayed_request_paths or "/user" not in delayed_request_paths:
        failures.append(
            "The delayed startup request set never included `/user`, so the cached-session "
            "auth verification was not the request being observed.\n"
            f"delayed_request_paths={delayed_request_paths!r}"
        )
    if not first_auth_probe_released:
        failures.append(
            "The first delayed GitHub `/user` startup probe never released within the "
            "configured observation window."
        )
    if not isinstance(first_probe_duration_seconds, (int, float)):
        failures.append("The first delayed GitHub `/user` probe duration was not measured.")
    elif first_probe_duration_seconds < MIN_PENDING_WINDOW_SECONDS:
        failures.append(
            "The first delayed GitHub `/user` startup probe did not remain pending long "
            "enough to prove live bootstrap observation.\n"
            f"Measured duration={first_probe_duration_seconds!r} seconds."
        )
    elif first_probe_duration_seconds > MAX_PENDING_WINDOW_SECONDS:
        failures.append(
            "The first delayed GitHub `/user` startup probe stayed pending much longer "
            "than the configured 5-second window, suggesting the run did not isolate "
            "the initial bootstrap probe.\n"
            f"Measured duration={first_probe_duration_seconds!r} seconds."
        )

    sample_count = pending_probe_state.get("sample_count")
    if not isinstance(sample_count, int) or sample_count < MIN_PENDING_SAMPLE_COUNT:
        failures.append(
            "The page-side bootstrap observer did not capture enough pending samples "
            "while the delayed `/user` probe was in flight.\n"
            f"sample_count={sample_count!r}"
        )
    if not isinstance(auth_probe_started_after_start_seconds, (int, float)):
        failures.append("The startup auth probe start time was never recorded.")
    if isinstance(first_shell_marker_after_start_seconds, (int, float)) and isinstance(
        auth_probe_started_after_start_seconds,
        (int, float),
    ) and auth_probe_started_after_start_seconds > (
        first_shell_marker_after_start_seconds + SHELL_MARKER_TOLERANCE_SECONDS
    ):
        failures.append(
            "The cached hosted session exposed visible shell markers before the GitHub "
            "`/user` startup probe began, so bootstrap bypassed mandatory network "
            "verification.\n"
            f"auth_probe_started_after_start_seconds={auth_probe_started_after_start_seconds!r}; "
            f"first_shell_marker_after_start_seconds={first_shell_marker_after_start_seconds!r}"
        )
    if isinstance(authoritative_shell_ready_after_start_seconds, (int, float)) and isinstance(
        auth_probe_started_after_start_seconds,
        (int, float),
    ) and auth_probe_started_after_start_seconds >= authoritative_shell_ready_after_start_seconds:
        failures.append(
            "The GitHub `/user` startup probe did not begin until after the shell was "
            "already interactive."
        )
    return failures


def _lifecycle_failures(
    *,
    shell_ready: bool,
    observation: dict[str, Any],
) -> list[str]:
    failures: list[str] = []
    if not shell_ready:
        failures.append(
            "The interactive shell never became ready after the cached-session startup "
            "probe observation window.\n"
            f"Observed shell window:\n{json.dumps(_window_payload(observation), indent=2)}"
        )
        return failures
    try:
        _assert_interactive_shell(observation)
    except AssertionError as error:
        failures.append(str(error))
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
            "The post-bootstrap shell did not expose the full interactive navigation.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell window:\n{json.dumps(_window_payload(observation), indent=2)}"
        )
    if observation["trigger"] is None:
        raise AssertionError(
            "The post-bootstrap shell did not expose the workspace switcher trigger.\n"
            f"Observed shell window:\n{json.dumps(_window_payload(observation), indent=2)}"
        )
    if not bool(observation["branding_visible"]):
        raise AssertionError(
            "The post-bootstrap shell did not expose the visible TrackState branding "
            "tagline.\n"
            f"Observed shell window:\n{json.dumps(_window_payload(observation), indent=2)}"
        )


def _record_missing_steps(result: dict[str, Any], *, starting_step: int) -> None:
    recorded = {
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    for step_number in range(starting_step, len(REQUEST_STEPS) + 1):
        if step_number in recorded:
            continue
        record_step(
            result,
            step=step_number,
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed=f"Not reached because step {starting_step - 1} failed.",
        )


def _request_path(url: str) -> str:
    parsed = urlparse(url)
    return parsed.path.rstrip("/") or "/"


def _relative_delayed_request_timings(
    *,
    delayed_request_timings: list[dict[str, Any]],
    startup_started_at_monotonic: float,
) -> list[dict[str, Any]]:
    relative_timings: list[dict[str, Any]] = []
    for timing in delayed_request_timings:
        if not isinstance(timing, dict):
            continue
        relative_timings.append(
            {
                "index": timing.get("index"),
                "url": str(timing.get("url", "")),
                "started_after_launch_seconds": relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    timing.get("started_at_monotonic"),
                ),
                "released_after_launch_seconds": relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    timing.get("released_at_monotonic"),
                ),
                "duration_seconds": relative_startup_event_seconds(
                    timing.get("started_at_monotonic"),
                    timing.get("released_at_monotonic"),
                ),
            },
        )
    return relative_timings


def _first_probe_duration_seconds(delayed_request_timings: Any) -> float | None:
    if not isinstance(delayed_request_timings, list):
        return None
    first_timing = next(
        (timing for timing in delayed_request_timings if isinstance(timing, dict)),
        None,
    )
    if first_timing is None:
        return None
    duration = first_timing.get("duration_seconds")
    if not isinstance(duration, (int, float)):
        return None
    return round(float(duration), 2)


def _earliest_shell_marker_after_start_seconds(pending_probe_state: Any) -> float | None:
    if not isinstance(pending_probe_state, dict):
        return None
    values = [
        pending_probe_state.get("first_any_shell_marker_visible_after_launch_seconds"),
        pending_probe_state.get("first_navigation_visible_after_launch_seconds"),
        pending_probe_state.get("first_trigger_visible_after_launch_seconds"),
        pending_probe_state.get("first_branding_visible_after_launch_seconds"),
    ]
    numeric_values = [round(float(value), 2) for value in values if isinstance(value, (int, float))]
    return min(numeric_values) if numeric_values else None


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
        samples.append(
            {
                "observed_after_launch_seconds": _ms_to_seconds(sample.get("observedAtMs")),
                "visible_navigation_labels": [
                    str(label) for label in sample.get("visibleNavigationLabels", [])
                ],
                "trigger_visible": bool(sample.get("triggerVisible")),
                "trigger_label": str(sample.get("triggerLabel", "")),
                "branding_visible": bool(sample.get("brandingVisible")),
                "shell_ready": bool(sample.get("shellReady")),
                "body_excerpt": str(sample.get("bodyExcerpt", "")),
            },
        )
    return samples


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
  window.__ts1033PendingShellProbeState = state;

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
    state.samples.push({
      observedAtMs: performance.now(),
      visibleNavigationLabels,
      triggerVisible: !!triggerLabel,
      triggerLabel,
      brandingVisible,
      shellReady: visibleNavigationLabels.length === readyLabels.length,
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
    if bool(result.get("product_failure")):
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
        "* Seeded an active hosted workspace plus stored GitHub token into browser storage to reproduce a cached session before launch.",
        "* Delayed the live GitHub {/user} startup probe by 5 seconds and captured bootstrap network traffic in the same browser session.",
        "* Verified the {/user} request began before visible shell markers appeared and then checked the final interactive shell state.",
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
        "testing/tests/TS-1033/test_ts_1033.py",
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
        "- Seeded an active hosted workspace plus stored GitHub token in browser storage to reproduce a cached authenticated session.",
        "- Delayed the live GitHub `/user` startup probe by 5 seconds and captured startup GitHub traffic in Chromium.",
        "- Required the `/user` request to begin during bootstrap before visible shell markers and then verified the user-visible shell still became interactive.",
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
            "The live run reproduced a cached hosted session, started the GitHub "
            "`/user` startup probe before visible shell markers appeared, and then "
            "rendered the interactive shell after the delayed probe completed.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{result.get('error', 'The deployed app did not expose the expected cached-session startup behavior.')}\n"
    )


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
        f"- Cached hosted workspace: `{result.get('cached_hosted_workspace_id')}`",
        f"- Delayed auth probe: GitHub `/user` delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- Cached session state: `{json.dumps(result.get('cached_session_state'), ensure_ascii=True)}`",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed request timings: `{json.dumps(result.get('delayed_request_timings', []), ensure_ascii=True)}`",
        f"- Pending probe state: `{json.dumps(result.get('pending_shell_probe_state', {}), ensure_ascii=True)}`",
        f"- Final shell observation: `{json.dumps(result.get('shell_window_observation'), ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "The deployed app issued the GitHub `/user` startup probe "
            f"{result.get('auth_probe_started_after_start_seconds')!r} seconds after "
            "launch, before the first visible shell marker at "
            f"{result.get('first_shell_marker_after_start_seconds')!r} seconds, kept the "
            "first delayed probe pending for "
            f"{result.get('first_auth_probe_pending_duration_seconds')!r} seconds, and "
            "then exposed the interactive shell."
        )
    return str(
        result.get(
            "error",
            "The deployed cached-session startup flow did not match the expected result.",
        ),
    )


if __name__ == "__main__":
    main()
