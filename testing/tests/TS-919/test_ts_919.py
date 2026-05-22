from __future__ import annotations

import json
import platform
import shutil
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherRowObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-919"
TEST_CASE_TITLE = (
    "Local Unavailable workspace action label shows Re-authenticate or Retry"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-919/test_ts_919.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
LOCAL_TARGET = "/tmp/trackstate-ts919-workspace"
LOCAL_DISPLAY_NAME = "Restorable local workspace"
HOSTED_DISPLAY_NAME = "Hosted setup workspace"
LINKED_BUGS = ["TS-915"]
SHELL_NAVIGATION_LABELS = ("Dashboard", "Board", "JQL Search", "Hierarchy", "Settings")
ACCEPTED_ACTION_LABELS = ("Re-authenticate", "Retry")
DISALLOWED_ACTION_LABELS = ("Open",)
REWORK_SUMMARY = (
    "Moved the workspace-switcher trigger and unavailable-row inspection behind "
    "`LiveWorkspaceSwitcherPage` public APIs so TS-919 no longer reaches into raw "
    "Playwright session internals."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts919_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts919_failure.png"

REQUEST_STEPS = [
    "Open the Workspace switcher from the application header.",
    "Locate the row for the unavailable local workspace.",
    "Inspect the text on the primary action button for that row.",
]
EXPECTED_RESULT = (
    "The button label is 'Re-authenticate' or 'Retry'. It is not labeled as 'Open'."
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)
    _remove_local_workspace_repository()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "linked_bugs": LINKED_BUGS,
        "steps": [],
        "human_verification": [],
    }
    page: LiveWorkspaceSwitcherPage | None = None

    try:
        config = load_live_setup_test_config()
        result["app_url"] = config.app_url

        service = LiveSetupRepositoryService(config=config)
        token = service.token
        if not token:
            raise RuntimeError(
                "TS-919 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        result["repository"] = service.repository
        result["repository_ref"] = service.ref

        workspace_state = _workspace_state(service.repository)
        result["preloaded_workspace_state"] = workspace_state

        runtime = StoredWorkspaceProfilesRuntime(
            repository=config.repository,
            token=token,
            workspace_state=workspace_state,
            workspace_token_profile_ids=(
                f"hosted:{service.repository.lower()}@{DEFAULT_BRANCH}",
            ),
        )
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: runtime,
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime_observation = tracker_page.open()
                page.set_viewport(**DESKTOP_VIEWPORT)
                result["runtime_state"] = runtime_observation.kind
                result["runtime_body_text"] = runtime_observation.body_text
                shell_observation = tracker_page.observe_interactive_shell(
                    SHELL_NAVIGATION_LABELS,
                )
                result["shell_observation"] = shell_observation
                if runtime_observation.kind != "ready" or not bool(
                    shell_observation.get("shell_ready"),
                ):
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the interactive "
                        "shell with the hosted-workspace preload.\n"
                        f"Observed runtime state: {runtime_observation.kind}\n"
                        f"Observed shell state:\n{json.dumps(shell_observation, indent=2)}",
                    )

                try:
                    page.dismiss_connection_banner()
                except Exception:
                    pass

                trigger_before = page.observe_trigger(timeout_ms=20_000)
                result["trigger_before_open"] = _trigger_payload(trigger_before)
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live shell before opening Workspace switcher to confirm "
                        "the hosted workspace was visibly active in the header."
                    ),
                    observed=(
                        f"trigger_label={trigger_before.semantic_label!r}; "
                        f"trigger_workspace_type={trigger_before.workspace_type!r}"
                    ),
                )

                switcher = page.open_and_observe(timeout_ms=20_000)
                local_row = page.observe_saved_workspace_row(
                    display_name=LOCAL_DISPLAY_NAME,
                    target_path=LOCAL_TARGET,
                    target_type_label="Local",
                    expected_state_label="Unavailable",
                    accepted_action_labels=ACCEPTED_ACTION_LABELS,
                    disallowed_action_labels=DISALLOWED_ACTION_LABELS,
                    timeout_ms=20_000,
                )

                result["switcher_observation"] = _switcher_payload(switcher)
                result["local_row"] = _row_payload(local_row)

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Opened the Workspace switcher from the application header.\n"
                        f"row_count={switcher.row_count}; "
                        f"switcher_text={switcher.switcher_text!r}"
                    ),
                )

                try:
                    _assert_unavailable_local_row(
                        local_row=local_row,
                        trigger=trigger_before,
                        switcher=switcher,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=str(error),
                    )
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed="Not reached because the unavailable local workspace row was not exposed in step 2.",
                    )
                    raise

                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Located the local workspace row in the visible `Unavailable` state.\n"
                        f"local_row={json.dumps(_row_payload(local_row), indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened Workspace switcher and visually confirmed the local "
                        "workspace row showed the unavailable state in the switcher surface."
                    ),
                    observed=(
                        f"local_row={json.dumps(_row_payload(local_row), ensure_ascii=True)}; "
                        f"switcher_text={switcher.switcher_text!r}"
                    ),
                )

                observed_action_label = _workspace_action_label(local_row)
                result["observed_action_label"] = observed_action_label

                try:
                    _assert_expected_action_label(
                        local_row=local_row,
                        observed_action_label=observed_action_label,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=REQUEST_STEPS[2],
                        observed=str(error),
                    )
                    raise

                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "Inspected the visible primary action label for the unavailable "
                        "workspace row.\n"
                        f"observed_action_label={observed_action_label!r}\n"
                        f"all_action_labels={json.dumps(list(local_row.action_labels) if local_row else [], indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Read the visible action text on the unavailable saved workspace row "
                        "as a user would in the switcher."
                    ),
                    observed=(
                        f"primary_action_label={observed_action_label!r}; "
                        f"allowed_labels={ACCEPTED_ACTION_LABELS!r}; "
                        f"disallowed_labels={DISALLOWED_ACTION_LABELS!r}"
                    ),
                )
            except Exception:
                if page is not None:
                    try:
                        if not FAILURE_SCREENSHOT_PATH.exists():
                            page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                        result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    except Exception as screenshot_error:
                        result["screenshot_error"] = (
                            f"{type(screenshot_error).__name__}: {screenshot_error}"
                        )
                raise

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    finally:
        _remove_local_workspace_repository()

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _workspace_state(repository: str) -> dict[str, object]:
    local_id = f"local:{LOCAL_TARGET}@{DEFAULT_BRANCH}"
    hosted_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    return {
        "activeWorkspaceId": hosted_id,
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
                "lastOpenedAt": "2026-05-22T00:00:00.000Z",
            },
            {
                "id": hosted_id,
                "displayName": HOSTED_DISPLAY_NAME,
                "customDisplayName": HOSTED_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-21T23:55:00.000Z",
            },
        ],
    }


def _remove_local_workspace_repository() -> None:
    shutil.rmtree(LOCAL_TARGET, ignore_errors=True)


def _find_named_local_row(
    switcher: WorkspaceSwitcherObservation,
) -> WorkspaceSwitcherRowObservation | None:
    for row in switcher.rows:
        if (
            row.display_name == LOCAL_DISPLAY_NAME
            and row.target_type_label == "Local"
            and LOCAL_TARGET in row.detail_text
        ):
            return row
    return None


def _assert_unavailable_local_row(
    *,
    local_row: WorkspaceSwitcherRowObservation | None,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
) -> None:
    if local_row is None:
        raise AssertionError(
            "Step 2 failed: the Workspace switcher did not expose the local workspace row.\n"
            f"Observed trigger label: {trigger.semantic_label!r}\n"
            f"Observed rows: {[row.visible_text for row in switcher.rows]!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}"
        )
    if local_row.state_label != "Unavailable":
        raise AssertionError(
            "Step 2 failed: the local workspace row was not shown in the expected "
            "`Unavailable` state.\n"
            f"Observed local row: {json.dumps(_row_payload(local_row), indent=2)}"
        )

def _workspace_action_label(
    row: WorkspaceSwitcherRowObservation | None,
) -> str:
    if row is None:
        raise AssertionError(
            "Step 3 failed: the open workspace switcher did not expose a saved local "
            "workspace row with an actionable control.",
        )
    action_label = next(
        (
            label
            for label in row.action_labels
            if label and not label.startswith("Delete:")
        ),
        None,
    )
    if not action_label:
        raise AssertionError(
            "Step 3 failed: the unavailable local workspace row did not expose any "
            "visible primary action.\n"
            f"Observed row: {json.dumps(_row_payload(row), indent=2)}"
        )
    return action_label


def _assert_expected_action_label(
    *,
    local_row: WorkspaceSwitcherRowObservation | None,
    observed_action_label: str,
) -> None:
    if observed_action_label in DISALLOWED_ACTION_LABELS:
        raise AssertionError(
            "Step 3 failed: the unavailable local workspace row still exposed the stale "
            "`Open` label instead of a recovery action.\n"
            f"Observed action label: {observed_action_label!r}\n"
            f"Observed row: {json.dumps(_row_payload(local_row), indent=2)}"
        )
    if observed_action_label not in ACCEPTED_ACTION_LABELS:
        raise AssertionError(
            "Step 3 failed: the unavailable local workspace row exposed an unexpected "
            "primary action label.\n"
            f"Observed action label: {observed_action_label!r}\n"
            f"Accepted labels: {list(ACCEPTED_ACTION_LABELS)!r}\n"
            f"Observed row: {json.dumps(_row_payload(local_row), indent=2)}"
        )


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "icon_count": trigger.icon_count,
        "viewport_width": trigger.viewport_width,
        "viewport_height": trigger.viewport_height,
        "top_button_labels": list(trigger.top_button_labels),
    }


def _row_payload(row: WorkspaceSwitcherRowObservation | None) -> dict[str, object] | None:
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


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [_row_payload(row) for row in switcher.rows],
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
        raise TypeError("result['steps'] must be a list")
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
    verifications = result.setdefault("human_verification", [])
    if not isinstance(verifications, list):
        raise TypeError("result['human_verification'] must be a list")
    verifications.append({"check": check, "observed": observed})


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
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
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


def _build_jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    steps = result.get("steps", [])
    step_lines = [
        f"# Step {step['step']} *{step['status'].upper()}*: {step['action']}\n"
        f"Observed: {{code}}{step['observed']}{{code}}"
        for step in steps
        if isinstance(step, dict)
    ]
    verifications = result.get("human_verification", [])
    verification_lines = [
        f"* {item['check']} Observed: {{code}}{item['observed']}{{code}}"
        for item in verifications
        if isinstance(item, dict)
    ]
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: URL={result.get('app_url')} | Browser={result.get('browser')} | OS={result.get('os')}",
        f"*Viewport*: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        "",
        "h4. Automation checks",
        *step_lines,
        "",
        "h4. Real user-style verification",
        *verification_lines,
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        (
            "The unavailable saved local workspace row exposed a recovery action labeled "
            f"`{result.get('observed_action_label')}` instead of `Open`."
            if passed
            else str(result.get("error", "The unavailable workspace label did not match the expected recovery action."))
        ),
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


def _build_pr_body(result: dict[str, object], *, passed: bool) -> str:
    steps = result.get("steps", [])
    verifications = result.get("human_verification", [])
    lines = [
        f"## {TICKET_KEY} {'passed' if passed else 'failed'}",
        "",
        "## Rework summary",
        f"- {REWORK_SUMMARY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{result.get('app_url')}` · {result.get('browser')} · {result.get('os')}",
        f"**Viewport:** `{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        "",
        "## Automation checks",
    ]
    for step in steps:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"- Step {step['step']} **{step['status']}** — {step['action']}  \n"
            f"  Observed: `{step['observed']}`"
        )
    lines.extend(["", "## Real user-style verification"])
    for item in verifications:
        if not isinstance(item, dict):
            continue
        lines.append(f"- **{item['check']}** Observed: `{item['observed']}`")
    lines.extend(
        [
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Actual result",
            (
                "The unavailable saved local workspace row exposed a recovery action labeled "
                f"`{result.get('observed_action_label')}` instead of `Open`."
                if passed
                else str(result.get("error", "The unavailable workspace label did not match the expected recovery action."))
            ),
        ],
    )
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


def _build_response_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            f"{REWORK_SUMMARY}\n\n"
            "The live unavailable saved workspace row showed a recovery action label "
            f"of `{result.get('observed_action_label')}` and did not show `Open`.\n"
        )
    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{REWORK_SUMMARY}\n\n"
        f"{result.get('error', 'The unavailable workspace label did not match the expected recovery action.')}\n"
    )


def _build_bug_description(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    screenshot = result.get("screenshot")
    annotated_steps: list[str] = []
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
        status = str(matching.get("status", "failed")).lower()
        icon = "✅" if status == "passed" else "❌"
        annotated_steps.append(
            f"{index}. {icon} {action} Observed: {matching.get('observed', '')}"
        )

    actual_result = str(
        result.get(
            "error",
            "The unavailable workspace label did not match the expected recovery action.",
        ),
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
        "## Actual result",
        actual_result,
        "",
        "## Expected result",
        EXPECTED_RESULT,
        "",
        "## Environment details",
        f"- URL: {result.get('app_url')}",
        f"- Browser: {result.get('browser')}",
        f"- OS: {result.get('os')}",
        f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
        f"- Local workspace target: {LOCAL_TARGET}",
        f"- Run command: `{RUN_COMMAND}`",
        "",
        "## Observed state",
        f"- Trigger before opening switcher: `{json.dumps(result.get('trigger_before_open'), ensure_ascii=True)}`",
        f"- Local row: `{json.dumps(result.get('local_row'), ensure_ascii=True)}`",
        f"- Selected row: `{json.dumps(result.get('selected_row'), ensure_ascii=True)}`",
        f"- Observed action label: `{result.get('observed_action_label')}`",
        f"- Accepted action labels: `{list(ACCEPTED_ACTION_LABELS)}`",
        f"- Disallowed action labels: `{list(DISALLOWED_ACTION_LABELS)}`",
    ]
    if screenshot:
        lines.extend(["", "## Screenshots or logs", f"- Screenshot: `{screenshot}`"])
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
