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
    WorkspaceSwitcherFocusOwnershipObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import FocusedElementObservation  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app,
)
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-889"
TEST_CASE_TITLE = "Open workspace switcher — focus moves to panel container"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-889/test_ts_889.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
OPEN_TRANSITION_SETTLE_MS = 1_500
DEFAULT_BRANCH = "main"
PRIMARY_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECONDARY_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
SECONDARY_WORKSPACE_WRITE_BRANCH = "ts-889-alt"
LINKED_BUGS = ["TS-884"]

REQUEST_STEPS = [
    "Launch the application in a desktop browser.",
    "Click the workspace switcher trigger to open the panel.",
    "Wait for the opening transition/animation to fully complete.",
    "Check the active element in the document.",
]
EXPECTED_RESULT = (
    "The active element is the workspace switcher panel container or an "
    "interactive child element within the panel. The focus is successfully "
    "transferred from the root FLUTTER-VIEW to the component."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts889_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts889_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-889 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()
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
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "open_transition_settle_ms": OPEN_TRANSITION_SETTLE_MS,
        "linked_bugs": LINKED_BUGS,
        "preloaded_workspace_state": workspace_state,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
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
                        "desktop state before the workspace-switcher focus scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)
                trigger = page.observe_trigger()
                result["trigger_observation"] = _trigger_payload(trigger)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"trigger_text={trigger.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop shell before opening the switcher and "
                        "confirmed Dashboard plus the workspace-switcher trigger were visible."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                switcher = page.open_and_observe()
                panel = page.observe_open_panel(
                    expected_container_kinds=("anchored-panel", "surface"),
                )
                rows = page.observe_saved_workspace_rows()
                result["open_switcher_observation"] = _switcher_payload(switcher)
                result["open_panel_observation"] = asdict(panel)
                result["saved_workspace_rows_after_open"] = _saved_workspace_rows_payload(
                    rows,
                )
                _assert_desktop_panel_open(
                    trigger=trigger,
                    switcher=switcher,
                    panel=panel,
                    rows=rows,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"container_kind={panel.container_kind}; "
                        f"anchored_to_trigger={panel.anchored_to_trigger}; "
                        f"row_count={len(rows)}; "
                        f"title_text={panel.title_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the workspace switcher and visually confirmed the "
                        "Workspace switcher title and saved workspace rows were rendered."
                    ),
                    observed=(
                        f"title={panel.title_text!r}; "
                        f"container_kind={panel.container_kind!r}; "
                        f"row_names={[row.display_name for row in rows]!r}; "
                        f"text_excerpt={_snippet(switcher.switcher_text)!r}"
                    ),
                )

                page.wait_for_surface_to_remain_open(
                    stability_ms=OPEN_TRANSITION_SETTLE_MS,
                    timeout_ms=6_000,
                )
                settled_panel = page.observe_open_panel(
                    expected_container_kinds=("anchored-panel", "surface"),
                    timeout_ms=4_000,
                )
                result["settled_panel_observation"] = asdict(settled_panel)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The workspace switcher stayed visibly open through the opening "
                        f"settle window of {OPEN_TRANSITION_SETTLE_MS / 1000:.1f} seconds."
                    ),
                )

                focus_ownership = page.observe_focus_ownership(panel=settled_panel)
                active = page.active_element()
                result["focus_ownership_after_open"] = _focus_ownership_payload(
                    focus_ownership,
                )
                result["focused_element_after_open"] = _focused_element_payload(active)
                _assert_focus_moved_to_switcher_panel(
                    focus_ownership=focus_ownership,
                    active=active,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        f"active_label={focus_ownership.active_label!r}; "
                        f"active_role={focus_ownership.active_role!r}; "
                        f"active_tag={focus_ownership.active_tag_name!r}; "
                        f"active_within_switcher={focus_ownership.active_within_switcher}; "
                        f"active_on_trigger={focus_ownership.active_on_trigger}; "
                        f"focus_owned_by_switcher={focus_ownership.focus_owned_by_switcher}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "After the opening animation settled, observed which control in the "
                        "visible switcher owned focus from a keyboard user's perspective."
                    ),
                    observed=(
                        f"active_label={focus_ownership.active_label!r}; "
                        f"active_role={focus_ownership.active_role!r}; "
                        f"active_tag={focus_ownership.active_tag_name!r}; "
                        f"visible={focus_ownership.active_visible}; "
                        f"in_viewport={focus_ownership.active_in_viewport}; "
                        f"active_within_switcher={focus_ownership.active_within_switcher}; "
                        f"active_on_trigger={focus_ownership.active_on_trigger}"
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


def _assert_desktop_panel_open(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> None:
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 2 failed: clicking the workspace switcher trigger did not open the "
            "expected desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if panel.width <= 0 or panel.height <= 0:
        raise AssertionError(
            "Step 2 failed: clicking the workspace switcher trigger did not expose a "
            "readable desktop panel surface.\n"
            f"Observed panel bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}\n"
            f"Observed trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )
    if "Workspace switcher" not in switcher.switcher_text and panel.title_text != "Workspace switcher":
        raise AssertionError(
            "Step 2 failed: the opened surface did not expose the expected Workspace "
            "switcher title.\n"
            f"Observed panel title: {panel.title_text!r}\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if len(rows) < 2:
        raise AssertionError(
            "Step 2 failed: the open workspace switcher did not render the preloaded "
            "saved workspace rows needed for this scenario.\n"
            f"Observed row count: {len(rows)}\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )


def _assert_focus_moved_to_switcher_panel(
    *,
    focus_ownership: WorkspaceSwitcherFocusOwnershipObservation,
    active: FocusedElementObservation,
) -> None:
    failures: list[str] = []
    if not focus_ownership.focus_owned_by_switcher:
        failures.append("keyboard focus was not owned by the open workspace switcher")
    if not focus_ownership.active_within_switcher:
        failures.append("the active element was not inside the visible switcher panel")
    if focus_ownership.active_on_trigger:
        failures.append("the active element stayed on the workspace-switcher trigger")
    if not focus_ownership.active_visible:
        failures.append("the active element was not visibly rendered")
    if not focus_ownership.active_in_viewport:
        failures.append("the active element was not inside the viewport")
    if focus_ownership.active_tag_name == "FLUTTER-VIEW" or active.tag_name == "FLUTTER-VIEW":
        failures.append("the active element remained the root FLUTTER-VIEW")
    if failures:
        raise AssertionError(
            "Step 4 failed: after the workspace switcher opening transition completed, "
            "keyboard focus did not move into the visible switcher panel.\n"
            f"Observed focus ownership: {json.dumps(_focus_ownership_payload(focus_ownership), indent=2)}\n"
            f"Observed active element: {json.dumps(_focused_element_payload(active), indent=2)}\n"
            + "\n".join(f"- {item}" for item in failures)
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
    error = str(result.get("error", "AssertionError: TS-889 failed"))
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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved workspaces.",
        "* Opened the desktop workspace switcher from Dashboard.",
        (
            f"* Waited {OPEN_TRANSITION_SETTLE_MS / 1000:.1f} seconds for the opening "
            "transition to settle before checking focus."
        ),
        "* Verified the active element after opening was inside the visible switcher panel, not on the trigger or the root FLUTTER-VIEW.",
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
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved workspaces.",
        "- Opened the desktop workspace switcher from Dashboard.",
        (
            f"- Waited {OPEN_TRANSITION_SETTLE_MS / 1000:.1f} seconds for the opening "
            "transition to settle before checking focus."
        ),
        "- Verified the active element after opening was inside the visible switcher panel, not on the trigger or the root `FLUTTER-VIEW`.",
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
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        f"- Command: `{RUN_COMMAND}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            "- Outcome: after the switcher opening transition settled, the active "
            "element was inside the visible workspace switcher panel."
            if passed
            else f"- Outcome: {_failed_step_summary(result)}"
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
            f"# {TICKET_KEY} - Workspace switcher does not move focus into the open panel",
            "",
            "## Steps to reproduce",
            "1. Launch the application in a desktop browser.",
            "2. Click the workspace switcher trigger to open the panel.",
            "3. Wait for the opening transition/animation to fully complete.",
            "4. Check the active element in the document.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {_actual_focus_summary(result)}",
            "",
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            (
                f"- Opening-settle wait: {OPEN_TRANSITION_SETTLE_MS / 1000:.1f} seconds"
            ),
            f"- Run command: {RUN_COMMAND}",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps(
                {
                    "focus_ownership_after_open": result.get(
                        "focus_ownership_after_open",
                    ),
                    "focused_element_after_open": result.get(
                        "focused_element_after_open",
                    ),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _actual_focus_summary(result: dict[str, object]) -> str:
    focus = result.get("focus_ownership_after_open")
    active = result.get("focused_element_after_open")
    if isinstance(focus, dict):
        return (
            "after the opening transition settled, the active element was "
            f"tag={focus.get('active_tag_name')!r}, role={focus.get('active_role')!r}, "
            f"label={focus.get('active_label')!r}; "
            f"active_within_switcher={focus.get('active_within_switcher')}, "
            f"active_on_trigger={focus.get('active_on_trigger')}, "
            f"focus_owned_by_switcher={focus.get('focus_owned_by_switcher')}."
        )
    if isinstance(active, dict):
        return (
            "after the opening transition settled, the active element was "
            f"tag={active.get('tag_name')!r}, role={active.get('role')!r}, "
            f"accessible_name={active.get('accessible_name')!r}."
        )
    return _failed_step_summary(result)


def _annotated_step_line(
    result: dict[str, object],
    step_number: int,
    action: str,
) -> str:
    marker = "✅" if _step_status(result, step_number) == "passed" else "❌"
    return (
        f"{step_number}. {marker} {action}\n"
        f"   Actual: {_step_observation(result, step_number)}"
    )


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return [f"{prefix} <no step data recorded>"]
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        marker = "✅" if step.get("status") == "passed" else "❌"
        lines.append(
            f"{prefix} {marker} Step {step.get('step')}: {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
    return lines or [f"{prefix} <no step data recorded>"]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return [f"{prefix} <no human-style verification recorded>"]
    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    return lines or [f"{prefix} <no human-style verification recorded>"]


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    if jira:
        return [f"{prefix} Screenshot: {{{{{screenshot}}}}}"]
    return [f"{prefix} Screenshot: `{screenshot}`"]


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _step_status(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("step") == step_number:
                return str(step.get("status"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("step") == step_number:
                return str(step.get("observed"))
    return "<no observation recorded>"


def _workspace_state(repository: str) -> dict[str, object]:
    primary_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    secondary_id = (
        f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECONDARY_WORKSPACE_WRITE_BRANCH}"
    )
    return {
        "activeWorkspaceId": primary_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": primary_id,
                "displayName": PRIMARY_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": PRIMARY_WORKSPACE_DISPLAY_NAME,
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
                "writeBranch": SECONDARY_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-18T03:20:00.000Z",
            },
        ],
    }


def _trigger_payload(observation: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "viewport_width": observation.viewport_width,
        "viewport_height": observation.viewport_height,
        "semantic_label": observation.semantic_label,
        "visible_text": observation.visible_text,
        "raw_text_lines": list(observation.raw_text_lines),
        "display_name": observation.display_name,
        "workspace_type": observation.workspace_type,
        "state_label": observation.state_label,
        "icon_count": observation.icon_count,
        "bounds": {
            "left": observation.left,
            "top": observation.top,
            "width": observation.width,
            "height": observation.height,
        },
        "top_button_labels": list(observation.top_button_labels),
    }


def _switcher_payload(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "switcher_text": observation.switcher_text,
        "row_count": observation.row_count,
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
            for row in observation.rows
        ],
    }


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


def _focus_ownership_payload(
    observation: WorkspaceSwitcherFocusOwnershipObservation,
) -> dict[str, object]:
    return {
        "active_label": observation.active_label,
        "active_role": observation.active_role,
        "active_tag_name": observation.active_tag_name,
        "active_outer_html": observation.active_outer_html,
        "active_visible": observation.active_visible,
        "active_in_viewport": observation.active_in_viewport,
        "switcher_focus_within": observation.switcher_focus_within,
        "active_within_switcher": observation.active_within_switcher,
        "active_on_trigger": observation.active_on_trigger,
        "focus_owned_by_switcher": observation.focus_owned_by_switcher,
    }


def _focused_element_payload(observation: FocusedElementObservation) -> dict[str, object]:
    return {
        "tag_name": observation.tag_name,
        "role": observation.role,
        "accessible_name": observation.accessible_name,
        "text": observation.text,
        "tabindex": observation.tabindex,
        "outer_html": observation.outer_html,
    }


def _snippet(value: str, *, limit: int = 220) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "..."


if __name__ == "__main__":
    main()
