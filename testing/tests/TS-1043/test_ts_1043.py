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
TS1002_SUPPORT_DIR = REPO_ROOT / "testing" / "tests" / "TS-1002" / "support"
if str(TS1002_SUPPORT_DIR) not in sys.path:
    sys.path.insert(0, str(TS1002_SUPPORT_DIR))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
)
from testing.components.pages.trackstate_tracker_page import TrackStateTrackerPage  # noqa: E402
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from ts1002_secondary_probe_delay_runtime import (  # noqa: E402
    STARTUP_SAMPLE_GLOBAL,
    Ts1002SecondaryProbeDelayRuntime,
    Ts1002SecondaryProbeObservation,
)
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

TICKET_KEY = "TS-1043"
TEST_CASE_TITLE = (
    "Startup regression — authentication probe flags are correctly set during "
    "secondary path hangs"
)
TEST_FILE_PATH = "testing/tests/TS-1043/test_ts_1043.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1043/test_ts_1043.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts1043-local"
LOCAL_DISPLAY_NAME = "Active local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
BRANDING_TEXT = "Git-native. Jira-compatible. Team-proven."
PRIMARY_AUTH_PATH = "/user"
SECONDARY_PROBE_PATH = "DEMO/project.json"
AUTH_DELAY_SECONDS = 1
SECONDARY_PROBE_DELAY_SECONDS = 31
AUTH_OBSERVATION_WAIT_SECONDS = 5
SYNC_TIMEOUT_SECONDS = 11
TIMEOUT_ASSERTION_SECONDS = SYNC_TIMEOUT_SECONDS + 1
SECONDARY_PROBE_START_WAIT_SECONDS = 60
POLL_INTERVAL_SECONDS = 0.25
CHECKPOINT_SAMPLE_TOLERANCE_SECONDS = 1.0
LINKED_BUGS = ["TS-1038"]
LINKED_BUG_NOTES = (
    "Reviewed TS-1038. Its merged fix requires the startup `/user` probe to begin "
    "promptly even while a secondary critical-path fetch is hung, so this test "
    "delays `DEMO/project.json` for 31 seconds, waits long enough to observe the "
    "first 5-second auth-probe window, and only asserts the timeout checkpoint "
    "after the linked 11-second window has elapsed."
)
REWORK_SUMMARY = (
    "Reused the approved live secondary-probe runtime from TS-1002 so TS-1043 "
    "checks the deployed `/user` lifecycle against an actual hung `DEMO/project.json` "
    "bootstrap fetch, then verifies the same run at the timeout checkpoint."
)
REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Access the internal diagnostic state or monitor the telemetry logs during the first 5 seconds of the initialization window.",
    "Verify the status of the `auth_probe_started` flag.",
    "Wait for the 11-second synchronization timeout window to expire.",
    "Re-inspect the internal state for the `auth_probe_released` flag.",
]
EXPECTED_RESULT = (
    "The `auth_probe_started` flag is set to true within the required 5-second "
    "window, and `auth_probe_released` is true by the timeout checkpoint, "
    "confirming the identity probe lifecycle executes concurrently and "
    "independently of the hung secondary data fetch."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1043_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1043_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1043 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    hosted_workspace_id = f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}"
    workspace_state = _workspace_state(service.repository)
    prepared_local_workspace = _prepare_local_workspace_repository()
    observation = Ts1002SecondaryProbeObservation(repository=service.repository)
    runtime = Ts1002SecondaryProbeDelayRuntime(
        repository=config.repository,
        token=token,
        workspace_state=workspace_state,
        observation=observation,
        auth_delay_seconds=AUTH_DELAY_SECONDS,
        secondary_delay_seconds=SECONDARY_PROBE_DELAY_SECONDS,
        secondary_paths=(SECONDARY_PROBE_PATH,),
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
        "auth_observation_wait_seconds": AUTH_OBSERVATION_WAIT_SECONDS,
        "auth_delay_seconds": AUTH_DELAY_SECONDS,
        "secondary_probe_delay_seconds": SECONDARY_PROBE_DELAY_SECONDS,
        "secondary_probe_path": SECONDARY_PROBE_PATH,
        "preloaded_workspace_state": workspace_state,
        "hosted_workspace_id": hosted_workspace_id,
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

            startup_started_at_epoch_seconds = time.time()
            startup_started_at_monotonic = time.monotonic()
            tracker_page.open_entrypoint(wait_until="commit", timeout_ms=120_000)
            result["startup_observation_initial"] = startup_surface_payload(tracker_page)
            record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed=(
                    "Opened the deployed TrackState app in Chromium with a stored GitHub "
                    "token, local plus hosted workspace profiles, a 1-second delayed "
                    "`/user` auth probe, and a 31-second delayed "
                    f"`{SECONDARY_PROBE_PATH}` bootstrap fetch."
                ),
            )

            secondary_probe_started, secondary_probe_snapshot = poll_until(
                probe=lambda: {
                    "secondary_probe_started_at_monotonic": (
                        observation.secondary_probe_started_at_monotonic
                    ),
                    "github_request_urls": list(observation.github_request_urls),
                    "body_text": tracker_page.body_text(),
                },
                is_satisfied=lambda snapshot: (
                    snapshot["secondary_probe_started_at_monotonic"] is not None
                ),
                timeout_seconds=SECONDARY_PROBE_START_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            result["github_request_urls"] = list(observation.github_request_urls)
            result["delayed_request_urls"] = list(observation.delayed_request_urls)
            result["delayed_auth_request_urls"] = list(observation.delayed_auth_request_urls)
            result["delayed_secondary_request_urls"] = list(
                observation.delayed_secondary_request_urls,
            )
            result["secondary_probe_started_after_start_seconds"] = (
                relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    observation.secondary_probe_started_at_monotonic,
                )
            )
            result["secondary_probe_released_after_start_seconds"] = (
                relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    observation.secondary_probe_released_at_monotonic,
                )
            )

            if not secondary_probe_started:
                observed = (
                    "The live run never requested the delayed secondary startup artifact "
                    f"`{SECONDARY_PROBE_PATH}`, so the hung-secondary scenario from the "
                    "ticket was not established.\n"
                    f"Observed GitHub requests: {json.dumps(secondary_probe_snapshot['github_request_urls'], ensure_ascii=True)}\n"
                    f"Observed body text:\n{secondary_probe_snapshot['body_text']}"
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

            auth_window_complete, auth_probe_snapshot = poll_until(
                probe=lambda: {
                    "auth_probe_started_at_monotonic": (
                        observation.auth_probe_started_at_monotonic
                    ),
                    "auth_probe_released_at_monotonic": (
                        observation.auth_probe_released_at_monotonic
                    ),
                    "github_request_urls": list(observation.github_request_urls),
                    "delayed_auth_request_urls": list(
                        observation.delayed_auth_request_urls,
                    ),
                    "delayed_secondary_request_urls": list(
                        observation.delayed_secondary_request_urls,
                    ),
                    "body_text": tracker_page.body_text(),
                },
                is_satisfied=lambda snapshot: (
                    snapshot["auth_probe_started_at_monotonic"] is not None
                    and snapshot["auth_probe_released_at_monotonic"] is not None
                ),
                timeout_seconds=AUTH_OBSERVATION_WAIT_SECONDS,
                interval_seconds=POLL_INTERVAL_SECONDS,
            )
            del auth_window_complete
            result["first_five_second_telemetry"] = auth_probe_snapshot
            result["auth_probe_started_after_start_seconds"] = (
                relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    observation.auth_probe_started_at_monotonic,
                )
            )
            result["auth_probe_released_after_start_seconds"] = (
                relative_startup_event_seconds(
                    startup_started_at_monotonic,
                    observation.auth_probe_released_at_monotonic,
                )
            )

            record_step(
                result,
                step=2,
                status="passed",
                action=REQUEST_STEPS[1],
                observed=(
                    "Captured startup telemetry during the first 5 seconds while the "
                    f"secondary `{SECONDARY_PROBE_PATH}` request was already pending.\n"
                    f"secondary_probe_started_after_start_seconds="
                    f"{result['secondary_probe_started_after_start_seconds']!r}; "
                    f"auth_probe_started_after_start_seconds="
                    f"{result['auth_probe_started_after_start_seconds']!r}; "
                    f"auth_probe_released_after_start_seconds="
                    f"{result['auth_probe_released_after_start_seconds']!r}; "
                    f"delayed_auth_request_urls="
                    f"{json.dumps(result['delayed_auth_request_urls'], ensure_ascii=True)}; "
                    f"delayed_secondary_request_urls="
                    f"{json.dumps(result['delayed_secondary_request_urls'], ensure_ascii=True)}"
                ),
            )

            step_three_error: str | None = None
            auth_probe_started_after_start_seconds = result[
                "auth_probe_started_after_start_seconds"
            ]
            auth_probe_released_after_start_seconds = result[
                "auth_probe_released_after_start_seconds"
            ]
            if auth_probe_started_after_start_seconds is None:
                step_three_error = (
                    "The live startup run never recorded `auth_probe_started=True` during "
                    f"the required first {AUTH_OBSERVATION_WAIT_SECONDS} seconds.\n"
                    f"Observed first-window telemetry:\n{json.dumps(auth_probe_snapshot, indent=2)}"
                )
            elif float(auth_probe_started_after_start_seconds) > AUTH_OBSERVATION_WAIT_SECONDS:
                step_three_error = (
                    "The live startup run started the `/user` auth probe too late for the "
                    "required first-window assertion.\n"
                    f"auth_probe_started_after_start_seconds="
                    f"{auth_probe_started_after_start_seconds!r}\n"
                    f"Observed first-window telemetry:\n{json.dumps(auth_probe_snapshot, indent=2)}"
                )

            if step_three_error is None:
                release_note = (
                    f"; auth_probe_released_after_start_seconds="
                    f"{auth_probe_released_after_start_seconds!r}"
                    if auth_probe_released_after_start_seconds is not None
                    else ""
                )
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "`auth_probe_started` became true within the required first 5-second "
                        "window while the delayed secondary bootstrap fetch was already "
                        "pending.\n"
                        f"auth_probe_started_after_start_seconds="
                        f"{auth_probe_started_after_start_seconds!r}"
                        f"{release_note}"
                    ),
                )
            else:
                result["product_failure"] = True
                record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=step_three_error,
                )

            timeout_window = _observe_timeout_checkpoint(
                tracker_page=tracker_page,
                startup_started_at_epoch_seconds=startup_started_at_epoch_seconds,
                startup_started_at_monotonic=startup_started_at_monotonic,
                observation=observation,
                checkpoint_target_epoch_seconds=(
                    observation.secondary_probe_started_at_epoch_seconds
                    + TIMEOUT_ASSERTION_SECONDS
                    if observation.secondary_probe_started_at_epoch_seconds is not None
                    else None
                ),
            )
            result["timeout_window_observation"] = timeout_window

            step_four_error: str | None = None
            if observation.secondary_probe_started_at_monotonic is None:
                step_four_error = (
                    "The delayed secondary startup probe never exposed a start time, so the "
                    "timeout checkpoint could not be anchored.\n"
                    f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                )
            elif timeout_window.get("checkpoint_source") != "page_sampler":
                step_four_error = (
                    "The timeout checkpoint could not be recovered from the live page "
                    "sampler while the secondary probe was pending.\n"
                    f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                )
            elif abs(float(timeout_window.get("checkpoint_sample_offset_seconds") or 0.0)) > (
                CHECKPOINT_SAMPLE_TOLERANCE_SECONDS
            ):
                step_four_error = (
                    "The recovered timeout checkpoint drifted too far from the intended "
                    "11-second window.\n"
                    f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                )
            elif not bool(timeout_window.get("secondary_probe_pending")):
                step_four_error = (
                    "The delayed secondary startup probe was already released when the "
                    "timeout checkpoint was sampled, so the hung-secondary condition was "
                    "not still active.\n"
                    f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                )

            if step_four_error is None:
                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        f"Recovered a timeout-checkpoint sample "
                        f"{timeout_window['checkpoint_sample_offset_seconds']!r} seconds "
                        "from the intended mark while the secondary probe was still pending.\n"
                        f"shell_ready="
                        f"{timeout_window['shell_observation']['shell_ready']!r}; "
                        f"visible_navigation_labels="
                        f"{json.dumps(timeout_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}; "
                        f"trigger={json.dumps(timeout_window.get('trigger'), ensure_ascii=True)}"
                    ),
                )
            else:
                result["product_failure"] = True
                record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=step_four_error,
                )

            step_five_error: str | None = None
            if timeout_window.get("auth_probe_released_after_start_seconds") is None:
                step_five_error = (
                    "The timeout checkpoint did not show `auth_probe_released=True`.\n"
                    f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                )
            elif (
                result["auth_probe_released_after_start_seconds"] is not None
                and timeout_window["auth_probe_released_after_start_seconds"]
                != result["auth_probe_released_after_start_seconds"]
            ):
                step_five_error = (
                    "The timeout checkpoint disagreed with the earlier telemetry about when "
                    "the auth probe released.\n"
                    f"first_window_release={result['auth_probe_released_after_start_seconds']!r}\n"
                    f"timeout_checkpoint_release="
                    f"{timeout_window['auth_probe_released_after_start_seconds']!r}\n"
                    f"Observed timeout window:\n{json.dumps(timeout_window, indent=2)}"
                )

            if step_five_error is None:
                record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        "Re-inspecting the timeout checkpoint showed `auth_probe_released` "
                        "already true even though the secondary bootstrap fetch was still "
                        "pending, so the auth lifecycle was not serialized behind "
                        f"`{SECONDARY_PROBE_PATH}`.\n"
                        f"auth_probe_released_after_start_seconds="
                        f"{timeout_window['auth_probe_released_after_start_seconds']!r}; "
                        f"secondary_probe_pending={timeout_window['secondary_probe_pending']!r}"
                    ),
                )
            else:
                result["product_failure"] = True
                record_step(
                    result,
                    step=5,
                    status="failed",
                    action=REQUEST_STEPS[4],
                    observed=step_five_error,
                )

            record_human_verification(
                result,
                check=(
                    "Viewed the live page at the timeout checkpoint the way a user would and "
                    "recorded the visible workspace trigger, navigation labels, and branding "
                    "as diagnostic context."
                ),
                observed=(
                    f"body_text_snippet={snippet(timeout_window['startup_observation']['body_text'])!r}; "
                    f"trigger_label={(timeout_window.get('trigger') or {}).get('semantic_label')!r}; "
                    f"visible_navigation_labels="
                    f"{json.dumps(timeout_window['shell_observation']['visible_navigation_labels'], ensure_ascii=True)}; "
                    f"branding_visible={timeout_window['branding_visible']!r}"
                ),
            )
            record_human_verification(
                result,
                check=(
                    "Reviewed the same run's startup telemetry the way a human tester would "
                    "when confirming the `/user` probe did not wait for the hung secondary "
                    "bootstrap fetch."
                ),
                observed=(
                    f"auth_probe_started_after_start_seconds="
                    f"{result['auth_probe_started_after_start_seconds']!r}; "
                    f"auth_probe_released_after_start_seconds="
                    f"{result['auth_probe_released_after_start_seconds']!r}; "
                    f"secondary_probe_started_after_start_seconds="
                    f"{result['secondary_probe_started_after_start_seconds']!r}; "
                    f"delayed_auth_request_urls="
                    f"{json.dumps(result['delayed_auth_request_urls'], ensure_ascii=True)}; "
                    f"delayed_secondary_request_urls="
                    f"{json.dumps(result['delayed_secondary_request_urls'], ensure_ascii=True)}"
                ),
            )

            if any(
                step.get("status") == "failed"
                for step in result.get("steps", [])
                if isinstance(step, dict)
            ):
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise AssertionError(
                    "\n\n".join(
                        str(step.get("observed"))
                        for step in result["steps"]
                        if isinstance(step, dict) and step.get("status") == "failed"
                    ),
                )

            tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            _write_pass_outputs(result)
            print(f"{TICKET_KEY} passed")
            return
    except AssertionError as error:
        if tracker_page is not None and "screenshot" not in result:
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
        if tracker_page is not None and "screenshot" not in result:
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
    )


def _prepare_local_workspace_repository() -> dict[str, object]:
    return prepare_local_workspace_repository(
        local_target=LOCAL_TARGET,
        default_branch=DEFAULT_BRANCH,
        marker_filename=".trackstate-ts1043-precondition.txt",
        marker_contents="Prepared for TS-1043 startup auth lifecycle validation.\n",
        commit_author_name="TS-1043 Automation",
        commit_author_email="ts1043@example.com",
        commit_message="Prepare TS-1043 local workspace",
    )


def _observe_timeout_checkpoint(
    *,
    tracker_page: TrackStateTrackerPage,
    startup_started_at_epoch_seconds: float,
    startup_started_at_monotonic: float,
    observation: Ts1002SecondaryProbeObservation,
    checkpoint_target_epoch_seconds: float | None,
) -> dict[str, Any]:
    sample = _select_startup_sample(
        tracker_page,
        checkpoint_target_epoch_seconds=checkpoint_target_epoch_seconds,
    )
    if sample is None:
        body_text = tracker_page.body_text()
        checkpoint_source = "live_read"
        checkpoint_sample_epoch_seconds = None
        checkpoint_sample_offset_seconds = None
        title = "TrackState.AI"
        location_href = tracker_page.app_url
        location_hash = ""
        location_pathname = (
            "/trackstate-setup/" if "trackstate-setup" in tracker_page.app_url else "/"
        )
    else:
        body_text = str(sample.get("bodyText", ""))
        checkpoint_source = "page_sampler"
        checkpoint_sample_epoch_seconds = round(float(sample["epochMs"]) / 1000, 2)
        checkpoint_sample_offset_seconds = (
            None
            if checkpoint_target_epoch_seconds is None
            else round(
                checkpoint_sample_epoch_seconds - checkpoint_target_epoch_seconds,
                2,
            )
        )
        title = str(sample.get("title", "TrackState.AI"))
        location_href = str(sample.get("locationHref", tracker_page.app_url))
        location_hash = str(sample.get("locationHash", ""))
        location_pathname = str(
            sample.get(
                "locationPathname",
                "/trackstate-setup/" if "trackstate-setup" in tracker_page.app_url else "/",
            ),
        )

    normalized_lines = [
        " ".join(line.split())
        for line in body_text.splitlines()
        if " ".join(line.split())
    ]
    trigger_line = next(
        (line for line in normalized_lines if line.startswith("Workspace switcher:")),
        None,
    )
    visible_navigation_labels = [
        label for label in SHELL_NAVIGATION_LABELS if label in body_text
    ]
    startup_observation = {
        "title": title,
        "location_href": location_href,
        "location_hash": location_hash,
        "location_pathname": location_pathname,
        "body_text": body_text,
        "button_labels": [
            label
            for label in (
                "Dashboard",
                "Board",
                "JQL Search",
                "Hierarchy",
                "Settings",
                "Connect GitHub",
                "Create issue",
            )
            if label in body_text
        ],
    }
    sample_epoch_seconds = checkpoint_sample_epoch_seconds
    return {
        "checkpoint_source": checkpoint_source,
        "checkpoint_target_epoch_seconds": (
            round(checkpoint_target_epoch_seconds, 2)
            if checkpoint_target_epoch_seconds is not None
            else None
        ),
        "checkpoint_sample_epoch_seconds": checkpoint_sample_epoch_seconds,
        "checkpoint_sample_offset_seconds": checkpoint_sample_offset_seconds,
        "shell_observation": {
            "body_text": body_text,
            "visible_navigation_labels": visible_navigation_labels,
            "fatal_banner_visible": "TrackState data was not found" in body_text,
            "connect_github_visible": "Connect GitHub" in body_text,
            "shell_ready": len(visible_navigation_labels) == len(SHELL_NAVIGATION_LABELS),
        },
        "startup_observation": startup_observation,
        "trigger": (
            {"semantic_label": trigger_line, "visible_text": trigger_line}
            if trigger_line is not None
            else None
        ),
        "branding_visible": BRANDING_TEXT in body_text or "TrackState.AI" in body_text,
        "auth_probe_started_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            observation.auth_probe_started_at_monotonic,
        ),
        "auth_probe_released_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            observation.auth_probe_released_at_monotonic,
        ),
        "elapsed_since_auth_start_seconds": _relative_epoch_seconds(
            observation.auth_probe_started_at_epoch_seconds,
            sample_epoch_seconds,
        ),
        "secondary_probe_pending": _request_pending_at_epoch(
            started_at_epoch_seconds=observation.secondary_probe_started_at_epoch_seconds,
            released_at_epoch_seconds=observation.secondary_probe_released_at_epoch_seconds,
            sample_epoch_seconds=sample_epoch_seconds,
        ),
        "secondary_probe_started_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            observation.secondary_probe_started_at_monotonic,
        ),
        "secondary_probe_released_after_start_seconds": relative_startup_event_seconds(
            startup_started_at_monotonic,
            observation.secondary_probe_released_at_monotonic,
        ),
        "elapsed_since_secondary_probe_start_seconds": _relative_epoch_seconds(
            observation.secondary_probe_started_at_epoch_seconds,
            sample_epoch_seconds,
        ),
        "shell_ready_after_start_seconds": (
            _relative_epoch_seconds(
                startup_started_at_epoch_seconds,
                sample_epoch_seconds,
            )
            if sample_epoch_seconds is not None
            and len(visible_navigation_labels) == len(SHELL_NAVIGATION_LABELS)
            else None
        ),
    }


def _select_startup_sample(
    tracker_page: TrackStateTrackerPage,
    *,
    checkpoint_target_epoch_seconds: float | None,
) -> dict[str, Any] | None:
    samples = [
        sample
        for sample in tracker_page.read_global_samples(STARTUP_SAMPLE_GLOBAL)
        if isinstance(sample, dict) and isinstance(sample.get("epochMs"), (int, float))
    ]
    if not samples:
        return None
    if checkpoint_target_epoch_seconds is None:
        return dict(samples[-1])
    return dict(
        min(
            samples,
            key=lambda sample: abs(
                (float(sample["epochMs"]) / 1000) - checkpoint_target_epoch_seconds,
            ),
        ),
    )


def _relative_epoch_seconds(
    started_at_epoch_seconds: float | None,
    event_epoch_seconds: float | None,
) -> float | None:
    if started_at_epoch_seconds is None or event_epoch_seconds is None:
        return None
    return round(event_epoch_seconds - started_at_epoch_seconds, 2)


def _request_pending_at_epoch(
    *,
    started_at_epoch_seconds: float | None,
    released_at_epoch_seconds: float | None,
    sample_epoch_seconds: float | None,
) -> bool:
    if (
        started_at_epoch_seconds is None
        or sample_epoch_seconds is None
        or sample_epoch_seconds < started_at_epoch_seconds
    ):
        return False
    if released_at_epoch_seconds is None:
        return True
    return sample_epoch_seconds < released_at_epoch_seconds


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
        f"*Timing Applied:* delayed `{SECONDARY_PROBE_PATH}` for {SECONDARY_PROBE_DELAY_SECONDS} seconds, delayed `/user` for {AUTH_DELAY_SECONDS} second, inspected the first {AUTH_OBSERVATION_WAIT_SECONDS} seconds, then re-checked after the {SYNC_TIMEOUT_SECONDS}-second timeout window",
        "",
        "h4. What was automated",
        "* Opened the deployed TrackState web app with preloaded local plus hosted workspace state and stored GitHub token state.",
        f"* Delayed the hosted bootstrap fetch for {{{{code}}}}{SECONDARY_PROBE_PATH}{{{{code}}}} by {SECONDARY_PROBE_DELAY_SECONDS} seconds so the secondary startup path remained hung.",
        f"* Observed the live GitHub {{{{code}}}}/user{{{{code}}}} probe telemetry during the first {AUTH_OBSERVATION_WAIT_SECONDS} seconds and re-checked the timeout checkpoint from the same run.",
        "* Captured timeout-checkpoint UI diagnostics, including workspace trigger, navigation labels, and branding, while the secondary probe was still pending.",
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
        "- Opened the deployed TrackState web app with preloaded local plus hosted workspace state and stored GitHub token state.",
        f"- Delayed `{SECONDARY_PROBE_PATH}` by {SECONDARY_PROBE_DELAY_SECONDS} seconds so the secondary startup path stayed hung while the `/user` auth probe still had to execute.",
        f"- Observed the `/user` auth-probe lifecycle during the first {AUTH_OBSERVATION_WAIT_SECONDS} seconds, then re-checked it after the {SYNC_TIMEOUT_SECONDS}-second timeout window.",
        "- Captured the same run's visible workspace trigger, navigation labels, and TrackState branding at the timeout checkpoint as diagnostic context.",
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
            "The live run started the `/user` auth probe within the first 5 seconds, "
            "kept `DEMO/project.json` pending through the timeout checkpoint, and showed "
            "the auth probe already released by that later checkpoint.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not expose the expected startup auth lifecycle.')}\n"
    )


def _should_write_bug_description(result: dict[str, Any]) -> bool:
    error = str(result.get("error", ""))
    if error.startswith("RuntimeError: TS-1043 requires GH_TOKEN or GITHUB_TOKEN"):
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
        f"- Delayed auth probe: GitHub `/user` delayed by {AUTH_DELAY_SECONDS} second",
        f"- Delayed secondary startup fetch: `{SECONDARY_PROBE_PATH}` delayed by {SECONDARY_PROBE_DELAY_SECONDS} seconds",
        f"- Timeout checkpoint: {TIMEOUT_ASSERTION_SECONDS} seconds after the delayed secondary probe started",
        "",
        "## Screenshots or logs",
        f"- Screenshot: `{result.get('screenshot')}`",
        f"- GitHub requests seen: `{json.dumps(result.get('github_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed auth requests seen: `{json.dumps(result.get('delayed_auth_request_urls', []), ensure_ascii=True)}`",
        f"- Delayed secondary requests seen: `{json.dumps(result.get('delayed_secondary_request_urls', []), ensure_ascii=True)}`",
        f"- First-window telemetry: `{json.dumps(result.get('first_five_second_telemetry'), ensure_ascii=True)}`",
        f"- Timeout window observation: `{json.dumps(result.get('timeout_window_observation'), ensure_ascii=True)}`",
    ]
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        return (
            "During the live hung-secondary startup run, the `/user` auth probe started "
            "within the first 5 seconds and was already released by the timeout "
            f"checkpoint while `{SECONDARY_PROBE_PATH}` was still pending."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not expose the expected startup auth-probe lifecycle.",
        ),
    )


if __name__ == "__main__":
    main()
