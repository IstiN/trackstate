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

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_workspace_switcher_visual_probe import (  # noqa: E402
    LiveWorkspaceSwitcherVisualProbe,
    WorkspaceSwitcherTriggerVisualObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-722"
TEST_CASE_TITLE = (
    "App-shell switcher trigger - repository button replacement and responsive layout"
)
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-722/test_ts_722.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
COMPACT_VIEWPORT = {"width": 390, "height": 844}
DESKTOP_SECTIONS = ("Dashboard", "Board", "JQL Search", "Settings")
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts722_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts722_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    visual_probe = LiveWorkspaceSwitcherVisualProbe()
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-722 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

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
        "compact_viewport": COMPACT_VIEWPORT,
        "steps": [],
        "human_verification": [],
        "desktop_section_observations": {},
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the workspace-switcher scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                page.dismiss_connection_banner()
                page.set_viewport(**DESKTOP_VIEWPORT)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Launch the application on a desktop browser.",
                    observed=(
                        f"Opened the deployed app at {config.app_url} in Chromium and "
                        f"reached the interactive tracker shell at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}."
                    ),
                )

                step_failures: list[str] = []

                desktop_summaries: list[str] = []
                for section in DESKTOP_SECTIONS:
                    page.navigate_to_section(section)
                    trigger = page.observe_trigger()
                    trigger_visual = _observe_trigger_visual(
                        page=page,
                        visual_probe=visual_probe,
                        trigger=trigger,
                    )
                    section_payload = asdict(trigger)
                    section_payload["visual_observation"] = asdict(trigger_visual)
                    desktop_observations = result.setdefault(
                        "desktop_section_observations",
                        {},
                    )
                    assert isinstance(desktop_observations, dict)
                    desktop_observations[section] = section_payload
                    try:
                        _assert_desktop_trigger(
                            trigger,
                            trigger_visual=trigger_visual,
                            section=section,
                        )
                    except AssertionError as error:
                        step_failures.append(str(error))
                    desktop_summaries.append(
                        f"{section}: label={trigger.semantic_label!r}, "
                        f"icon_count={trigger.icon_count}, "
                        f"visual_icon_visible={trigger_visual.icon_visible}, "
                        f"visible_text={trigger.visible_text!r}, "
                        f"top_buttons={list(trigger.top_button_labels)!r}",
                    )
                if step_failures:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action=(
                            "Verify the legacy repository-access button is replaced by a "
                            "workspace switcher across tracker sections."
                        ),
                        observed=step_failures[0],
                    )
                else:
                    _record_step(
                        result,
                        step=2,
                        status="passed",
                        action=(
                            "Verify the legacy repository-access button is replaced by a "
                            "workspace switcher across tracker sections."
                        ),
                        observed="; ".join(desktop_summaries),
                    )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the top app shell in Dashboard, Board, JQL Search, and "
                        "Settings and checked what a user would see in the workspace control."
                    ),
                    observed="; ".join(desktop_summaries),
                )

                page.navigate_to_section("Dashboard")
                desktop_trigger = page.observe_trigger()
                desktop_trigger_visual = _observe_trigger_visual(
                    page=page,
                    visual_probe=visual_probe,
                    trigger=desktop_trigger,
                )
                result["desktop_trigger_observation"] = {
                    **asdict(desktop_trigger),
                    "visual_observation": asdict(desktop_trigger_visual),
                }
                desktop_panel: WorkspaceSwitcherPanelObservation | None = None
                try:
                    page.open_switcher()
                    desktop_panel = page.observe_panel(desktop_trigger)
                    result["desktop_panel_observation"] = asdict(desktop_panel)
                    _assert_desktop_panel(
                        panel=desktop_panel,
                        trigger=desktop_trigger,
                    )
                except AssertionError as error:
                    step_failures.append(str(error))
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=(
                            "Click the desktop switcher trigger and verify it opens an "
                            "anchored panel."
                        ),
                        observed=str(error),
                    )
                else:
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=(
                            "Click the desktop switcher trigger and verify it opens an "
                            "anchored panel."
                        ),
                        observed=(
                            f"container_kind={desktop_panel.container_kind}; "
                            f"role={desktop_panel.container_role!r}; "
                            f"anchored={desktop_panel.anchored_to_trigger}; "
                            f"bounds=({desktop_panel.left:.1f}, {desktop_panel.top:.1f}, "
                            f"{desktop_panel.width:.1f}, {desktop_panel.height:.1f})"
                        ),
                    )
                finally:
                    page.close_switcher()

                if desktop_panel is not None:
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the desktop workspace switcher from the live app shell "
                            "and checked where the surface appeared relative to the trigger."
                        ),
                        observed=(
                            f"container_kind={desktop_panel.container_kind}; "
                            f"title={desktop_panel.title_text!r}; "
                            f"text_excerpt={_snippet(desktop_panel.container_text)}"
                        ),
                    )

                try:
                    page.set_viewport(**COMPACT_VIEWPORT)
                except AssertionError as error:
                    step_failures.append(str(error))
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action="Resize the browser to a compact mobile width.",
                        observed=str(error),
                    )
                else:
                    _record_step(
                        result,
                        step=4,
                        status="passed",
                        action="Resize the browser to a compact mobile width.",
                        observed=(
                            f"Viewport settled at {COMPACT_VIEWPORT['width']}x"
                            f"{COMPACT_VIEWPORT['height']}."
                        ),
                    )

                mobile_trigger = page.observe_trigger()
                mobile_trigger_visual = _observe_trigger_visual(
                    page=page,
                    visual_probe=visual_probe,
                    trigger=mobile_trigger,
                )
                result["compact_trigger_observation"] = {
                    **asdict(mobile_trigger),
                    "visual_observation": asdict(mobile_trigger_visual),
                }
                try:
                    _assert_compact_trigger(
                        mobile_trigger,
                        desktop_trigger=desktop_trigger,
                        trigger_visual=mobile_trigger_visual,
                    )
                except AssertionError as error:
                    step_failures.append(str(error))
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action=(
                            "Verify the compact-width switcher trigger uses a condensed, "
                            "icon-led presentation."
                        ),
                        observed=str(error),
                    )
                else:
                    _record_step(
                        result,
                        step=5,
                        status="passed",
                        action=(
                            "Verify the compact-width switcher trigger uses a condensed, "
                            "icon-led presentation."
                        ),
                        observed=(
                            f"lines={list(mobile_trigger.raw_text_lines)!r}; "
                            f"size=({mobile_trigger.width:.1f}x{mobile_trigger.height:.1f}); "
                            f"label={mobile_trigger.semantic_label!r}; "
                            f"visual_icon_visible={mobile_trigger_visual.icon_visible}; "
                            f"top_buttons={list(mobile_trigger.top_button_labels)!r}"
                        ),
                    )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the compact/mobile app shell and checked the switcher "
                        "looked condensed rather than like the desktop button."
                    ),
                    observed=(
                        f"lines={list(mobile_trigger.raw_text_lines)!r}; "
                        f"size=({mobile_trigger.width:.1f}x{mobile_trigger.height:.1f}); "
                        f"text={mobile_trigger.visible_text!r}; "
                        f"visual_icon_visible={mobile_trigger_visual.icon_visible}"
                    ),
                )

                mobile_panel: WorkspaceSwitcherPanelObservation | None = None
                try:
                    page.open_switcher()
                    mobile_panel = page.observe_panel(mobile_trigger)
                    result["compact_panel_observation"] = asdict(mobile_panel)
                    _assert_compact_panel(mobile_panel)
                except AssertionError as error:
                    step_failures.append(str(error))
                    _record_step(
                        result,
                        step=6,
                        status="failed",
                        action=(
                            "Click the compact trigger and verify it opens a bottom sheet "
                            "or full-screen sheet."
                        ),
                        observed=str(error),
                    )
                else:
                    _record_step(
                        result,
                        step=6,
                        status="passed",
                        action=(
                            "Click the compact trigger and verify it opens a bottom sheet "
                            "or full-screen sheet."
                        ),
                        observed=(
                            f"container_kind={mobile_panel.container_kind}; "
                            f"role={mobile_panel.container_role!r}; "
                            f"bottom_aligned={mobile_panel.bottom_aligned}; "
                            f"full_screen_like={mobile_panel.full_screen_like}; "
                            f"bounds=({mobile_panel.left:.1f}, {mobile_panel.top:.1f}, "
                            f"{mobile_panel.width:.1f}, {mobile_panel.height:.1f})"
                        ),
                    )
                finally:
                    page.close_switcher()

                if mobile_panel is not None:
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the compact/mobile workspace switcher and checked the "
                            "surface behaved like a sheet from a user perspective."
                        ),
                        observed=(
                            f"container_kind={mobile_panel.container_kind}; "
                            f"title={mobile_panel.title_text!r}; "
                            f"text_excerpt={_snippet(mobile_panel.container_text)}"
                        ),
                    )

                if step_failures:
                    raise AssertionError(step_failures[0])

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
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


def _assert_desktop_trigger(
    trigger: WorkspaceSwitcherTriggerObservation,
    *,
    trigger_visual: WorkspaceSwitcherTriggerVisualObservation,
    section: str,
) -> None:
    if not trigger.semantic_label.startswith("Workspace switcher:"):
        raise AssertionError(
            f"Step 2 failed: in {section}, the app shell did not expose a workspace "
            "switcher semantics label.\n"
            f"Observed label: {trigger.semantic_label!r}",
        )
    if not trigger.display_name:
        raise AssertionError(
            f"Step 2 failed: in {section}, the workspace switcher did not expose the "
            "active workspace name.\n"
            f"Observed label: {trigger.semantic_label!r}",
        )
    if trigger.workspace_type not in {"Hosted", "Local"}:
        raise AssertionError(
            f"Step 2 failed: in {section}, the workspace switcher did not expose the "
            "active workspace type.\n"
            f"Observed label: {trigger.semantic_label!r}",
        )
    if not trigger.state_label:
        raise AssertionError(
            f"Step 2 failed: in {section}, the workspace switcher did not expose any "
            "workspace state label.\n"
            f"Observed label: {trigger.semantic_label!r}",
        )
    if trigger.state_label not in trigger.visible_text:
        raise AssertionError(
            f"Step 2 failed: in {section}, the desktop switcher did not keep the visible "
            "workspace state badge text in the trigger.\n"
            f"Expected state text: {trigger.state_label!r}\n"
            f"Observed text: {trigger.visible_text!r}",
        )
    if trigger.icon_count <= 0 and not trigger_visual.icon_visible:
        raise AssertionError(
            f"Step 2 failed: in {section}, the desktop switcher did not keep a visible "
            "leading workspace icon.\n"
            f"Observed semantic icon_count: {trigger.icon_count}\n"
            f"Observed visual icon: {trigger_visual.icon_visible}",
        )
    if trigger.height > 40:
        raise AssertionError(
            f"Step 2 failed: in {section}, the desktop switcher trigger did not keep "
            "the expected compact desktop height.\n"
            f"Observed height: {trigger.height}",
        )
    legacy_labels = [
        label
        for label in trigger.top_button_labels
        if label in {"Repository access", "Manage GitHub access", trigger.state_label}
    ]
    if legacy_labels:
        raise AssertionError(
            f"Step 2 failed: in {section}, the old repository-access control still "
            "appeared alongside the workspace switcher.\n"
            f"Observed top button labels: {list(trigger.top_button_labels)!r}",
        )


def _assert_desktop_panel(
    *,
    panel: WorkspaceSwitcherPanelObservation,
    trigger: WorkspaceSwitcherTriggerObservation,
) -> None:
    if panel.title_text != "Workspace switcher":
        raise AssertionError(
            "Step 3 failed: opening the desktop switcher did not show the expected "
            "workspace-switcher title.\n"
            f"Observed title: {panel.title_text!r}\n"
            f"Observed container text: {panel.container_text}",
        )
    if trigger.display_name not in panel.container_text:
        raise AssertionError(
            "Step 3 failed: opening the desktop switcher did not show the active "
            "workspace summary in the opened surface.\n"
            f"Expected workspace name: {trigger.display_name!r}\n"
            f"Observed container text: {panel.container_text}",
        )
    if panel.container_kind != "anchored-panel":
        raise AssertionError(
            "Step 3 failed: clicking the desktop workspace switcher did not open an "
            "anchored panel.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}\n"
            f"Trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )


def _assert_compact_trigger(
    trigger: WorkspaceSwitcherTriggerObservation,
    *,
    desktop_trigger: WorkspaceSwitcherTriggerObservation,
    trigger_visual: WorkspaceSwitcherTriggerVisualObservation,
) -> None:
    if trigger.height < 44:
        raise AssertionError(
            "Step 5 failed: the compact workspace switcher did not expand to a "
            "touch-friendly mobile height.\n"
            f"Observed height: {trigger.height}",
        )
    if trigger.width < trigger.viewport_width * 0.55:
        raise AssertionError(
            "Step 5 failed: the compact workspace switcher did not render in a visible "
            "condensed mobile-width presentation.\n"
            f"Observed width: {trigger.width}\n"
            f"Viewport width: {trigger.viewport_width}",
        )
    if trigger.top < 40:
        raise AssertionError(
            "Step 5 failed: the compact workspace switcher did not move into the "
            "stacked mobile header presentation.\n"
            f"Observed top offset: {trigger.top}",
        )
    if trigger.height <= desktop_trigger.height:
        raise AssertionError(
            "Step 5 failed: the compact workspace switcher did not visibly change from "
            "the desktop trigger height.\n"
            f"Desktop height: {desktop_trigger.height}\n"
            f"Compact height: {trigger.height}",
        )
    if trigger.icon_count <= 0 and not trigger_visual.icon_visible:
        raise AssertionError(
            "Step 5 failed: the compact workspace switcher did not keep a visible "
            "leading icon for the icon-led mobile presentation.\n"
            f"Observed semantic icon_count: {trigger.icon_count}\n"
            f"Observed visual icon: {trigger_visual.icon_visible}",
        )
    if any(label in DESKTOP_SECTIONS for label in trigger.top_button_labels):
        raise AssertionError(
            "Step 5 failed: the compact workspace switcher still shared the desktop "
            "top-row navigation layout instead of the stacked mobile header.\n"
            f"Observed top buttons: {list(trigger.top_button_labels)!r}",
        )


def _assert_compact_panel(panel: WorkspaceSwitcherPanelObservation) -> None:
    if panel.title_text != "Workspace switcher":
        raise AssertionError(
            "Step 6 failed: opening the compact workspace switcher did not show the "
            "expected workspace-switcher title.\n"
            f"Observed title: {panel.title_text!r}",
        )
    if panel.container_kind not in {"bottom-sheet", "full-screen-sheet"}:
        raise AssertionError(
            "Step 6 failed: clicking the compact workspace switcher did not open a "
            "bottom sheet or full-screen sheet.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
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
    error = str(result.get("error", "AssertionError: TS-722 failed"))
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
            "* Verified the app shell across *Dashboard*, *Board*, *JQL Search*, and "
            "*Settings* to confirm the old repository-access button was replaced by a "
            "workspace switcher showing the active workspace name, icon, and state."
        ),
        (
            "* Verified the opened switcher container on desktop and after resizing to "
            "a compact/mobile width."
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
            "- Checked the live app shell in **Dashboard**, **Board**, **JQL Search**, "
            "and **Settings** to verify the legacy repository-access button had been "
            "replaced by a workspace switcher."
        ),
        (
            "- Opened the switcher on desktop, resized to a compact/mobile width, and "
            "opened it again to verify the container adapted by layout."
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
            else "- Outcome: the live app shell exposed the workspace switcher across sections and adapted the trigger/container between desktop and compact layouts."
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
            f"# {TICKET_KEY} - Workspace switcher app-shell regression",
            "",
            "## Steps to reproduce",
            "1. Launch the deployed TrackState application on a desktop browser.",
            "2. Verify the previous standalone repository-access button is replaced by a workspace switcher showing the active workspace name, icon, and state badge.",
            "3. Click the switcher trigger and verify it opens an anchored panel.",
            "4. Resize the browser to a compact/mobile width.",
            "5. Verify the switcher trigger uses a condensed, icon-led presentation.",
            "6. Click the trigger and verify it opens a bottom sheet or full-screen sheet.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(
                result,
                1,
                "Launch the deployed TrackState application on a desktop browser.",
            ),
            _annotated_step_line(
                result,
                2,
                "Verify the old repository-access button is replaced by a workspace switcher across tracker sections.",
            ),
            _annotated_step_line(
                result,
                3,
                "Click the desktop switcher trigger and verify it opens an anchored panel.",
            ),
            _annotated_step_line(
                result,
                4,
                "Resize the browser to a compact/mobile width.",
            ),
            _annotated_step_line(
                result,
                5,
                "Verify the compact switcher trigger uses a condensed, icon-led presentation.",
            ),
            _annotated_step_line(
                result,
                6,
                "Click the compact trigger and verify it opens a bottom sheet or full-screen sheet.",
            ),
            "",
            "## Actual vs Expected",
            (
                "- Expected: the app shell replaces the legacy repository-access button "
                "with a workspace switcher across tracker sections, the desktop trigger "
                "opens an anchored panel, and the compact trigger opens a bottom sheet "
                "or full-screen sheet."
            ),
            f"- Actual: {result.get('error', '<missing error>')}",
            "",
            "## Environment",
            f"- URL: `{result.get('app_url', '')}`",
            f"- Repository: `{result.get('repository', '')}` @ `{result.get('repository_ref', '')}`",
            f"- Browser: `{result.get('browser', 'Chromium (Playwright)')}`",
            f"- OS: `{result.get('os', '')}`",
            f"- Screenshot: `{result.get('screenshot', str(FAILURE_SCREENSHOT_PATH))}`",
            "",
            "## Desktop section observations",
            "```json",
            json.dumps(result.get("desktop_section_observations", {}), indent=2),
            "```",
            "",
            "## Panel observations",
            "```json",
            json.dumps(
                {
                    "desktop_panel_observation": result.get("desktop_panel_observation", {}),
                    "compact_panel_observation": result.get("compact_panel_observation", {}),
                },
                indent=2,
            ),
            "```",
            "",
            "## Exact error message / traceback",
            "```text",
            str(result.get("traceback", result.get("error", "<missing traceback>"))),
            "```",
        ],
    ) + "\n"


def _annotated_step_line(result: dict[str, object], step_number: int, action: str) -> str:
    status = _step_status(result, step_number)
    marker = "✅" if status == "passed" else "❌"
    return f"- {marker} {action}\n  Actual: {_step_observation(result, step_number)}"


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    if jira:
        return [f"{prefix} Screenshot: {{{{{screenshot}}}}}"]
    return [f"{prefix} Screenshot: `{screenshot}`"]


def _observe_trigger_visual(
    *,
    page: LiveWorkspaceSwitcherPage,
    visual_probe: LiveWorkspaceSwitcherVisualProbe,
    trigger: WorkspaceSwitcherTriggerObservation,
) -> WorkspaceSwitcherTriggerVisualObservation:
    with tempfile.NamedTemporaryFile(
        dir=OUTPUTS_DIR,
        prefix="ts722_trigger_",
        suffix=".png",
        delete=False,
    ) as handle:
        screenshot_path = Path(handle.name)
    try:
        page.screenshot(str(screenshot_path))
        return visual_probe.observe_trigger(
            screenshot_path=screenshot_path,
            trigger=trigger,
        )
    finally:
        screenshot_path.unlink(missing_ok=True)


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
    lines = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    return lines or [f"{prefix} <no human-style verification recorded>"]


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


def _snippet(value: str, *, limit: int = 240) -> str:
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 3]}..."


if __name__ == "__main__":
    main()
