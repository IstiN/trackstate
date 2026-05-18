from __future__ import annotations

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
    WorkspaceSwitcherEscapeDismissObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherTransitionMonitorObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-819"
TEST_CASE_TITLE = "Press Escape key — workspace switcher panel dismisses"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-819/test_ts_819.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts819_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts819_failure.png"
ESCAPE_DISMISS_TIMEOUT_MS = 4_000

REQUEST_STEPS = [
    "Launch the application on a desktop browser.",
    "Click the workspace switcher trigger to open the panel.",
    "Press the 'Escape' key on the keyboard.",
    "Observe the state of the workspace switcher panel.",
]
EXPECTED_RESULT = (
    "The workspace switcher panel closes immediately and focus returns to the "
    "workspace switcher trigger."
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
            "TS-819 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()

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
        "escape_dismiss_timeout_ms": ESCAPE_DISMISS_TIMEOUT_MS,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the Escape dismissal scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger_before = page.observe_trigger()
                    result["trigger_before"] = _trigger_payload(trigger_before)
                except AssertionError as error:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"trigger_label={trigger_before.semantic_label!r}; "
                        f"trigger_text={trigger_before.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop app shell before opening the panel and "
                        "confirmed Dashboard plus the visible workspace switcher trigger "
                        "were rendered."
                    ),
                    observed=(
                        f"trigger_text={trigger_before.visible_text!r}; "
                        f"top_buttons={list(trigger_before.top_button_labels)!r}"
                    ),
                )

                try:
                    switcher = page.open_and_observe()
                    panel = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                    )
                    _assert_desktop_panel_open(
                        trigger=trigger_before,
                        switcher=switcher,
                        panel=panel,
                    )
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = {
                        "title_text": panel.title_text,
                        "container_kind": panel.container_kind,
                        "container_role": panel.container_role,
                        "container_text": panel.container_text,
                        "anchored_to_trigger": panel.anchored_to_trigger,
                        "bottom_aligned": panel.bottom_aligned,
                        "full_screen_like": panel.full_screen_like,
                        "background_dimmed": panel.background_dimmed,
                        "bounds": {
                            "left": panel.left,
                            "top": panel.top,
                            "width": panel.width,
                            "height": panel.height,
                        },
                    }
                except Exception as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=REQUEST_STEPS[1],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        f"container_kind={panel.container_kind}; "
                        f"anchored_to_trigger={panel.anchored_to_trigger}; "
                        f"row_count={switcher.row_count}; "
                        f"title_visible={'Workspace switcher' in switcher.switcher_text}"
                    ),
                )

                try:
                    page.start_transition_monitor()
                    dismissal = page.close(timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS)
                    escape_monitor = page.read_transition_monitor(clear=True)
                    result["escape_dismissal_observation"] = _escape_dismissal_payload(
                        dismissal,
                    )
                    result["escape_transition_monitor"] = _transition_monitor_payload(
                        escape_monitor,
                    )
                    _assert_escape_surface_dismissal(
                        dismissal=dismissal,
                        monitor=escape_monitor,
                    )
                except Exception as error:
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
                        "Pressed Escape while the visible workspace switcher surface was "
                        "open and the transition monitor observed the panel disappear "
                        f"within {ESCAPE_DISMISS_TIMEOUT_MS} ms."
                    ),
                )

                try:
                    trigger_after = page.observe_trigger()
                    result["trigger_after"] = _trigger_payload(trigger_after)
                    page.press_enter_on_active_element_and_wait_for_surface(
                        timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS,
                    )
                    keyboard_reopen_switcher = page.observe_open_switcher(
                        timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS,
                    )
                    keyboard_reopen_panel = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=ESCAPE_DISMISS_TIMEOUT_MS,
                    )
                    result["keyboard_reopen_switcher_observation"] = _switcher_payload(
                        keyboard_reopen_switcher,
                    )
                    result["keyboard_reopen_panel_observation"] = {
                        "title_text": keyboard_reopen_panel.title_text,
                        "container_kind": keyboard_reopen_panel.container_kind,
                        "container_role": keyboard_reopen_panel.container_role,
                        "container_text": keyboard_reopen_panel.container_text,
                        "anchored_to_trigger": keyboard_reopen_panel.anchored_to_trigger,
                        "bottom_aligned": keyboard_reopen_panel.bottom_aligned,
                        "full_screen_like": keyboard_reopen_panel.full_screen_like,
                        "background_dimmed": keyboard_reopen_panel.background_dimmed,
                        "bounds": {
                            "left": keyboard_reopen_panel.left,
                            "top": keyboard_reopen_panel.top,
                            "width": keyboard_reopen_panel.width,
                            "height": keyboard_reopen_panel.height,
                        },
                    }
                    _assert_escape_focus_return(
                        trigger_before=trigger_before,
                        trigger_after=trigger_after,
                        keyboard_reopen_switcher=keyboard_reopen_switcher,
                        keyboard_reopen_panel=keyboard_reopen_panel,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=REQUEST_STEPS[3],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=REQUEST_STEPS[3],
                    observed=(
                        "The workspace switcher surface disappeared, the trigger still "
                        "showed the same active workspace, and pressing Enter without "
                        "clicking reopened the switcher from the restored trigger focus."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher, pressed Escape, and "
                        "used the keyboard again without clicking to confirm the trigger "
                        "remained the active user-visible control."
                    ),
                    observed=(
                        f"trigger_after={trigger_after.semantic_label!r}; "
                        f"keyboard_reopen_kind={keyboard_reopen_panel.container_kind!r}; "
                        f"keyboard_reopen_rows={keyboard_reopen_switcher.row_count}"
                    ),
                )
            except Exception:
                if page is not None:
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
) -> None:
    if switcher.row_count <= 0:
        raise AssertionError(
            "Step 2 failed: opening the workspace switcher did not expose any visible "
            "workspace rows.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
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


def _assert_escape_surface_dismissal(
    *,
    dismissal: WorkspaceSwitcherEscapeDismissObservation,
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
) -> None:
    failures: list[str] = []

    if not dismissal.dashboard_visible:
        failures.append(
            "the main Dashboard shell was not visibly present after Escape",
        )
    if not dismissal.trigger_visible:
        failures.append(
            "the workspace switcher trigger was not visible after Escape",
        )
    if monitor.sample_count <= 0 or monitor.visible_sample_count <= 0:
        failures.append(
            "the transition monitor did not capture the visible workspace switcher "
            "surface before Escape",
        )
    if not monitor.ever_hidden_after_visible:
        failures.append(
            "the transition monitor never observed the visible workspace switcher "
            "surface disappear after Escape",
        )

    if failures:
        raise AssertionError(
            "Step 3 failed: pressing Escape did not dismiss the user-visible workspace "
            "switcher surface reliably.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed monitor kinds: {list(monitor.observed_container_kinds)!r}\n"
            + f"Observed monitor row counts: {list(monitor.observed_row_counts)!r}\n"
            + f"Observed body text:\n{dismissal.body_text}",
        )


def _assert_escape_focus_return(
    *,
    trigger_before: WorkspaceSwitcherTriggerObservation,
    trigger_after: WorkspaceSwitcherTriggerObservation,
    keyboard_reopen_switcher: WorkspaceSwitcherObservation,
    keyboard_reopen_panel: WorkspaceSwitcherPanelObservation,
) -> None:
    failures: list[str] = []

    if trigger_after.semantic_label != trigger_before.semantic_label:
        failures.append(
            "the workspace switcher trigger no longer reflected the same active "
            f"workspace state (before={trigger_before.semantic_label!r}, "
            f"after={trigger_after.semantic_label!r})",
        )
    try:
        _assert_desktop_panel_open(
            trigger=trigger_after,
            switcher=keyboard_reopen_switcher,
            panel=keyboard_reopen_panel,
        )
    except AssertionError as error:
        failures.append(
            "pressing Enter immediately after Escape did not reopen the visible "
            f"workspace switcher from the restored trigger focus ({error})",
        )

    if failures:
        raise AssertionError(
            "Step 4 failed: after Escape, the workspace switcher trigger was not left "
            "in the expected keyboard-usable state.\n"
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
    error = str(result.get("error", "AssertionError: TS-819 failed"))
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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "* Opened the desktop workspace switcher from Dashboard.",
        "* Pressed the Escape key while the workspace switcher panel was visible.",
        "* Verified the visible panel disappeared and focus returned to the workspace switcher trigger.",
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
        "- Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "- Opened the desktop workspace switcher from Dashboard.",
        "- Pressed Escape while the workspace switcher panel was visible.",
        "- Verified the visible panel disappeared and focus returned to the workspace switcher trigger.",
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
        "- Added TS-819 live desktop coverage for Escape-key dismissal of the workspace switcher panel.",
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
            else "- Outcome: the desktop workspace switcher closed on Escape and focus returned to the trigger."
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
            f"# {TICKET_KEY} - Workspace switcher does not dismiss correctly on Escape",
            "",
            "## Steps to reproduce",
            "1. Launch the application on a desktop browser.",
            "2. Click the workspace switcher trigger to open the panel.",
            "3. Press the 'Escape' key on the keyboard.",
            "4. Observe the state of the workspace switcher panel.",
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
            f"- Actual: {result.get('error', '<missing error>')}",
            "",
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            (
                f"- Repository: {result.get('repository')} @ "
                f"{result.get('repository_ref')}"
            ),
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Run command: {RUN_COMMAND}",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps(
                {
                    "trigger_before": result.get("trigger_before"),
                    "open_switcher_observation": result.get("open_switcher_observation"),
                    "open_panel_observation": result.get("open_panel_observation"),
                    "trigger_after": result.get("trigger_after"),
                    "focused_after": result.get("focused_after"),
                    "body_text_after_escape": result.get("body_text_after_escape"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


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
    if not isinstance(steps, list):
        return "failed"
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "<no observation recorded>"
    for step in steps:
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    return "<no observation recorded>"


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "raw_text_lines": list(trigger.raw_text_lines),
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "viewport_width": trigger.viewport_width,
        "viewport_height": trigger.viewport_height,
        "bounds": {
            "left": trigger.left,
            "top": trigger.top,
            "width": trigger.width,
            "height": trigger.height,
        },
        "top_button_labels": list(trigger.top_button_labels),
    }


def _escape_dismissal_payload(
    observation: WorkspaceSwitcherEscapeDismissObservation,
) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "dashboard_visible": observation.dashboard_visible,
        "trigger_visible": observation.trigger_visible,
    }


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": switcher.row_count,
        "switcher_text": switcher.switcher_text,
        "rows": [
            {
                "display_name": row.display_name,
                "target_type_label": row.target_type_label,
                "state_label": row.state_label,
                "detail_text": row.detail_text,
                "visible_text": row.visible_text,
                "selected": row.selected,
                "action_labels": list(row.action_labels),
                "button_labels": list(row.button_labels),
            }
            for row in switcher.rows
        ],
    }


def _transition_monitor_payload(
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
) -> dict[str, object]:
    return {
        "sample_count": monitor.sample_count,
        "visible_sample_count": monitor.visible_sample_count,
        "hidden_sample_count": monitor.hidden_sample_count,
        "ever_hidden_after_visible": monitor.ever_hidden_after_visible,
        "observed_container_kinds": list(monitor.observed_container_kinds),
        "observed_row_counts": list(monitor.observed_row_counts),
        "observed_active_workspace_names": list(
            monitor.observed_active_workspace_names,
        ),
        "latest_visible_container_kind": monitor.latest_visible_container_kind,
        "latest_visible_row_count": monitor.latest_visible_row_count,
        "latest_visible_active_workspace_name": (
            monitor.latest_visible_active_workspace_name
        ),
    }


if __name__ == "__main__":
    main()
