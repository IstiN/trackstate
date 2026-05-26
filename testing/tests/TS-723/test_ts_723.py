from __future__ import annotations

from dataclasses import asdict
import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.trackstate_tracker_page import (  # noqa: E402
    TrackStateTrackerPage,
    WorkspaceRestoreMessageObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.ts723_workspace_restore_runtime import (  # noqa: E402
    Ts723WorkspaceRestoreRuntime,
    WorkspaceRestoreConsoleEvent,
)

TICKET_KEY = "TS-723"
TEST_CASE_TITLE = (
    "Startup restoration - recency-based fallback for invalid last-active workspace"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-723/test_ts_723.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts723_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts723_failure.png"

REQUEST_STEPS = [
    "Launch the application.",
    "Monitor the startup sequence and WorkspaceSessionCoordinator logs.",
    "Observe the non-blocking message displayed upon reaching the shell.",
    "Verify which workspace is currently active in the switcher trigger.",
]
EXPECTED_RESULT = (
    "The app skips W1, displays a message naming W1 and the reason for the skip, "
    "and automatically opens W2. The user is not routed to Settings because a "
    "valid fallback (W2) was found."
)
HOSTED_TARGET = "IstiN/trackstate-setup"
DEFAULT_BRANCH = "main"
OLDEST_WRITE_BRANCH = "fix/readme-missing-file-404"
INVALID_LOCAL_TARGET = "/tmp/ts723-missing-w1"
W1_DISPLAY_NAME = "W1 invalid workspace"
W2_DISPLAY_NAME = "W2 hosted workspace"
W3_DISPLAY_NAME = "W3 oldest workspace"
WORKSPACE_STORAGE_KEYS = (
    "trackstate.workspaceProfiles.state",
    "flutter.trackstate.workspaceProfiles.state",
)
SHELL_NAVIGATION_LABELS = (
    "Dashboard",
    "Board",
    "JQL Search",
    "Hierarchy",
    "Settings",
)
SETTINGS_SURFACE_MARKERS = (
    "Project settings administration",
    "Saved workspaces",
    "Repository access settings",
)
CONSOLE_INTERESTING_FRAGMENTS = (
    "workspace",
    "restore",
    "saved",
    "repository path",
    "local",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": "",
        "repository": "",
        "repository_ref": "",
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "preloaded_workspace_state": _workspace_state(),
        "steps": [],
        "human_verification": [],
    }

    try:
        config = load_live_setup_test_config()
        service = LiveSetupRepositoryService(config=config)
        token = service.token
        workspace_state = _workspace_state()
        result.update(
            {
                "app_url": config.app_url,
                "repository": service.repository,
                "repository_ref": service.ref,
                "preloaded_workspace_state": workspace_state,
            },
        )
        if not token:
            raise RuntimeError(
                "TS-723 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        runtime = Ts723WorkspaceRestoreRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
        )

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            try:
                runtime_state = tracker_page.open()
                result["runtime_state"] = runtime_state.kind
                result["runtime_body_text"] = runtime_state.body_text

                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation"] = shell_observation
                if runtime_state.kind != "ready" or not bool(
                    shell_observation["shell_ready"],
                ):
                    observed = (
                        "The deployed app did not reach the interactive shell after the "
                        "saved workspace preload was injected.\n"
                        f"Observed runtime state: {runtime_state.kind}\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}"
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=observed,
                    )
                    _record_human_verification(
                        result,
                        check=(
                            "Viewed the deployed app startup after preloading W1 as an "
                            "invalid local workspace and W2/W3 as hosted workspaces."
                        ),
                        observed=(
                            "The visible experience did not reach the interactive shell.\n"
                            f"Visible body text: {_snippet(str(shell_observation.get('body_text', '')))}"
                        ),
                    )
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the interactive "
                        "tracker shell while restoring the preloaded workspaces.\n"
                        f"Observed runtime state: {runtime_state.kind}\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
                    )

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the deployed TrackState app with W1 preloaded as the "
                        "active saved workspace, plus W2 and W3 as older hosted fallbacks."
                    ),
                )

                console_events = [asdict(event) for event in runtime.console_events]
                interesting_console_events = _interesting_console_events(
                    runtime.console_events,
                )
                result["console_events"] = console_events
                result["interesting_console_events"] = [
                    asdict(event) for event in interesting_console_events
                ]
                result["page_errors"] = list(runtime.page_errors)
                if runtime.page_errors:
                    observed = _console_summary(
                        interesting_console_events=interesting_console_events,
                        page_errors=runtime.page_errors,
                    )
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=observed,
                    )
                    raise AssertionError(
                        "Step 2 failed: startup restoration surfaced page errors while "
                        "restoring the saved workspaces.\n"
                        f"{observed}",
                    )

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=_console_summary(
                        interesting_console_events=interesting_console_events,
                        page_errors=runtime.page_errors,
                    ),
                )

                message_observation = tracker_page.observe_workspace_restore_message(
                    workspace_name=W1_DISPLAY_NAME,
                )
                result["restore_message_observation"] = _restore_message_payload(
                    message_observation,
                )
                _assert_restore_message(message_observation)

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Observed the visible startup restore banner in the shell: "
                        f"{message_observation.message_text!r}"
                    ),
                )

                switcher_observation = tracker_page.observe_workspace_switcher_trigger()
                result["switcher_observation"] = _switcher_payload(switcher_observation)
                _assert_switcher_state(
                    switcher_observation=switcher_observation,
                    shell_observation=shell_observation,
                )

                storage_snapshot = runtime.storage_snapshot()
                result["storage_snapshot"] = storage_snapshot
                persisted_workspace_state = _decode_workspace_state(storage_snapshot)
                result["persisted_workspace_state"] = persisted_workspace_state
                _assert_persisted_active_workspace(persisted_workspace_state)

                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "The workspace switcher trigger and persisted workspace state both "
                        f"pointed to W2. switcher_aria_label={switcher_observation.aria_label!r}; "
                        f"persisted_active_workspace={persisted_workspace_state.get('activeWorkspaceId')!r}"
                    ),
                )

                _record_human_verification(
                    result,
                    check=(
                        "Viewed the shell as a user after startup and confirmed the app "
                        "stayed on the tracker shell instead of redirecting to Settings."
                    ),
                    observed=(
                        f"visible_navigation_labels={shell_observation['visible_navigation_labels']}; "
                        f"settings_surface_visible={any(marker in switcher_observation.body_text for marker in SETTINGS_SURFACE_MARKERS)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the non-blocking restore message shown after shell startup."
                    ),
                    observed=message_observation.message_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the workspace switcher trigger exactly as the user sees it "
                        "in the header."
                    ),
                    observed=(
                        f"aria_label={switcher_observation.aria_label!r}; "
                        f"visible_text={switcher_observation.visible_text!r}"
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception as error:
                result.setdefault("error", _format_error(error))
                result.setdefault("traceback", traceback.format_exc())
                if not FAILURE_SCREENSHOT_PATH.exists():
                    tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-723 passed")


def _workspace_state() -> dict[str, object]:
    w1_id = f"local:{INVALID_LOCAL_TARGET}@{DEFAULT_BRANCH}"
    w2_id = f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}"
    w3_id = f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}:{OLDEST_WRITE_BRANCH}"
    return {
        "activeWorkspaceId": w1_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": w1_id,
                "displayName": W1_DISPLAY_NAME,
                "targetType": "local",
                "target": INVALID_LOCAL_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "customDisplayName": W1_DISPLAY_NAME,
                "lastOpenedAt": "2026-05-14T11:00:00.000Z",
            },
            {
                "id": w2_id,
                "displayName": W2_DISPLAY_NAME,
                "targetType": "hosted",
                "target": HOSTED_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "customDisplayName": W2_DISPLAY_NAME,
                "lastOpenedAt": "2026-05-14T10:00:00.000Z",
            },
            {
                "id": w3_id,
                "displayName": W3_DISPLAY_NAME,
                "targetType": "hosted",
                "target": HOSTED_TARGET,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": OLDEST_WRITE_BRANCH,
                "customDisplayName": W3_DISPLAY_NAME,
                "lastOpenedAt": "2026-05-14T09:00:00.000Z",
            },
        ],
    }


def _assert_restore_message(
    observation: WorkspaceRestoreMessageObservation,
) -> None:
    expected_prefix = f"Skipped {W1_DISPLAY_NAME} during restore."
    if expected_prefix not in observation.message_text:
        raise AssertionError(
            "Step 3 failed: the visible non-blocking restore message did not name "
            "the skipped W1 workspace.\n"
            f"Expected prefix: {expected_prefix}\n"
            f"Observed message: {observation.message_text}\n"
            f"Observed body text:\n{observation.body_text}",
        )
    reason = observation.message_text.replace(expected_prefix, "", 1).strip()
    if not reason or reason.lower() == "close":
        raise AssertionError(
            "Step 3 failed: the visible non-blocking restore message did not "
            "include a clear reason for skipping W1.\n"
            f"Observed message: {observation.message_text}\n"
            f"Observed body text:\n{observation.body_text}",
        )


def _assert_switcher_state(
    *,
    switcher_observation: WorkspaceSwitcherTriggerObservation,
    shell_observation: dict[str, object],
) -> None:
    if W2_DISPLAY_NAME not in switcher_observation.aria_label:
        raise AssertionError(
            "Step 4 failed: the workspace switcher trigger did not show W2 as the "
            "active workspace after startup recovery.\n"
            f"Observed switcher aria-label: {switcher_observation.aria_label}\n"
            f"Observed switcher text: {switcher_observation.visible_text}\n"
            f"Observed body text:\n{switcher_observation.body_text}",
        )
    if "Hosted" not in switcher_observation.aria_label:
        raise AssertionError(
            "Step 4 failed: the workspace switcher trigger did not expose W2 as a "
            "hosted workspace.\n"
            f"Observed switcher aria-label: {switcher_observation.aria_label}",
        )
    if any(marker in switcher_observation.body_text for marker in SETTINGS_SURFACE_MARKERS):
        raise AssertionError(
            "Expected result failed: startup recovery routed the user into Settings "
            "instead of keeping the shell on the restored workspace.\n"
            f"Observed body text:\n{switcher_observation.body_text}",
        )
    if not bool(shell_observation.get("shell_ready")):
        raise AssertionError(
            "Expected result failed: the shell was not interactive after the W2 "
            "fallback was selected.\n"
            f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
        )


def _assert_persisted_active_workspace(
    persisted_workspace_state: dict[str, object],
) -> None:
    expected_active_workspace = f"hosted:{HOSTED_TARGET.lower()}@{DEFAULT_BRANCH}"
    observed_active_workspace = persisted_workspace_state.get("activeWorkspaceId")
    if observed_active_workspace != expected_active_workspace:
        raise AssertionError(
            "Step 4 failed: the persisted saved-workspace state did not promote W2 "
            "to the active workspace after startup recovery.\n"
            f"Expected activeWorkspaceId: {expected_active_workspace}\n"
            f"Observed activeWorkspaceId: {observed_active_workspace}\n"
            f"Observed persisted workspace state:\n"
            f"{json.dumps(persisted_workspace_state, indent=2, sort_keys=True)}",
        )


def _interesting_console_events(
    events: list[WorkspaceRestoreConsoleEvent],
) -> list[WorkspaceRestoreConsoleEvent]:
    interesting: list[WorkspaceRestoreConsoleEvent] = []
    for event in events:
        normalized_text = event.text.lower()
        if any(fragment in normalized_text for fragment in CONSOLE_INTERESTING_FRAGMENTS):
            interesting.append(event)
    return interesting


def _console_summary(
    *,
    interesting_console_events: list[WorkspaceRestoreConsoleEvent],
    page_errors: list[str],
) -> str:
    console_lines = [
        f"[{event.level}] {event.text}"
        for event in interesting_console_events[:8]
    ]
    if not console_lines:
        console_lines = ["<no workspace-related console events captured>"]
    error_lines = page_errors[:8] if page_errors else ["<no page errors>"]
    return (
        "Monitored browser console/page errors during startup.\n"
        f"Interesting console events:\n{_join_lines(console_lines)}\n"
        f"Page errors:\n{_join_lines(error_lines)}"
    )


def _decode_workspace_state(storage_snapshot: dict[str, str | None]) -> dict[str, object]:
    prefixed_value = storage_snapshot.get("flutter.trackstate.workspaceProfiles.state")
    raw_value = prefixed_value or storage_snapshot.get("trackstate.workspaceProfiles.state")
    if raw_value is None:
        raise AssertionError(
            "Expected result failed: the browser did not retain any persisted "
            "workspace state after startup recovery.",
        )
    decoded = json.loads(raw_value)
    if isinstance(decoded, str):
        decoded = json.loads(decoded)
    if not isinstance(decoded, dict):
        raise AssertionError(
            "Expected result failed: the persisted workspace state was not a JSON object.\n"
            f"Observed value: {raw_value}",
        )
    return decoded


def _restore_message_payload(
    observation: WorkspaceRestoreMessageObservation,
) -> dict[str, object]:
    return {
        "message_text": observation.message_text,
        "body_text": observation.body_text,
    }


def _switcher_payload(
    observation: WorkspaceSwitcherTriggerObservation,
) -> dict[str, object]:
    return {
        "aria_label": observation.aria_label,
        "visible_text": observation.visible_text,
        "body_text": observation.body_text,
    }


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if not isinstance(steps, list):
        raise AssertionError("Result payload `steps` must be a list.")
    steps.append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        },
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    if not isinstance(checks, list):
        raise AssertionError("Result payload `human_verification` must be a list.")
    checks.append({"check": check, "observed": observed})


def _write_pass_outputs(result: dict[str, object]) -> None:
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

    restore_message = _restore_message_text(result)
    switcher_label = _switcher_aria_label(result)
    active_workspace_id = _persisted_active_workspace_id(result)
    console_summary = _result_console_summary(result)
    screenshot_path = str(result.get("screenshot", SUCCESS_SCREENSHOT_PATH))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        "* Step 1: Opened the deployed TrackState app with three preloaded saved workspaces where W1 was the active local workspace pointing at an invalid path, W2 was the next most recent hosted workspace, and W3 was the oldest hosted workspace.",
        "* Step 2: Monitored startup console/page-error output while the app restored the preloaded workspace state.",
        f"* Step 3: Verified the visible non-blocking shell message showed {jira_inline(restore_message)} after W1 was skipped.",
        f"* Step 4: Verified the workspace switcher trigger and persisted saved-workspace state both promoted W2 as active ({jira_inline(active_workspace_id)}).",
        "",
        "h4. Human-style verification",
        "* Viewed the post-startup shell as a user and confirmed the app stayed on the interactive tracker shell instead of routing to Project Settings.",
        f"* Viewed the visible restore banner text in the shell: {jira_inline(restore_message)}.",
        f"* Viewed the header workspace switcher trigger text/semantics: {jira_inline(switcher_label)}.",
        "",
        "h4. Result",
        "* Step 1 passed: the deployed app reached the interactive shell.",
        "* Step 2 passed: startup recovery completed without page errors while logs were monitored.",
        "* Step 3 passed: the shell displayed a non-blocking restore message naming W1 and explaining why it was skipped.",
        "* Step 4 passed: W2 became the active workspace in the switcher trigger and in persisted saved-workspace state.",
        "* The observed behavior matched the expected result.",
        "",
        "h4. Startup log summary",
        "{code}",
        console_summary,
        "{code}",
        "",
        "h4. Screenshot",
        str(screenshot_path),
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app with W1 preloaded as the active invalid local workspace plus W2/W3 as older hosted workspaces.",
        "- Monitored startup console/page-error output during workspace restoration.",
        f"- Verified the visible shell message showed `{restore_message}` after W1 was skipped.",
        f"- Verified the workspace switcher trigger and persisted saved-workspace state both promoted W2 as active (`{active_workspace_id}`).",
        "",
        "## Human-style verification",
        "- Observed the post-startup experience stay on the interactive shell instead of routing into Project Settings.",
        f"- Observed the user-facing restore banner text: `{restore_message}`.",
        f"- Observed the header workspace switcher trigger semantics/text: `{switcher_label}`.",
        "",
        "## Result",
        "- Step 1 passed: the deployed app reached the interactive shell.",
        "- Step 2 passed: startup recovery completed without page errors while logs were monitored.",
        "- Step 3 passed: the shell displayed a non-blocking restore message naming W1 and the skip reason.",
        "- Step 4 passed: W2 became the active workspace in both the switcher trigger and persisted state.",
        "- The observed behavior matched the expected result.",
        "",
        "## Startup log summary",
        "```text",
        console_summary,
        "```",
        "",
        "## Screenshot",
        screenshot_path,
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = str(result.get("error", "AssertionError: unknown failure"))
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            },
        )
        + "\n",
        encoding="utf-8",
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. Failed step details",
        *_jira_step_lines(result),
        "",
        "h4. Human-style verification",
        *_jira_human_verification_lines(result),
        "",
        "h4. Error",
        "{code}",
        error_message,
        "{code}",
        "",
        "h4. Environment",
        f"* URL: {result.get('app_url', '<missing>')}",
        f"* Repository: {result.get('repository', '<missing>')} @ {result.get('repository_ref', '<missing>')}",
        f"* Browser: {result.get('browser', '<missing>')}",
        f"* OS: {result.get('os', '<missing>')}",
        f"* Screenshot: {result.get('screenshot', FAILURE_SCREENSHOT_PATH)}",
    ]
    if result.get("traceback"):
        jira_lines.extend(
            [
                "",
                "h4. Stack trace",
                "{code}",
                str(result["traceback"]),
                "{code}",
            ],
        )

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## Failed step details",
        *_markdown_step_lines(result),
        "",
        "## Human-style verification",
        *_markdown_human_verification_lines(result),
        "",
        "## Error",
        "```text",
        error_message,
        "```",
        "",
        "## Environment",
        f"- URL: {result.get('app_url', '<missing>')}",
        f"- Repository: {result.get('repository', '<missing>')} @ {result.get('repository_ref', '<missing>')}",
        f"- Browser: {result.get('browser', '<missing>')}",
        f"- OS: {result.get('os', '<missing>')}",
        f"- Screenshot: {result.get('screenshot', FAILURE_SCREENSHOT_PATH)}",
    ]
    if result.get("traceback"):
        markdown_lines.extend(
            [
                "",
                "## Stack trace",
                "```text",
                str(result["traceback"]),
                "```",
            ],
        )

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _bug_description(result: dict[str, object]) -> str:
    storage_snapshot = result.get("storage_snapshot")
    switcher_observation = result.get("switcher_observation")
    restore_message_observation = result.get("restore_message_observation")
    console_summary = _result_console_summary(result)
    screenshot = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    body_text = (
        _safe_dict_get(switcher_observation, "body_text")
        or _safe_dict_get(restore_message_observation, "body_text")
        or str(result.get("runtime_body_text", ""))
    )

    lines = [
        f"# {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## Summary",
        EXPECTED_RESULT,
        "",
        "## Exact steps to reproduce",
        *_bug_annotated_steps(result),
        "",
        "## Actual vs Expected",
        f"- **Expected:** {EXPECTED_RESULT}",
        (
            "- **Actual:** "
            + (
                _first_failure_observation(result)
                or "The live startup restoration flow did not produce the expected shell/message/active-workspace state."
            )
        ),
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback") or result.get("error") or "<missing>"),
        "```",
        "",
        "## Environment details",
        f"- URL: {result.get('app_url', '<missing>')}",
        f"- Repository: {result.get('repository', '<missing>')} @ {result.get('repository_ref', '<missing>')}",
        f"- Browser: {result.get('browser', '<missing>')}",
        f"- OS: {result.get('os', '<missing>')}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Visible state at failure",
        "```text",
        body_text or "<no body text captured>",
        "```",
        "",
        "## Screenshots or logs",
        f"- Screenshot: {screenshot}",
        "```text",
        console_summary,
        "```",
    ]
    if storage_snapshot:
        lines.extend(
            [
                "",
                "## Persisted storage snapshot",
                "```json",
                json.dumps(storage_snapshot, indent=2, sort_keys=True),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _jira_step_lines(result: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for step_number, action in enumerate(REQUEST_STEPS, start=1):
        step = _step_payload(result, step_number)
        if step is None:
            lines.append(f"* Step {step_number}: ⏭️ Not reached. {action}")
            continue
        status = step["status"]
        icon = "✅" if status == "passed" else "❌"
        lines.append(
            f"* Step {step_number}: {icon} {action} Observed: {jira_inline(str(step['observed']))}",
        )
    return lines


def _markdown_step_lines(result: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for step_number, action in enumerate(REQUEST_STEPS, start=1):
        step = _step_payload(result, step_number)
        if step is None:
            lines.append(f"- Step {step_number}: ⏭️ Not reached. {action}")
            continue
        status = step["status"]
        icon = "✅" if status == "passed" else "❌"
        lines.append(f"- Step {step_number}: {icon} {action} Observed: {step['observed']}")
    return lines


def _jira_human_verification_lines(result: dict[str, object]) -> list[str]:
    checks = result.get("human_verification")
    if not isinstance(checks, list) or not checks:
        return ["* No additional human-style verification notes were captured before failure."]
    return [
        f"* {jira_inline(str(item.get('check', 'Check')))} — {jira_inline(str(item.get('observed', '')))}"
        for item in checks
        if isinstance(item, dict)
    ]


def _markdown_human_verification_lines(result: dict[str, object]) -> list[str]:
    checks = result.get("human_verification")
    if not isinstance(checks, list) or not checks:
        return ["- No additional human-style verification notes were captured before failure."]
    return [
        f"- {item.get('check', 'Check')} — {item.get('observed', '')}"
        for item in checks
        if isinstance(item, dict)
    ]


def _bug_annotated_steps(result: dict[str, object]) -> list[str]:
    lines: list[str] = []
    for step_number, action in enumerate(REQUEST_STEPS, start=1):
        step = _step_payload(result, step_number)
        if step is None:
            lines.append(f"{step_number}. ⏭️ {action} Not reached.")
            continue
        status = step["status"]
        icon = "✅" if status == "passed" else "❌"
        lines.append(f"{step_number}. {icon} {action} Observed: {step['observed']}")
    return lines


def _step_payload(
    result: dict[str, object],
    step_number: int,
) -> dict[str, object] | None:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return step
    return None


def _first_failure_observation(result: dict[str, object]) -> str | None:
    steps = result.get("steps")
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("status") == "failed":
            return str(step.get("observed", ""))
    return None


def _restore_message_text(result: dict[str, object]) -> str:
    return _safe_dict_get(result.get("restore_message_observation"), "message_text") or "<missing>"


def _switcher_aria_label(result: dict[str, object]) -> str:
    return _safe_dict_get(result.get("switcher_observation"), "aria_label") or "<missing>"


def _persisted_active_workspace_id(result: dict[str, object]) -> str:
    persisted = result.get("persisted_workspace_state")
    return _safe_dict_get(persisted, "activeWorkspaceId") or "<missing>"


def _result_console_summary(result: dict[str, object]) -> str:
    interesting = result.get("interesting_console_events")
    page_errors = result.get("page_errors")
    events: list[WorkspaceRestoreConsoleEvent] = []
    if isinstance(interesting, list):
        for item in interesting:
            if isinstance(item, dict):
                events.append(
                    WorkspaceRestoreConsoleEvent(
                        level=str(item.get("level", "")),
                        text=str(item.get("text", "")),
                    ),
                )
    errors = [str(item) for item in page_errors] if isinstance(page_errors, list) else []
    return _console_summary(
        interesting_console_events=events,
        page_errors=errors,
    )


def _safe_dict_get(payload: object, key: str) -> str | None:
    if isinstance(payload, dict):
        value = payload.get(key)
        if value is None:
            return None
        return str(value)
    return None


def _join_lines(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)


def _format_error(error: Exception) -> str:
    return f"{type(error).__name__}: {error}"


def _snippet(value: str, *, limit: int = 280) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def jira_inline(value: str) -> str:
    escaped = value.replace("{", "\\{").replace("}", "\\}")
    return f"{{code}}{escaped}{{code}}"


if __name__ == "__main__":
    main()
