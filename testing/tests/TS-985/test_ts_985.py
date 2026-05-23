from __future__ import annotations

import json
import platform
import subprocess
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
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import WebAppTimeoutError  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.delayed_auth_workspace_profiles_runtime import (  # noqa: E402
    DelayedAuthWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-985"
TEST_CASE_TITLE = (
    "Application startup with successful probe — UI shell becomes interactive "
    "without waiting for timeout"
)
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
LINKED_BUG_NOTES = (
    "Reviewed input/TS-985/linked_bugs.md and found TS-973, which targets the "
    "workspace-switcher footer focus loop rather than startup timing; it added "
    "no extra async wait requirement beyond the 2-second startup probe used here."
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
    runtime = DelayedAuthWorkspaceProfilesRuntime(
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

                trigger_visible, initial_trigger = poll_until(
                    probe=lambda: _try_observe_trigger(page),
                    is_satisfied=lambda candidate: candidate is not None,
                    timeout_seconds=120,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                if not trigger_visible or initial_trigger is None:
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
                result["initial_trigger_observation"] = _trigger_payload(initial_trigger)
                result["trigger_observed_after_start_seconds"] = round(
                    time.monotonic() - startup_started_at_monotonic,
                    2,
                )

                if not runtime.wait_for_auth_probe_start(
                    timeout_seconds=AUTH_PROBE_START_WAIT_SECONDS,
                ):
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

                if not runtime.wait_for_auth_probe_release(
                    timeout_seconds=SHELL_READY_WAIT_SECONDS,
                ):
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

                auth_probe_started_after_start_seconds = _relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    runtime.auth_probe_started_at_monotonic,
                )
                auth_probe_released_after_start_seconds = _relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    runtime.auth_probe_released_at_monotonic,
                )
                result["auth_probe_started_after_start_seconds"] = (
                    auth_probe_started_after_start_seconds
                )
                result["auth_probe_released_after_start_seconds"] = (
                    auth_probe_released_after_start_seconds
                )
                result["github_request_urls"] = list(runtime.github_request_urls)
                result["delayed_request_urls"] = list(runtime.delayed_request_urls)

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

                shell_ready, shell_window = poll_until(
                    probe=lambda: _observe_shell_window(
                        tracker_page=tracker_page,
                        page=page,
                        runtime=runtime,
                        startup_started_at_monotonic=startup_started_at_monotonic,
                    ),
                    is_satisfied=lambda observation: bool(
                        observation["shell_observation"]["shell_ready"],
                    ),
                    timeout_seconds=SHELL_READY_WAIT_SECONDS,
                    interval_seconds=POLL_INTERVAL_SECONDS,
                )
                result["shell_window_observation"] = shell_window

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
                shell_ready_after_probe_release_seconds = shell_window[
                    "shell_ready_after_probe_release_seconds"
                ]

                timing_failures: list[str] = []
                if auth_probe_released_after_start_seconds is None:
                    timing_failures.append(
                        "The delayed startup probe release time could not be measured.",
                    )
                if shell_ready_after_start_seconds is None:
                    timing_failures.append(
                        "The shell_ready transition time could not be measured.",
                    )
                if (
                    auth_probe_released_after_start_seconds is not None
                    and shell_ready_after_start_seconds is not None
                    and shell_ready_after_start_seconds
                    < auth_probe_released_after_start_seconds
                ):
                    timing_failures.append(
                        "The shell reported ready before the delayed startup probe was released.",
                    )
                if (
                    shell_ready_after_start_seconds is not None
                    and shell_ready_after_start_seconds >= FULL_SYNC_TIMEOUT_SECONDS
                ):
                    timing_failures.append(
                        f"The shell became ready only after {shell_ready_after_start_seconds!r} "
                        f"seconds, which is not before the full {FULL_SYNC_TIMEOUT_SECONDS}-second "
                        "timeout window.",
                    )
                if (
                    shell_ready_after_start_seconds is not None
                    and shell_ready_after_start_seconds > MAX_READY_AFTER_START_SECONDS
                ):
                    timing_failures.append(
                        f"The shell became ready after {shell_ready_after_start_seconds!r} "
                        f"seconds, which is too slow for the expected short successful-probe path "
                        f"(threshold {MAX_READY_AFTER_START_SECONDS} seconds).",
                    )
                if (
                    shell_ready_after_probe_release_seconds is not None
                    and shell_ready_after_probe_release_seconds
                    > MAX_READY_AFTER_RELEASE_SECONDS
                ):
                    timing_failures.append(
                        "The shell did not become interactive soon enough after the startup "
                        f"probe completed. Observed delay after release: "
                        f"{shell_ready_after_probe_release_seconds!r} seconds; allowed "
                        f"threshold: {MAX_READY_AFTER_RELEASE_SECONDS} seconds.",
                    )

                if timing_failures:
                    observed = (
                        "The startup probe completed, but the live app did not prove the "
                        "expected immediate shell-ready behavior.\n"
                        f"shell_ready_after_start_seconds={shell_ready_after_start_seconds!r}; "
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"shell_ready_after_probe_release_seconds="
                        f"{shell_ready_after_probe_release_seconds!r}; "
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
                        f"auth_probe_released_after_start_seconds="
                        f"{auth_probe_released_after_start_seconds!r}; "
                        f"shell_ready_after_probe_release_seconds="
                        f"{shell_ready_after_probe_release_seconds!r}; "
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
                        f"shell_ready_after_start_seconds={shell_ready_after_start_seconds!r}; "
                        f"shell_ready_after_probe_release_seconds="
                        f"{shell_ready_after_probe_release_seconds!r}; "
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
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": local_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": local_id,
                "displayName": LOCAL_DISPLAY_NAME,
                "customDisplayName": LOCAL_DISPLAY_NAME,
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
        ],
    }


def _prepare_local_workspace_repository() -> dict[str, object]:
    local_path = Path(LOCAL_TARGET)
    local_path.mkdir(parents=True, exist_ok=True)

    git_dir = local_path / ".git"
    if not git_dir.exists():
        subprocess.run(
            ["git", "init", "--initial-branch", DEFAULT_BRANCH, str(local_path)],
            check=True,
            capture_output=True,
            text=True,
        )

    marker_path = local_path / ".trackstate-ts985-precondition.txt"
    marker_path.write_text(
        "Prepared for TS-985 successful startup probe validation.\n",
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "-C", str(local_path), "add", marker_path.name],
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip() or head.returncode != 0:
        subprocess.run(
            [
                "git",
                "-C",
                str(local_path),
                "-c",
                "user.name=TS-985 Automation",
                "-c",
                "user.email=ts985@example.com",
                "commit",
                "--allow-empty",
                "-m",
                "Prepare TS-985 local workspace",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    branch = subprocess.run(
        ["git", "-C", str(local_path), "branch", "--show-current"],
        check=True,
        capture_output=True,
        text=True,
    )
    head = subprocess.run(
        ["git", "-C", str(local_path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "-C", str(local_path), "status", "--short"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        "path": str(local_path),
        "branch": branch.stdout.strip(),
        "head": head.stdout.strip(),
        "status": status.stdout.strip(),
        "marker_path": str(marker_path),
    }


def _observe_shell_window(
    *,
    tracker_page: TrackStateTrackerPage,
    page: LiveWorkspaceSwitcherPage,
    runtime: DelayedAuthWorkspaceProfilesRuntime,
    startup_started_at_monotonic: float,
) -> dict[str, Any]:
    shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
        timeout_ms=1_000,
    )
    startup_observation = _startup_surface_payload(tracker_page)
    trigger = _safe_trigger_payload(page)
    body_text = str(shell_observation.get("body_text", ""))
    title = str(startup_observation.get("title", ""))
    shell_ready_after_start_seconds = _relative_startup_event_seconds(
        startup_started_at_monotonic,
        time.monotonic() if bool(shell_observation.get("shell_ready")) else None,
    )
    auth_probe_released_after_start_seconds = _relative_startup_event_seconds(
        startup_started_at_monotonic,
        runtime.auth_probe_released_at_monotonic,
    )
    shell_ready_after_probe_release_seconds = _elapsed_between(
        runtime.auth_probe_released_at_monotonic,
        time.monotonic() if bool(shell_observation.get("shell_ready")) else None,
    )
    return {
        "shell_observation": shell_observation,
        "startup_observation": startup_observation,
        "trigger": trigger,
        "branding_visible": BRANDING_TEXT in body_text
        or "TrackState" in body_text
        or "TrackState" in title,
        "auth_pending": runtime.auth_probe_pending,
        "auth_probe_started_after_start_seconds": _relative_startup_event_seconds(
            startup_started_at_monotonic,
            runtime.auth_probe_started_at_monotonic,
        ),
        "auth_probe_released_after_start_seconds": auth_probe_released_after_start_seconds,
        "shell_ready_after_start_seconds": shell_ready_after_start_seconds,
        "shell_ready_after_probe_release_seconds": shell_ready_after_probe_release_seconds,
    }


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
    if event_monotonic is None:
        return None
    return round(event_monotonic - startup_started_at_monotonic, 2)


def _startup_surface_payload(tracker_page: TrackStateTrackerPage) -> dict[str, Any]:
    observation = tracker_page.observe_startup_surface()
    return {
        "title": observation.title,
        "location_href": observation.location_href,
        "location_hash": observation.location_hash,
        "location_pathname": observation.location_pathname,
        "body_text": observation.body_text,
        "button_labels": list(observation.button_labels),
    }


def _safe_trigger_payload(
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any] | None:
    try:
        trigger = page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None
    return _trigger_payload(trigger)


def _try_observe_trigger(
    page: LiveWorkspaceSwitcherPage,
) -> WorkspaceSwitcherTriggerObservation | None:
    try:
        return page.observe_trigger(timeout_ms=1_000)
    except (AssertionError, WebAppTimeoutError):
        return None


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, Any]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "top_button_labels": list(trigger.top_button_labels),
    }


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
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _record_step(
    result: dict[str, Any],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        },
    )


def _record_human_verification(
    result: dict[str, Any],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _record_not_reached_steps(
    result: dict[str, Any],
    *,
    starting_step: int,
) -> None:
    recorded = {
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    for step_number in range(starting_step, len(REQUEST_STEPS) + 1):
        if step_number in recorded:
            continue
        _record_step(
            result,
            step=step_number,
            status="failed",
            action=REQUEST_STEPS[step_number - 1],
            observed=f"Not reached because step {starting_step - 1} failed.",
        )


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    error = str(result.get("error", f"AssertionError: {TICKET_KEY} failed"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            },
        )
        + "\n",
        encoding="utf-8",
    )
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
        f"*Startup probe setup*: delayed successful GitHub {{/user}} probe by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        f"*Timeout target checked*: shell becomes interactive before the full {FULL_SYNC_TIMEOUT_SECONDS}-second window",
        f"*Linked bug review*: {LINKED_BUG_NOTES}",
        "",
        "h4. What was automated",
        "* Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded workspace state.",
        "* Delayed the live GitHub {/user} startup probe by 2 seconds, then waited for the real deployed shell to report {shell_ready} instead of asserting immediately.",
        "* Verified the visible shell became interactive before the full 11-second timeout and shortly after the delayed probe completed.",
        "* Confirmed the live page exposed shell navigation, the top-bar workspace trigger, and TrackState branding from the user's perspective.",
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
        "- Added a live Playwright startup regression that delays the initial GitHub `/user` probe by 2 seconds and proves the deployed shell becomes interactive shortly after the probe succeeds instead of waiting for the full timeout window.",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Startup probe setup:** delayed successful GitHub `/user` probe by `{SIMULATED_PROBE_DELAY_SECONDS}` seconds",
        f"**Timeout target checked:** interactive shell before the full `{FULL_SYNC_TIMEOUT_SECONDS}`-second window",
        f"**Linked bug review:** {LINKED_BUG_NOTES}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored GitHub token and preloaded workspace state.",
        "- Delayed the live GitHub `/user` startup probe by 2 seconds, then waited for the real deployed shell to report `shell_ready` instead of asserting immediately.",
        "- Verified the visible shell became interactive before the full 11-second timeout and shortly after the delayed probe completed.",
        "- Confirmed the live page exposed shell navigation, the top-bar workspace trigger, and TrackState branding from the user's perspective.",
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
    annotated_steps: list[str] = []
    steps = result.get("steps", [])
    for index, action in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and int(step.get("step", -1)) == index
            ),
            None,
        )
        if matching is None:
            annotated_steps.append(f"{index}. ⏭️ {action} Not reached.")
            continue
        icon = "✅" if str(matching.get("status")) == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}"
        )

    shell_window = json.dumps(result.get("shell_window_observation"), ensure_ascii=True)
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
        f"- Delayed startup probe: GitHub `/user` delayed by {SIMULATED_PROBE_DELAY_SECONDS} seconds",
        f"- Full timeout window checked: {FULL_SYNC_TIMEOUT_SECONDS} seconds",
        "",
        "## Screenshots or logs",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed requests seen: `{json.dumps(result.get('delayed_request_urls', []), ensure_ascii=True)}`",
        f"- Shell observation: `{shell_window}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
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
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        if jira:
            lines.append(
                f"# Step {step['step']} *{str(step['status']).upper()}*: {step['action']}\n"
                f"Observed: {{{{code}}}}{step['observed']}{{{{code}}}}",
            )
        else:
            lines.append(
                f"- Step {step['step']} **{step['status']}** — {step['action']}  \n"
                f"  Observed: `{step['observed']}`",
            )
    return lines


def _human_lines(result: dict[str, Any], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        if not isinstance(entry, dict):
            continue
        if jira:
            lines.append(
                f"* {entry['check']} Observed: {{{{code}}}}{entry['observed']}{{{{code}}}}",
            )
        else:
            lines.append(f"- **{entry['check']}** Observed: `{entry['observed']}`")
    return lines


if __name__ == "__main__":
    main()
