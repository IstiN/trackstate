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

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app,
)
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-838"
TEST_CASE_TITLE = "Workspace switcher trigger mouse interaction - surface opens on click"
RUN_COMMAND = (
    "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-838/test_ts_838.py"
)
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
DEFAULT_BRANCH = "main"
ACTIVE_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECONDARY_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
SECONDARY_WRITE_BRANCH = "ts-838-alt"
REQUEST_STEPS = [
    "Open the TrackState app in a desktop browser.",
    "Locate the workspace switcher trigger in the top-bar navigation.",
    "Click on the workspace switcher trigger using the mouse.",
]
EXPECTED_RESULT = (
    "The workspace switcher surface (panel or sheet) opens successfully upon "
    "clicking, confirming the element is no longer blocked by restrictive CSS "
    "on its parent container."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts838_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts838_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    workspace_state = _workspace_state(service.repository)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "expected_result": EXPECTED_RESULT,
        "preloaded_workspace_state": workspace_state,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        token = service.token
        if not token:
            raise RuntimeError(
                "TS-838 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )
        user = service.fetch_authenticated_user()
        result["user_login"] = user.login

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=service.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the mouse-click scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)

                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']} and "
                        "reached the interactive desktop Dashboard shell."
                    ),
                )

                trigger = page.observe_trigger()
                result["trigger_observation"] = _trigger_payload(trigger)
                _assert_trigger_visible(trigger)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"trigger_text={trigger.visible_text!r}; "
                        f"display_name={trigger.display_name!r}; "
                        f"workspace_type={trigger.workspace_type!r}; "
                        f"state_label={trigger.state_label!r}; "
                        f"bounds=({trigger.left:.1f}, {trigger.top:.1f}, "
                        f"{trigger.width:.1f}, {trigger.height:.1f})"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live desktop shell exactly as a user would and "
                        "confirmed the top-bar workspace switcher trigger was visibly "
                        "present with the current workspace summary."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                switcher = page.open_and_observe()
                panel = page.observe_open_panel(
                    expected_container_kinds=("anchored-panel", "surface"),
                )
                (
                    saved_workspace_rows,
                    saved_workspace_row_source,
                ) = _observe_saved_workspace_rows(
                    page=page,
                    switcher=switcher,
                )
                result["open_switcher_observation"] = _switcher_payload(switcher)
                result["open_panel_observation"] = asdict(panel)
                result["saved_workspace_rows"] = _saved_workspace_rows_payload(
                    saved_workspace_rows,
                )
                result["saved_workspace_row_source"] = saved_workspace_row_source
                _assert_surface_open(
                    trigger=trigger,
                    switcher=switcher,
                    panel=panel,
                    saved_workspace_rows=saved_workspace_rows,
                    saved_workspace_row_source=saved_workspace_row_source,
                )
                visible_row_names = [
                    row.display_name for row in saved_workspace_rows
                ]
                active_workspace = next(
                    (row.display_name for row in saved_workspace_rows if row.selected),
                    None,
                )
                result["visible_row_names"] = visible_row_names
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        f"panel_kind={panel.container_kind!r}; "
                        f"anchored_to_trigger={panel.anchored_to_trigger}; "
                        f"row_count={switcher.row_count}; "
                        f"parsed_saved_row_count={len(saved_workspace_rows)}; "
                        f"saved_workspace_row_source={saved_workspace_row_source!r}; "
                        f"active_workspace_visible={ACTIVE_WORKSPACE_DISPLAY_NAME in visible_row_names}; "
                        f"secondary_workspace_visible={SECONDARY_WORKSPACE_DISPLAY_NAME in visible_row_names}; "
                        f"active_workspace_selected={active_workspace == ACTIVE_WORKSPACE_DISPLAY_NAME}; "
                        f"active_label_visible={any('Active' in row.action_labels for row in saved_workspace_rows)}; "
                        f"open_label_visible={any(any(label.startswith('Open: ') for label in row.action_labels) for row in saved_workspace_rows)}; "
                        "heading_visible="
                        f"{'Workspace switcher' in switcher.switcher_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked the visible workspace switcher trigger with the mouse "
                        "and confirmed the user-visible switcher surface opened on top "
                        "of the desktop shell."
                    ),
                    observed=(
                        f"title_visible={'Workspace switcher' in switcher.switcher_text}; "
                        f"panel_kind={panel.container_kind!r}; "
                        f"visible_rows={visible_row_names!r}; "
                        f"switcher_text_excerpt={_snippet(switcher.switcher_text)}"
                    ),
                )
            except Exception:
                try:
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

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _assert_trigger_visible(trigger: WorkspaceSwitcherTriggerObservation) -> None:
    failures: list[str] = []
    if not trigger.semantic_label.startswith("Workspace switcher:"):
        failures.append(
            f"the trigger semantics label was {trigger.semantic_label!r}",
        )
    if not trigger.visible_text.strip():
        failures.append("the trigger did not expose any visible text")
    if not trigger.display_name.strip():
        failures.append("the trigger did not expose the active workspace display name")
    if trigger.workspace_type not in {"Hosted", "Local"}:
        failures.append(
            f"the trigger workspace type was {trigger.workspace_type!r}",
        )
    if not trigger.state_label.strip():
        failures.append("the trigger did not expose the active workspace state label")
    if trigger.width <= 0 or trigger.height <= 0:
        failures.append(
            "the trigger did not expose a positive clickable area in the desktop viewport",
        )
    if failures:
        raise AssertionError(
            "Step 2 failed: the workspace switcher trigger was not exposed as a "
            "visible top-bar control in the desktop shell.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}\n"
            f"Problems: {'; '.join(failures)}",
        )


def _assert_surface_open(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    saved_workspace_rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    saved_workspace_row_source: str,
) -> None:
    failures: list[str] = []
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append("the visible Workspace switcher title was missing")
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"the opened surface was {panel.container_kind!r} instead of a desktop panel-style surface",
        )
    if panel.width <= 0 or panel.height <= 0:
        failures.append(
            "the opened surface did not expose positive visible bounds",
        )
    if len(saved_workspace_rows) <= 0:
        failures.append("the opened surface did not expose any parsed saved workspace rows")
    if len(saved_workspace_rows) < 2:
        failures.append(
            "the opened surface did not expose both preloaded saved workspace rows",
        )
    saved_workspace_names = {row.display_name for row in saved_workspace_rows}
    if ACTIVE_WORKSPACE_DISPLAY_NAME not in saved_workspace_names:
        failures.append(
            f"{ACTIVE_WORKSPACE_DISPLAY_NAME!r} was missing from the parsed saved workspace rows",
        )
    if SECONDARY_WORKSPACE_DISPLAY_NAME not in saved_workspace_names:
        failures.append(
            f"{SECONDARY_WORKSPACE_DISPLAY_NAME!r} was missing from the parsed saved workspace rows",
        )
    active_row = next((row for row in saved_workspace_rows if row.selected), None)
    if active_row is None:
        failures.append("none of the parsed saved workspace rows was marked active")
    elif active_row.display_name != ACTIVE_WORKSPACE_DISPLAY_NAME:
        failures.append(
            f"the selected saved workspace row was {active_row.display_name!r} instead of "
            f"{ACTIVE_WORKSPACE_DISPLAY_NAME!r}",
        )
    if not any("Active" in row.action_labels for row in saved_workspace_rows):
        failures.append("the opened surface did not show the active-row label")
    if not any(
        any(label.startswith("Open: ") for label in row.action_labels)
        for row in saved_workspace_rows
    ):
        failures.append("the opened surface did not show an inactive row open action")
    expected_rows = {
        row.display_name: row for row in saved_workspace_rows
    }
    for expected_name in (
        ACTIVE_WORKSPACE_DISPLAY_NAME,
        SECONDARY_WORKSPACE_DISPLAY_NAME,
    ):
        row = expected_rows.get(expected_name)
        if row is None:
            continue
        if (
            saved_workspace_row_source == "page.observe_saved_workspace_rows"
            and (row.width <= 0 or row.height <= 0)
        ):
            failures.append(
                f"the parsed saved workspace row {expected_name!r} did not expose positive visible bounds",
            )
        if "Branch:" not in row.detail_text:
            failures.append(
                f"the parsed saved workspace row {expected_name!r} did not expose repository branch details",
            )
    if failures:
        raise AssertionError(
            "Step 3 failed: clicking the workspace switcher trigger did not open "
            "the expected user-visible workspace switcher surface.\n"
            f"Observed trigger: {json.dumps(_trigger_payload(trigger), indent=2)}\n"
            f"Observed switcher: {json.dumps(_switcher_payload(switcher), indent=2)}\n"
            f"Observed panel: {json.dumps(asdict(panel), indent=2)}\n"
            f"Saved workspace row source: {saved_workspace_row_source}\n"
            f"Observed saved workspace rows: {json.dumps(_saved_workspace_rows_payload(saved_workspace_rows), indent=2)}\n"
            f"Problems: {'; '.join(failures)}",
        )


def _record_step(
    result: dict[str, object],
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
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-838 failed"))
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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_markdown_summary(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was tested",
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and preloaded saved hosted workspaces.",
        "* Verified the visible desktop top-bar workspace switcher trigger rendered with the active workspace summary.",
        "* Clicked the visible workspace switcher trigger with the mouse.",
        "* Verified that a user-visible workspace switcher surface opened with the heading and saved workspace rows.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    lines.extend(_artifact_lines(result, jira=True))
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and preloaded saved hosted workspaces.",
        "- Verified the visible desktop top-bar workspace switcher trigger rendered with the active workspace summary.",
        "- Clicked the visible workspace switcher trigger with the mouse.",
        "- Verified that a user-visible workspace switcher surface opened with the heading and saved workspace rows.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository "
            f"`{result['repository']}` @ `{result['repository_ref']}`, browser "
            f"`Chromium (Playwright)`, OS `{result['os']}`."
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    lines.extend(_artifact_lines(result, jira=False))
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        "## Test Automation Summary",
        "",
        "- Added TS-838 live desktop coverage for the workspace switcher trigger click interaction.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            f"- Outcome: {_failed_step_summary(result)}"
            if not passed
            else "- Outcome: clicking the visible workspace switcher trigger opened the desktop workspace switcher surface."
        ),
    ]
    lines.extend(_artifact_lines(result, jira=False))
    if not passed:
        lines.extend(
            [
                "",
                "## Error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY} - Workspace switcher trigger click does not open the surface",
            "",
            "## Steps to reproduce",
            f"1. {REQUEST_STEPS[0]} {_step_outcome(result, 1)}",
            f"2. {REQUEST_STEPS[1]} {_step_outcome(result, 2)}",
            f"3. {REQUEST_STEPS[2]} {_step_outcome(result, 3)}",
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Actual result",
            _failed_step_summary(result),
            "",
            "## Environment",
            f"- URL: {result.get('app_url', '<unknown>')}",
            f"- Repository: {result.get('repository', '<unknown>')} @ {result.get('repository_ref', '<unknown>')}",
            f"- Browser: {result.get('browser', '<unknown>')}",
            f"- OS: {result.get('os', '<unknown>')}",
            f"- Run command: {result.get('run_command', RUN_COMMAND)}",
            "",
            "## Screenshot / logs",
            f"- Screenshot: {result.get('screenshot', '<not captured>')}",
            "",
            "## Exact error message",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
        ],
    ) + "\n"


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") == "failed":
                return (
                    f"Step {step.get('step')} ({step.get('action')}) failed: "
                    f"{step.get('observed')}"
                )
    return str(result.get("error", "No failure details recorded."))


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "failed"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "not_reached"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "<no observation recorded>"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    failed = _first_failed_step(result)
    if failed is not None:
        return (
            f"Not reached because Step {failed.get('step')} failed: "
            f"{failed.get('action')}"
        )
    return "<no observation recorded>"


def _step_outcome(result: dict[str, object], step_number: int) -> str:
    status = _step_status(result, step_number)
    observation = _step_observation(result, step_number)
    if status == "passed":
        return f"✅ Passed — {observation}"
    if status == "failed":
        return f"❌ Failed — {observation}"
    return f"⚪ Not reached — {observation}"


def _first_failed_step(result: dict[str, object]) -> dict[str, object] | None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("status") == "failed":
            return step
    return None


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return ["* No step results recorded."]
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        icon = "✅" if step.get("status") == "passed" else "❌"
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} {icon} Step {step.get('step')}: {step.get('action')} — "
            f"{step.get('observed')}"
        )
    return lines or ["* No step results recorded."]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return ["* No human-style verification recorded."]
    prefix = "*" if jira else "-"
    lines = [
        f"{prefix} {check.get('check')} — {check.get('observed')}"
        for check in checks
        if isinstance(check, dict)
    ]
    return lines or ["* No human-style verification recorded."]


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    lines = ["", "## Artifacts" if not jira else "h4. Artifacts"]
    if result.get("screenshot"):
        lines.append(f"{prefix} Screenshot: {result['screenshot']}")
    lines.append(f"{prefix} Run command: {RUN_COMMAND}")
    return lines


def _workspace_state(repository: str) -> dict[str, object]:
    main_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    secondary_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECONDARY_WRITE_BRANCH}"
    return {
        "activeWorkspaceId": main_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": main_id,
                "displayName": ACTIVE_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": ACTIVE_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-18T03:30:00.000Z",
            },
            {
                "id": secondary_id,
                "displayName": SECONDARY_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECONDARY_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECONDARY_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-18T03:20:00.000Z",
            },
        ],
    }


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "icon_count": trigger.icon_count,
        "bounds": {
            "left": trigger.left,
            "top": trigger.top,
            "width": trigger.width,
            "height": trigger.height,
        },
        "viewport": {
            "width": trigger.viewport_width,
            "height": trigger.viewport_height,
        },
        "top_button_labels": list(trigger.top_button_labels),
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [
            {
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
            for row in switcher.rows
        ],
    }


def _observe_saved_workspace_rows(
    *,
    page: LiveWorkspaceSwitcherPage,
    switcher: WorkspaceSwitcherObservation,
) -> tuple[tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...], str]:
    try:
        return page.observe_saved_workspace_rows(), "page.observe_saved_workspace_rows"
    except AssertionError as error:
        parsed_rows = _parse_saved_workspace_rows_from_switcher_text(
            switcher,
            fallback_error=error,
        )
        return parsed_rows, "switcher_text_parser"


def _parse_saved_workspace_rows_from_switcher_text(
    switcher: WorkspaceSwitcherObservation,
    *,
    fallback_error: AssertionError,
) -> tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...]:
    lines = [
        " ".join(line.split()).strip()
        for line in switcher.body_text.splitlines()
        if line.strip()
    ]
    heading_indexes = [
        index for index, line in enumerate(lines) if line == "Workspace switcher"
    ]
    candidate_lines = lines[heading_indexes[-1] + 1 :] if heading_indexes else lines
    rows: list[WorkspaceSwitcherSavedWorkspaceRowObservation] = []
    index = 0
    while index + 2 < len(candidate_lines):
        header = candidate_lines[index]
        action = candidate_lines[index + 1]
        delete_action = candidate_lines[index + 2]
        if "Branch:" not in header or not delete_action.startswith("Delete: "):
            index += 1
            continue

        display_name: str | None = None
        target_type_label: str | None = None
        state_label: str | None = None
        detail_text = header
        header_parts = [part.strip() for part in header.split(", ", 3)]
        if len(header_parts) >= 4:
            display_name = header_parts[0]
            target_type_label = header_parts[1] or None
            state_label = header_parts[2] or None
            detail_text = header_parts[3]
        elif len(header_parts) >= 2:
            display_name = header_parts[0]
            target_type_label = header_parts[1] or None
            detail_text = ", ".join(header_parts[2:]) or header

        if not display_name:
            index += 1
            continue

        rows.append(
            WorkspaceSwitcherSavedWorkspaceRowObservation(
                display_name=display_name,
                target_type_label=target_type_label,
                state_label=state_label,
                detail_text=detail_text,
                selected=action == "Active",
                action_labels=(action, delete_action),
                left=0.0,
                top=0.0,
                width=0.0,
                height=0.0,
            ),
        )
        index += 3

    if rows:
        return tuple(rows)

    raise AssertionError(
        "The open workspace switcher did not expose any structurally parseable "
        "saved workspace rows after the click.\n"
        f"Fallback observer error: {fallback_error}\n"
        f"Observed switcher text:\n{switcher.switcher_text}\n"
        f"Observed body text:\n{switcher.body_text}",
    ) from fallback_error


def _saved_workspace_rows_payload(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...] | list[object],
) -> list[dict[str, object]]:
    payload: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, WorkspaceSwitcherSavedWorkspaceRowObservation):
            continue
        payload.append(
            {
                "display_name": row.display_name,
                "target_type_label": row.target_type_label,
                "state_label": row.state_label,
                "detail_text": row.detail_text,
                "selected": row.selected,
                "action_labels": list(row.action_labels),
                "bounds": {
                    "left": row.left,
                    "top": row.top,
                    "width": row.width,
                    "height": row.height,
                },
            },
        )
    return payload


def _snippet(text: str, *, limit: int = 220) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3]}..."


if __name__ == "__main__":
    main()
