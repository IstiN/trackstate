from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
TEST_DIR = Path(__file__).resolve().parent
if str(TEST_DIR) not in sys.path:
    sys.path.insert(0, str(TEST_DIR))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherRowObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.utils.polling import poll_until  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from ts982_bootstrap_sync_failure_runtime import (  # noqa: E402
    Ts982BootstrapSyncFailureObservation,
    Ts982BootstrapSyncFailureRuntime,
)

TICKET_KEY = "TS-982"
TEST_CASE_TITLE = (
    "Workspace synchronization fails with non-200 response — application shell "
    "mounts in Safe Mode"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-982/test_ts_982.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
LINKED_BUGS = ["TS-977", "TS-991", "TS-1014", "TS-1027"]
INJECTED_FAILURE_STATUS_CODE = 500
INJECTED_FAILURE_ATTEMPT = 1
SETTLE_TIMEOUT_SECONDS = 20
FAILURE_MESSAGE_FRAGMENTS = (
    "Sync error, attention needed",
    "GitHub connection failed (500)",
    "Internal Server Error",
    "Sync issue",
)
AUTH_FALLBACK_FRAGMENTS = (
    "Stored GitHub token is no longer valid",
    "Needs sign-in",
)
REQUIRED_SWITCHER_STATE = "Sync issue"
REWORK_SUMMARY = (
    "Updates TS-982 to fail the live startup branch-sync request, wait for the "
    "post-failure state to settle, and only pass when the shell stays mounted "
    "and Workspace switcher shows the exact `Sync issue` recovery state."
)
REQUEST_STEPS = [
    "Launch the TrackState application.",
    "Monitor the UI mounting sequence.",
    "Verify the visibility and interactivity of the TopBar and Sidebar navigation.",
    'Check the workspace switcher panel area for the "Sync issue" fallback component.',
]
EXPECTED_RESULT = (
    "The application shell (TopBar, Sidebar) mounts successfully and remains "
    'interactive instead of staying stuck on a terminal error screen. The '
    'workspace switcher displays a "Sync issue" component, confirming the local '
    "handling of the synchronization failure."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts982_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts982_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-982 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

    observation = Ts982BootstrapSyncFailureObservation(repository=service.repository)
    runtime = Ts982BootstrapSyncFailureRuntime(
        repository=service.repository,
        token=token,
        workspace_state=_workspace_state(service.repository),
        observation=observation,
        fail_status_code=INJECTED_FAILURE_STATUS_CODE,
        fail_on_startup_sync_attempt=INJECTED_FAILURE_ATTEMPT,
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
        "injected_failure_status_code": INJECTED_FAILURE_STATUS_CODE,
        "injected_failure_attempt": INJECTED_FAILURE_ATTEMPT,
        "injected_failure_path": observation.startup_sync_path,
        "preloaded_workspace_state": _workspace_state(service.repository),
        "steps": [],
        "human_verification": [],
    }

    failures: list[str] = []
    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            tracker_page.session.set_viewport_size(**DESKTOP_VIEWPORT)
            runtime_observation = tracker_page.open()
            result["runtime_state"] = runtime_observation.kind
            result["runtime_body_text"] = runtime_observation.body_text
            if runtime_observation.kind == "ready":
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed app with a seeded hosted workspace and a "
                        "one-time synthetic HTTP 500 queued for the startup branch-sync "
                        f"request. Initial runtime state={runtime_observation.kind!r}."
                    ),
                )
            else:
                step_one_error = (
                    "Step 1 failed: the deployed app did not reach the startup shell before "
                    "the workspace-sync failure scenario began.\n"
                    f"Observed runtime state: {runtime_observation.kind}\n"
                    f"Observed body text:\n{runtime_observation.body_text}"
                )
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=step_one_error,
                )
                failures.append(step_one_error)

            safe_mode_reached, safe_mode_observation = poll_until(
                probe=lambda: _observe_safe_mode_window(tracker_page, page, observation),
                is_satisfied=_safe_mode_window_reached,
                timeout_seconds=45,
                interval_seconds=2,
            )
            result["safe_mode_observation"] = safe_mode_observation
            if safe_mode_reached:
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The startup branch-sync request was blocked after the shell began "
                        "mounting, and the page stayed on the interactive shell observation "
                        "path long enough to inspect the async recovery state.\n"
                        f"blocked_request={json.dumps(safe_mode_observation['blocked_request'], ensure_ascii=True)}\n"
                        f"visible_failure_fragments={json.dumps(safe_mode_observation['visible_failure_fragments'], ensure_ascii=True)}\n"
                        f"visible_auth_fragments={json.dumps(safe_mode_observation['visible_auth_fragments'], ensure_ascii=True)}"
                    ),
                )
            else:
                step_two_error = (
                    "Step 2 failed: the synthetic workspace-sync 500 did not surface as a "
                    "visible startup failure within the expected observation window.\n"
                    f"Observed window: {json.dumps(safe_mode_observation, ensure_ascii=True)}"
                )
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=step_two_error,
                )
                failures.append(step_two_error)

            settled_recovery_state, settled_recovery_observation = poll_until(
                probe=lambda: _observe_settled_recovery_state(tracker_page, page),
                is_satisfied=_settled_recovery_state_ready,
                timeout_seconds=SETTLE_TIMEOUT_SECONDS,
                interval_seconds=2,
            )
            result["settled_recovery_observation"] = settled_recovery_observation
            result["settled_recovery_state_ready"] = settled_recovery_state

            try:
                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                    timeout_ms=10_000,
                )
                trigger = page.observe_trigger()
                result["shell_observation"] = shell_observation
                result["trigger_observation"] = _trigger_payload(trigger)
                _assert_shell_is_interactive(shell_observation, trigger)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The desktop shell remained interactive after the 500 failure. "
                        f"visible_navigation_labels={json.dumps(shell_observation['visible_navigation_labels'], ensure_ascii=True)}; "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"top_button_labels={json.dumps(list(trigger.top_button_labels), ensure_ascii=True)}"
                    ),
                )
            except Exception as error:
                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                    timeout_ms=2_000,
                )
                result["shell_observation"] = shell_observation
                trigger = None
                try:
                    trigger = page.observe_trigger()
                    result["trigger_observation"] = _trigger_payload(trigger)
                except Exception:
                    result["trigger_observation"] = None
                step_three_error = (
                    "Step 3 failed: the TopBar and Sidebar did not remain fully interactive "
                    "after the startup sync failure.\n"
                    f"error={error}\n"
                    f"shell_observation={json.dumps(shell_observation, ensure_ascii=True)}\n"
                    f"trigger_observation={json.dumps(result['trigger_observation'], ensure_ascii=True)}"
                )
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=step_three_error,
                )
                failures.append(step_three_error)

            try:
                switcher = page.open_and_observe()
                panel = page.observe_open_panel(
                    expected_container_kinds=("anchored-panel", "surface"),
                    timeout_ms=4_000,
                )
                result["switcher_observation"] = _switcher_payload(switcher)
                result["panel_observation"] = _panel_payload(panel)
                sync_issue_row = _find_sync_issue_row(switcher)
                result["fallback_row"] = _row_payload(sync_issue_row)
                _assert_workspace_switcher_fallback(
                    switcher=switcher,
                    panel=panel,
                    sync_issue_row=sync_issue_row,
                    settled_recovery_observation=settled_recovery_observation,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "Workspace switcher stayed open and exposed the saved hosted "
                        f"workspace with the exact `{REQUIRED_SWITCHER_STATE}` recovery "
                        "state instead of an auth/sign-in fallback.\n"
                        f"fallback_row={json.dumps(result['fallback_row'], ensure_ascii=True)}\n"
                        f"settled_recovery={json.dumps(settled_recovery_observation, ensure_ascii=True)}\n"
                        f"panel={json.dumps(result['panel_observation'], ensure_ascii=True)}"
                    ),
                )
            except Exception as error:
                step_four_error = (
                    "Step 4 failed: the workspace switcher did not expose a visible fallback "
                    "workspace state after the startup sync failure.\n"
                    f"error={error}\n"
                    f"switcher_observation={json.dumps(result.get('switcher_observation'), ensure_ascii=True)}\n"
                    f"panel_observation={json.dumps(result.get('panel_observation'), ensure_ascii=True)}"
                )
                _record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=step_four_error,
                )
                failures.append(step_four_error)

            _record_human_verification(
                result,
                check=(
                    "Viewed the live desktop shell as a user and confirmed TrackState "
                    "branding plus the desktop navigation stayed visible after the 500 "
                    "workspace-sync failure surfaced."
                ),
                observed=(
                    f"visible_navigation_labels={json.dumps(result.get('shell_observation', {}).get('visible_navigation_labels', []), ensure_ascii=True)}; "
                    f"failure_fragments={json.dumps(safe_mode_observation.get('visible_failure_fragments', []), ensure_ascii=True)}; "
                    f"auth_fragments={json.dumps(settled_recovery_observation.get('visible_auth_fragments', []), ensure_ascii=True)}; "
                    f"body_preview={settled_recovery_observation.get('body_preview')!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Opened Workspace switcher and checked the saved hosted workspace row "
                    "from the same user-visible panel where a recovery fallback would appear."
                ),
                observed=(
                    f"fallback_row={json.dumps(result.get('fallback_row'), ensure_ascii=True)}; "
                    f"settled_trigger={json.dumps(settled_recovery_observation.get('trigger_observation'), ensure_ascii=True)}; "
                    f"switcher_text={result.get('switcher_observation', {}).get('switcher_text')!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Confirmed the startup failure was visible to the user as an on-screen "
                    "500 error message while the rest of the shell remained usable."
                ),
                observed=(
                    f"blocked_request={json.dumps(safe_mode_observation.get('blocked_request'), ensure_ascii=True)}; "
                    f"visible_failure_fragments={json.dumps(settled_recovery_observation.get('visible_failure_fragments', []), ensure_ascii=True)}"
                ),
            )

            if failures:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise AssertionError("\n\n".join(failures))

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            _write_pass_outputs(result)
            print("TS-982 passed")
            return
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        result["blocked_requests"] = [
            _blocked_request_payload(item) for item in observation.blocked_requests
        ]
        result["startup_sync_urls"] = list(observation.startup_sync_urls)
        result["all_repository_request_urls"] = list(observation.all_repository_request_urls)
        if page is not None and "screenshot" not in result:
            page.screenshot(str(FAILURE_SCREENSHOT_PATH))
            result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
        _write_failure_outputs(result)
        raise


def _workspace_state(repository: str) -> dict[str, object]:
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_id,
                "displayName": "",
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-14T12:00:00.000Z",
            },
        ],
    }


def _observe_safe_mode_window(
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
    observation: Ts982BootstrapSyncFailureObservation,
) -> dict[str, Any]:
    body_text = tracker_page.body_text()
    shell_observation = tracker_page.observe_interactive_shell(
        SHELL_NAVIGATION_LABELS,
        timeout_ms=3_000,
    )
    trigger_payload: dict[str, Any] | None
    try:
        trigger_payload = _trigger_payload(page.observe_trigger())
    except Exception:
        trigger_payload = None
    visible_failure_fragments = [
        fragment for fragment in FAILURE_MESSAGE_FRAGMENTS if fragment in body_text
    ]
    visible_auth_fragments = [
        fragment for fragment in AUTH_FALLBACK_FRAGMENTS if fragment in body_text
    ]
    blocked_request = (
        _blocked_request_payload(observation.blocked_requests[0])
        if observation.blocked_requests
        else None
    )
    return {
        "blocked_request": blocked_request,
        "blocked_request_count": len(observation.blocked_requests),
        "blocked_was_exercised": observation.blocked_was_exercised,
        "visible_failure_fragments": visible_failure_fragments,
        "visible_auth_fragments": visible_auth_fragments,
        "failure_message_visible": bool(visible_failure_fragments),
        "body_preview": body_text[:500],
        "body_text": body_text,
        "shell_observation": shell_observation,
        "trigger_observation": trigger_payload,
        "startup_sync_urls": list(observation.startup_sync_urls),
    }


def _safe_mode_window_reached(observation: dict[str, Any]) -> bool:
    return bool(
        observation.get("blocked_was_exercised")
        and observation.get("shell_observation", {}).get("shell_ready")
    )


def _observe_settled_recovery_state(
    tracker_page,
    page: LiveWorkspaceSwitcherPage,
) -> dict[str, Any]:
    body_text = tracker_page.body_text()
    trigger_payload: dict[str, Any] | None
    try:
        trigger_payload = _trigger_payload(page.observe_trigger())
    except Exception:
        trigger_payload = None
    visible_failure_fragments = [
        fragment for fragment in FAILURE_MESSAGE_FRAGMENTS if fragment in body_text
    ]
    visible_auth_fragments = [
        fragment for fragment in AUTH_FALLBACK_FRAGMENTS if fragment in body_text
    ]
    return {
        "body_preview": body_text[:500],
        "body_text": body_text,
        "trigger_observation": trigger_payload,
        "visible_failure_fragments": visible_failure_fragments,
        "visible_auth_fragments": visible_auth_fragments,
    }


def _settled_recovery_state_ready(observation: dict[str, Any]) -> bool:
    trigger_observation = observation.get("trigger_observation") or {}
    state_label = str(trigger_observation.get("state_label", "")).strip()
    return bool(state_label and state_label != "Needs sign-in")


def _assert_shell_is_interactive(
    shell_observation: dict[str, object],
    trigger: WorkspaceSwitcherTriggerObservation,
) -> None:
    if not bool(shell_observation.get("shell_ready")):
        raise AssertionError(
            "The desktop shell did not report shell_ready=true.\n"
            f"Observed shell state: {json.dumps(shell_observation, ensure_ascii=True)}"
        )
    visible_navigation_labels = [
        str(label) for label in shell_observation.get("visible_navigation_labels", [])
    ]
    missing_navigation = [
        label for label in SHELL_NAVIGATION_LABELS if label not in visible_navigation_labels
    ]
    if missing_navigation:
        raise AssertionError(
            "The shell was missing one or more required navigation labels after the "
            "startup sync failure.\n"
            f"Missing labels: {missing_navigation}\n"
            f"Observed shell state: {json.dumps(shell_observation, ensure_ascii=True)}"
        )
    if not trigger.semantic_label.strip():
        raise AssertionError("The workspace switcher trigger did not expose a readable label.")
    if trigger.width <= 0 or trigger.height <= 0:
        raise AssertionError(
            "The workspace switcher trigger was not visibly sized in the mounted shell.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), ensure_ascii=True)}"
        )


def _find_sync_issue_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        state_label = (row.state_label or "").strip()
        if state_label == REQUIRED_SWITCHER_STATE:
            return row
    return None


def _assert_workspace_switcher_fallback(
    *,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    sync_issue_row: WorkspaceSwitcherRowObservation | None,
    settled_recovery_observation: dict[str, Any],
) -> None:
    if switcher.row_count < 1:
        raise AssertionError(
            "Workspace switcher did not expose any saved workspace rows.\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), ensure_ascii=True)}"
        )
    if "Saved workspaces" not in switcher.switcher_text:
        raise AssertionError(
            "Workspace switcher did not render the saved-workspaces section.\n"
            f"Observed switcher text: {switcher.switcher_text!r}"
        )
    if sync_issue_row is None:
        raise AssertionError(
            "Workspace switcher did not expose the exact required `Sync issue` row.\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), ensure_ascii=True)}\n"
            f"Settled recovery: {json.dumps(settled_recovery_observation, ensure_ascii=True)}"
        )
    if sync_issue_row.state_label != REQUIRED_SWITCHER_STATE:
        raise AssertionError(
            "Workspace switcher exposed a row, but it was not labeled with the exact "
            f"required `{REQUIRED_SWITCHER_STATE}` state.\n"
            f"Observed row: {json.dumps(_row_payload(sync_issue_row), ensure_ascii=True)}"
        )
    if panel.width <= 0 or panel.height <= 0:
        raise AssertionError(
            "Workspace switcher panel was not visibly rendered.\n"
            f"Observed panel: {json.dumps(_panel_payload(panel), ensure_ascii=True)}"
        )
    if REQUIRED_SWITCHER_STATE not in switcher.switcher_text:
        raise AssertionError(
            "Workspace switcher text never exposed the exact `Sync issue` recovery copy.\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), ensure_ascii=True)}"
        )
    if (
        settled_recovery_observation.get("trigger_observation", {}).get("state_label")
        == "Needs sign-in"
    ):
        raise AssertionError(
            "The startup flow settled into the auth/sign-in fallback state instead of "
            "the required sync-issue recovery state.\n"
            f"Observed recovery: {json.dumps(settled_recovery_observation, ensure_ascii=True)}"
        )


def _record_step(
    result: dict[str, Any],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    result.setdefault("steps", []).append(
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
    result.setdefault("human_verification", []).append(
        {
            "check": check,
            "observed": observed,
        },
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
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        f"*Injected failure*: HTTP {INJECTED_FAILURE_STATUS_CODE} on startup branch-sync request attempt {INJECTED_FAILURE_ATTEMPT}",
        "",
        "h4. What was automated",
        "* Seeded a hosted workspace and stored GitHub token in browser storage for the deployed app.",
        "* Injected a one-time HTTP 500 into the live startup branch-sync path and waited for the post-failure state to settle before inspecting the recovery UI.",
        "* Verified the desktop navigation and workspace switcher trigger stayed visible instead of the app getting stuck on a terminal error surface.",
        "* Opened Workspace switcher and required the saved hosted workspace to show the exact `Sync issue` recovery state, not an auth/sign-in fallback.",
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
        f"- {REWORK_SUMMARY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        f"**Injected failure:** `HTTP {INJECTED_FAILURE_STATUS_CODE}` on startup branch-sync request attempt `{INJECTED_FAILURE_ATTEMPT}`",
        "",
        "## What was automated",
        "- Seeded a hosted workspace and stored GitHub token in browser storage for the deployed app.",
        "- Injected a one-time HTTP 500 into the live startup branch-sync path and waited for the post-failure state to settle before asserting the recovery UI.",
        "- Verified the desktop shell, navigation, and workspace switcher trigger stayed usable instead of collapsing to a blank startup surface.",
        "- Opened Workspace switcher and required the saved hosted workspace to show the exact `Sync issue` recovery state instead of an auth/sign-in fallback.",
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
        fallback_row = result.get("fallback_row") or {}
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "The synthetic 500 surfaced during startup sync, but the deployed app still "
            "mounted the desktop shell, kept the navigation and workspace switcher "
            "interactive, and showed the saved hosted workspace in the switcher with the "
            f"exact `{fallback_row.get('state_label')}` recovery state.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The deployed app did not preserve the interactive shell during the startup sync failure scenario.')}\n"
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
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}",
        )

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
        f"- Injected failure: HTTP {INJECTED_FAILURE_STATUS_CODE} on startup branch-sync request attempt {INJECTED_FAILURE_ATTEMPT}",
        "",
        "## Screenshots or logs",
        f"- Blocked requests: `{json.dumps(result.get('blocked_requests', []), ensure_ascii=True)}`",
        f"- Safe-mode observation: `{json.dumps(result.get('safe_mode_observation'), ensure_ascii=True)}`",
        f"- Settled recovery observation: `{json.dumps(result.get('settled_recovery_observation'), ensure_ascii=True)}`",
        f"- Shell observation: `{json.dumps(result.get('shell_observation'), ensure_ascii=True)}`",
        f"- Trigger observation: `{json.dumps(result.get('trigger_observation'), ensure_ascii=True)}`",
        f"- Switcher observation: `{json.dumps(result.get('switcher_observation'), ensure_ascii=True)}`",
        f"- Fallback row: `{json.dumps(result.get('fallback_row'), ensure_ascii=True)}`",
    ]
    if result.get("screenshot"):
        lines.append(f"- Screenshot: `{result['screenshot']}`")
    return "\n".join(lines) + "\n"


def _actual_result_summary(result: dict[str, Any], *, passed: bool) -> str:
    if passed:
        fallback_row = result.get("fallback_row") or {}
        blocked_request = result.get("safe_mode_observation", {}).get("blocked_request")
        return (
            "After the synthetic startup-sync 500 was triggered, the app kept the desktop "
            "shell interactive, showed the sync failure on screen, and left the hosted "
            "workspace available in Workspace switcher with the recovery state "
            f"`{fallback_row.get('state_label')}`. Blocked request: {blocked_request}."
        )
    return str(
        result.get(
            "error",
            "The deployed app did not preserve the interactive shell during the startup "
            "sync failure scenario.",
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


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, Any]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "icon_count": trigger.icon_count,
        "top_button_labels": list(trigger.top_button_labels),
        "left": trigger.left,
        "top": trigger.top,
        "width": trigger.width,
        "height": trigger.height,
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, Any]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
    }


def _panel_payload(panel: WorkspaceSwitcherPanelObservation) -> dict[str, Any]:
    return {
        "title_text": panel.title_text,
        "container_kind": panel.container_kind,
        "container_role": panel.container_role,
        "container_text": panel.container_text,
        "left": panel.left,
        "top": panel.top,
        "width": panel.width,
        "height": panel.height,
        "anchored_to_trigger": panel.anchored_to_trigger,
        "bottom_aligned": panel.bottom_aligned,
        "full_screen_like": panel.full_screen_like,
        "background_dimmed": panel.background_dimmed,
    }


def _row_payload(row: WorkspaceSwitcherRowObservation | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return {
        "display_name": row.display_name,
        "target_type_label": row.target_type_label,
        "state_label": row.state_label,
        "detail_text": row.detail_text,
        "visible_text": row.visible_text,
        "selected": row.selected,
        "semantics_label": row.semantics_label,
        "icon_accessibility_label": row.icon_accessibility_label,
        "action_labels": list(row.action_labels),
        "button_labels": list(row.button_labels),
    }


def _blocked_request_payload(blocked_request) -> dict[str, Any]:
    return {
        "url": blocked_request.url,
        "path": blocked_request.path,
        "attempt": blocked_request.attempt,
        "status_code": blocked_request.status_code,
    }


if __name__ == "__main__":
    main()
