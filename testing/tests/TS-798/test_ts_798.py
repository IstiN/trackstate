from __future__ import annotations

from dataclasses import asdict
import json
import platform
import sys
import tempfile
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_desktop_header_layout_page import (  # noqa: E402
    HeaderThemeToggleCycleObservation,
    LiveDesktopHeaderLayoutPage,
)
from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-798"
TEST_CASE_TITLE = (
    "Desktop workspace switcher activation - background dimming is absent and UI remains interactive"
)
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-798/test_ts_798.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts798_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts798_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-798 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            workspace_page = LiveWorkspaceSwitcherPage(tracker_page)
            header_page = LiveDesktopHeaderLayoutPage(
                tracker_page,
                user_login=user.login,
            )
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                try:
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the workspace-switcher scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    workspace_page.dismiss_connection_banner()
                    workspace_page.set_viewport(**DESKTOP_VIEWPORT)

                    desktop_trigger = workspace_page.observe_trigger()
                    interaction_control = _preferred_interaction_label(
                        desktop_trigger.top_button_labels,
                    )
                    interaction_button = header_page.observe_button(interaction_control)
                    result["interaction_button_observation"] = asdict(interaction_button)
                    result["interaction_control"] = interaction_control
                    result["desktop_trigger_observation"] = asdict(desktop_trigger)
                except AssertionError as error:
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action="Launch the application on a desktop browser.",
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Launch the application on a desktop browser.",
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"interaction_control={interaction_control!r}; "
                        f"interaction_bounds=({interaction_button.left:.1f}, "
                        f"{interaction_button.top:.1f}, {interaction_button.width:.1f}, "
                        f"{interaction_button.height:.1f}); "
                        f"top_buttons={list(desktop_trigger.top_button_labels)!r}; "
                        f"trigger_label={desktop_trigger.semantic_label!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop app shell and confirmed the visible header "
                        "showed the workspace switcher plus other interactive top-bar controls."
                    ),
                    observed=(
                        f"interaction_control={interaction_control!r}; "
                        f"top_buttons={list(desktop_trigger.top_button_labels)!r}; "
                        f"trigger_text={desktop_trigger.visible_text!r}"
                    ),
                )

                try:
                    desktop_panel = _open_and_observe_panel(
                        page=workspace_page,
                        trigger=desktop_trigger,
                    )
                    result["desktop_panel_observation"] = asdict(desktop_panel)
                    _assert_desktop_panel_is_non_modal(
                        panel=desktop_panel,
                        trigger=desktop_trigger,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action="Click the workspace switcher trigger to open the panel.",
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Click the workspace switcher trigger to open the panel.",
                    observed=(
                        f"container_kind={desktop_panel.container_kind}; "
                        f"anchored_to_trigger={desktop_panel.anchored_to_trigger}; "
                        f"bounds=({desktop_panel.left:.1f}, {desktop_panel.top:.1f}, "
                        f"{desktop_panel.width:.1f}, {desktop_panel.height:.1f})"
                    ),
                )

                try:
                    if desktop_panel.background_dimmed:
                        raise AssertionError(
                            "Step 3 failed: opening the desktop workspace switcher dimmed "
                            "the background like a modal instead of keeping the app shell "
                            "fully visible.\n"
                            f"Observed container kind: {desktop_panel.container_kind}\n"
                            f"Observed bounds: left={desktop_panel.left:.1f}, "
                            f"top={desktop_panel.top:.1f}, width={desktop_panel.width:.1f}, "
                            f"height={desktop_panel.height:.1f}",
                        )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=(
                            "Inspect the background area of the application for any dimming "
                            "or opacity changes."
                        ),
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Inspect the background area of the application for any dimming "
                        "or opacity changes."
                    ),
                    observed=(
                        f"background_dimmed={desktop_panel.background_dimmed}; "
                        f"container_kind={desktop_panel.container_kind}; "
                        f"bright_change_pixels={desktop_panel.bright_change_pixels}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher and visually checked that "
                        "the page behind it stayed fully readable instead of dimming like a modal."
                    ),
                    observed=(
                        f"background_dimmed={desktop_panel.background_dimmed}; "
                        f"surface_kind={desktop_panel.container_kind}; "
                        f"interaction_control={interaction_control!r}; "
                        f"top_buttons_still_visible={list(desktop_trigger.top_button_labels)!r}"
                    ),
                )

                try:
                    expected_toggled_label = (
                        "Light theme"
                        if interaction_control == "Dark theme"
                        else "Dark theme"
                    )
                    header_page.click_observed_button(interaction_button)
                    workspace_page.close_switcher()
                    try:
                        toggled_button = header_page.observe_button(
                            expected_toggled_label,
                            timeout_ms=10_000,
                        )
                    except Exception as error:
                        raise AssertionError(
                            "Step 4 failed: clicking the visible desktop theme toggle while "
                            "the workspace switcher was open did not change the header theme "
                            "state after the panel closed.\n"
                            f"Observed initial label: {interaction_control!r}\n"
                            f"Expected toggled label: {expected_toggled_label!r}\n"
                            f"Observed body text after closing the panel:\n"
                            f"{header_page.current_body_text()}"
                        ) from error
                    restored_label = header_page.toggle_theme()
                    theme_cycle = HeaderThemeToggleCycleObservation(
                        initial_label=interaction_control,
                        toggled_label=toggled_button.label,
                        restored_label=restored_label,
                    )
                    result["toggled_button_observation"] = asdict(toggled_button)
                    result["theme_cycle_observation"] = asdict(theme_cycle)
                    _assert_header_interaction(
                        interaction_control=interaction_control,
                        theme_cycle=theme_cycle,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action=(
                            "Attempt to interact with another header element like the Search "
                            "issues field or Create issue button."
                        ),
                        observed=f"{type(error).__name__}: {error}",
                    )
                    raise
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Attempt to interact with another header element like the Search "
                        "issues field or Create issue button."
                    ),
                    observed=(
                        f"interaction_control={interaction_control!r}; "
                        f"initial_label={theme_cycle.initial_label!r}; "
                        f"toggled_label={theme_cycle.toggled_label!r}; "
                        f"restored_label={theme_cycle.restored_label!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Toggled another visible desktop header control while the workspace "
                        "switcher was open to confirm the rest of the top bar still responded "
                        "to input."
                    ),
                    observed=(
                        f"interaction_control={interaction_control!r}; "
                        f"toggled_to={theme_cycle.toggled_label!r}; "
                        f"restored_to={theme_cycle.restored_label!r}"
                    ),
                )

                workspace_page.close_switcher()
                header_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                header_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
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


def _assert_desktop_panel_is_non_modal(
    *,
    panel: WorkspaceSwitcherPanelObservation,
    trigger: WorkspaceSwitcherTriggerObservation,
) -> None:
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 2 failed: clicking the desktop workspace switcher did not open the "
            "expected desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if not panel.anchored_to_trigger:
        raise AssertionError(
            "Step 2 failed: clicking the desktop workspace switcher did not keep the "
            "surface anchored to the trigger.\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}\n"
            f"Trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )
def _assert_header_interaction(
    *,
    interaction_control: str,
    theme_cycle: HeaderThemeToggleCycleObservation,
) -> None:
    if interaction_control not in {"Dark theme", "Light theme"}:
        raise AssertionError(
            "Step 4 failed: the desktop header did not expose a visible interaction "
            "control before the workspace switcher probe.\n"
            f"Observed interaction control: {interaction_control!r}",
        )
    if theme_cycle.initial_label != interaction_control:
        raise AssertionError(
            "Step 4 failed: the visible desktop theme control changed before the "
            "interaction probe started.\n"
            f"Observed interaction control: {interaction_control!r}\n"
            f"Observed initial label: {theme_cycle.initial_label!r}",
        )
    if theme_cycle.toggled_label == theme_cycle.initial_label:
        raise AssertionError(
            "Step 4 failed: another visible desktop header control did not react while "
            "the workspace switcher was open.\n"
            f"Observed interaction control: {interaction_control!r}\n"
            f"Observed toggled label: {theme_cycle.toggled_label!r}",
        )
    if theme_cycle.restored_label != theme_cycle.initial_label:
        raise AssertionError(
            "Step 4 failed: the visible desktop theme control did not return to its "
            "original label after the interaction probe completed.\n"
            f"Observed initial label: {theme_cycle.initial_label!r}\n"
            f"Observed restored label: {theme_cycle.restored_label!r}",
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
    error = str(result.get("error", "AssertionError: TS-798 failed"))
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
        (
            "* Opened the desktop workspace switcher and checked the visible surface "
            "behaved like a non-modal desktop panel instead of a dimmed modal overlay."
        ),
        (
            "* Probed another visible desktop top-bar control while the switcher was open "
            "to confirm the desktop header remained interactive."
        ),
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
        (
            "- Opened the desktop workspace switcher and verified the live surface did "
            "not dim the background like a modal overlay."
        ),
        (
            "- Probed another visible desktop top-bar control while the switcher was open to "
            "verify another header control remained interactive."
        ),
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
        (
            "- Added TS-798 live desktop coverage for non-modal workspace-switcher "
            "behavior and real header interactivity while the switcher is open."
        ),
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
            else f"- Outcome: {_successful_outcome_summary(result)}"
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
            f"# {TICKET_KEY} - Desktop workspace switcher still behaves like a modal or blocks header interaction",
            "",
            "## Steps to reproduce",
            "1. Launch the application on a desktop browser.",
            "2. Click the workspace switcher trigger to open the panel.",
            "3. Inspect the background area of the application for any dimming or opacity changes.",
            "4. Attempt to hover over or interact with another header element like the Search issues field or Create issue button.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(
                result,
                1,
                "Launch the application on a desktop browser.",
            ),
            _annotated_step_line(
                result,
                2,
                "Click the workspace switcher trigger to open the panel.",
            ),
            _annotated_step_line(
                result,
                3,
                "Inspect the background area of the application for any dimming or opacity changes.",
            ),
            _annotated_step_line(
                result,
                4,
                "Attempt to hover over or interact with another header element like the Search issues field or Create issue button.",
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            (
                "- Expected: opening the desktop workspace switcher should not dim the "
                "application background, the surface should behave like a panel rather "
                "than a modal dialog, and the user should still be able to interact with "
                "another visible header control such as the desktop theme toggle."
            ),
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


def _successful_outcome_summary(result: dict[str, object]) -> str:
    interaction_control = str(result.get("interaction_control", "another visible header control"))
    theme_cycle = result.get("theme_cycle_observation")
    if isinstance(theme_cycle, dict):
        toggled_label = str(theme_cycle.get("toggled_label", "")).strip()
        restored_label = str(theme_cycle.get("restored_label", "")).strip()
        if toggled_label and restored_label:
            return (
                "the desktop workspace switcher opened without background dimming and "
                f"the visible `{interaction_control}` control toggled to "
                f"`{toggled_label}` and back to `{restored_label}` while the switcher "
                "stayed open."
            )
    return (
        "the desktop workspace switcher opened without background dimming and another "
        "visible header control remained interactive while the switcher stayed open."
    )


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


def _open_and_observe_panel(
    *,
    page: LiveWorkspaceSwitcherPage,
    trigger: WorkspaceSwitcherTriggerObservation,
) -> WorkspaceSwitcherPanelObservation:
    with tempfile.NamedTemporaryFile(
        dir=OUTPUTS_DIR,
        prefix="ts798_panel_before_",
        suffix=".png",
        delete=False,
    ) as before_handle:
        before_path = Path(before_handle.name)
    with tempfile.NamedTemporaryFile(
        dir=OUTPUTS_DIR,
        prefix="ts798_panel_after_",
        suffix=".png",
        delete=False,
    ) as after_handle:
        after_path = Path(after_handle.name)
    try:
        page.screenshot(str(before_path))
        page.open_switcher()
        page.screenshot(str(after_path))
        return page.observe_panel(
            trigger,
            before_screenshot_path=before_path,
            after_screenshot_path=after_path,
        )
    finally:
        before_path.unlink(missing_ok=True)
        after_path.unlink(missing_ok=True)


def _preferred_interaction_label(labels: tuple[str, ...]) -> str:
    for candidate in ("Dark theme", "Light theme"):
        if candidate in labels:
            return candidate
    raise AssertionError(
        "Step 1 failed: the desktop app shell did not expose a visible theme toggle "
        "suitable for the interaction probe.\n"
        f"Observed top buttons: {list(labels)!r}",
    )


if __name__ == "__main__":
    main()
