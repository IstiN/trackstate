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
    WorkspaceSwitcherTransitionMonitorObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-797"
TEST_CASE_TITLE = (
    "Resize viewport with open workspace switcher - container type transforms dynamically"
)
RUN_COMMAND = "PYTHONPATH=. python3 testing/tests/TS-797/test_ts_797.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
COMPACT_VIEWPORT = {"width": 390, "height": 844}
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts797_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts797_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-797 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
    }

    page: LiveWorkspaceSwitcherPage | None = None
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
                        "desktop state before the resize scenario began.\n"
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
                    action="Launch the application on a desktop browser.",
                    observed=(
                        f"Opened the deployed app at {config.app_url} in Chromium and "
                        f"reached Dashboard at {DESKTOP_VIEWPORT['width']}x"
                        f"{DESKTOP_VIEWPORT['height']}."
                    ),
                )

                desktop_trigger = page.observe_trigger()
                result["desktop_trigger_observation"] = asdict(desktop_trigger)

                try:
                    desktop_switcher = page.open_and_observe()
                    desktop_panel = page.observe_open_panel()
                    _assert_desktop_open(
                        trigger_name=desktop_trigger.display_name,
                        switcher=desktop_switcher,
                        panel=desktop_panel,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action="Click the workspace switcher trigger to open the anchored panel.",
                        observed=str(error),
                    )
                    raise
                result["desktop_open_observation"] = {
                    "switcher": asdict(desktop_switcher),
                    "panel": asdict(desktop_panel),
                }
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Click the workspace switcher trigger to open the anchored panel.",
                    observed=(
                        f"container_kind={desktop_panel.container_kind}; "
                        f"anchored_to_trigger={desktop_panel.anchored_to_trigger}; "
                        f"background_dimmed={desktop_panel.background_dimmed}; "
                        f"title_visible={'Workspace switcher' in desktop_switcher.switcher_text}; "
                        f"active_workspace={_selected_workspace_name(desktop_switcher)!r}; "
                        f"row_count={desktop_switcher.row_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the workspace switcher on desktop and checked the user-facing "
                        "title, active workspace row, and anchored placement next to the trigger."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"active_workspace={_selected_workspace_name(desktop_switcher)!r}; "
                        f"text_excerpt={_snippet(desktop_switcher.switcher_text)}"
                    ),
                )

                page.start_transition_monitor()
                try:
                    page.observe_open_switcher()
                    page.set_viewport(**COMPACT_VIEWPORT)
                    mobile_switcher = page.observe_open_switcher()
                    to_mobile_monitor = page.read_transition_monitor(clear=True)
                    mobile_panel = page.observe_open_panel()
                    _assert_mobile_transition(
                        desktop_switcher=desktop_switcher,
                        mobile_switcher=mobile_switcher,
                        mobile_panel=mobile_panel,
                        monitor=to_mobile_monitor,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action="Resize the browser while the panel stays open to a compact mobile width.",
                        observed=str(error),
                    )
                    raise
                result["to_mobile_observation"] = {
                    "switcher": asdict(mobile_switcher),
                    "panel": asdict(mobile_panel),
                    "monitor": asdict(to_mobile_monitor),
                }
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Resize the browser while the panel stays open to a compact mobile width.",
                    observed=(
                        f"Viewport settled at {COMPACT_VIEWPORT['width']}x"
                        f"{COMPACT_VIEWPORT['height']} with the switcher still visible."
                    ),
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Observe the switcher container transition on the compact/mobile layout.",
                    observed=(
                        f"container_kind={mobile_panel.container_kind}; "
                        f"bottom_aligned={mobile_panel.bottom_aligned}; "
                        f"background_dimmed={mobile_panel.background_dimmed}; "
                        f"monitor_kinds={list(to_mobile_monitor.observed_container_kinds)!r}; "
                        f"active_workspace={_selected_workspace_name(mobile_switcher)!r}; "
                        f"row_count={mobile_switcher.row_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the open switcher after shrinking to mobile width and checked "
                        "that it behaved like a bottom sheet without losing the visible state."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"active_workspace={_selected_workspace_name(mobile_switcher)!r}; "
                        f"text_excerpt={_snippet(mobile_switcher.switcher_text)}"
                    ),
                )

                page.start_transition_monitor()
                try:
                    page.observe_open_switcher()
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    restored_switcher = page.observe_open_switcher()
                    to_desktop_monitor = page.read_transition_monitor(clear=True)
                    restored_panel = page.observe_open_panel()
                    _assert_desktop_restore(
                        desktop_switcher=desktop_switcher,
                        restored_switcher=restored_switcher,
                        restored_panel=restored_panel,
                        monitor=to_desktop_monitor,
                    )
                except Exception as error:
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action="Resize the browser back to desktop width while the switcher stays open.",
                        observed=str(error),
                    )
                    raise
                result["back_to_desktop_observation"] = {
                    "switcher": asdict(restored_switcher),
                    "panel": asdict(restored_panel),
                    "monitor": asdict(to_desktop_monitor),
                }
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Resize the browser back to desktop width while the switcher stays open.",
                    observed=(
                        f"container_kind={restored_panel.container_kind}; "
                        f"anchored_to_trigger={restored_panel.anchored_to_trigger}; "
                        f"background_dimmed={restored_panel.background_dimmed}; "
                        f"monitor_kinds={list(to_desktop_monitor.observed_container_kinds)!r}; "
                        f"active_workspace={_selected_workspace_name(restored_switcher)!r}; "
                        f"row_count={restored_switcher.row_count}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the same open switcher after expanding back to desktop width "
                        "and checked that it returned to the anchored-panel presentation."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"active_workspace={_selected_workspace_name(restored_switcher)!r}; "
                        f"text_excerpt={_snippet(restored_switcher.switcher_text)}"
                    ),
                )

                page.close_switcher()
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
            finally:
                page.stop_transition_monitor()
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


def _assert_desktop_open(
    *,
    trigger_name: str,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
) -> None:
    if switcher.row_count <= 0:
        raise AssertionError(
            "Step 2 failed: opening the workspace switcher did not expose any workspace rows.\n"
            f"Observed switcher text: {switcher.switcher_text}",
        )
    active_workspace = _selected_workspace_name(switcher)
    if active_workspace != trigger_name:
        raise AssertionError(
            "Step 2 failed: the anchored panel did not keep the same active workspace that "
            "the desktop trigger summarized.\n"
            f"Trigger workspace: {trigger_name!r}\n"
            f"Active workspace row: {active_workspace!r}",
        )
    if "Workspace switcher" not in switcher.switcher_text:
        raise AssertionError(
            "Step 2 failed: the opened desktop surface did not show the expected "
            "Workspace switcher heading.\n"
            f"Observed text: {switcher.switcher_text!r}",
        )
    if panel.container_kind != "anchored-panel" or not panel.anchored_to_trigger:
        raise AssertionError(
            "Step 2 failed: clicking the workspace switcher did not open the anchored "
            "desktop panel.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Anchored to trigger: {panel.anchored_to_trigger}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if panel.background_dimmed:
        raise AssertionError(
            "Step 2 failed: the desktop workspace switcher dimmed the background like a "
            "modal dialog instead of behaving like an anchored panel.",
        )


def _assert_mobile_transition(
    *,
    desktop_switcher: WorkspaceSwitcherObservation,
    mobile_switcher: WorkspaceSwitcherObservation,
    mobile_panel: WorkspaceSwitcherPanelObservation,
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
) -> None:
    _assert_same_switcher_state(
        reference=desktop_switcher,
        candidate=mobile_switcher,
        step="Step 4",
        scenario="after shrinking the viewport to mobile width",
    )
    if "Workspace switcher" not in mobile_switcher.switcher_text:
        raise AssertionError(
            "Step 4 failed: the open mobile surface no longer showed the expected "
            "Workspace switcher heading.\n"
            f"Observed text: {mobile_switcher.switcher_text!r}",
        )
    if mobile_panel.container_kind != "bottom-sheet":
        raise AssertionError(
            "Step 4 failed: the open workspace switcher did not transform into a mobile "
            "bottom sheet after the viewport shrank.\n"
            f"Observed container kind: {mobile_panel.container_kind}\n"
            f"Observed bounds: left={mobile_panel.left:.1f}, top={mobile_panel.top:.1f}, "
            f"width={mobile_panel.width:.1f}, height={mobile_panel.height:.1f}",
        )
    if not mobile_panel.bottom_aligned or not mobile_panel.background_dimmed:
        raise AssertionError(
            "Step 4 failed: the compact layout did not present the switcher like a user-"
            "visible bottom sheet.\n"
            f"Bottom aligned: {mobile_panel.bottom_aligned}\n"
            f"Background dimmed: {mobile_panel.background_dimmed}",
        )
    _assert_monitor_continuity(
        monitor,
        step="Step 4",
    )


def _assert_desktop_restore(
    *,
    desktop_switcher: WorkspaceSwitcherObservation,
    restored_switcher: WorkspaceSwitcherObservation,
    restored_panel: WorkspaceSwitcherPanelObservation,
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
) -> None:
    _assert_same_switcher_state(
        reference=desktop_switcher,
        candidate=restored_switcher,
        step="Step 5",
        scenario="after expanding the viewport back to desktop width",
    )
    if "Workspace switcher" not in restored_switcher.switcher_text:
        raise AssertionError(
            "Step 5 failed: the restored desktop surface no longer showed the expected "
            "Workspace switcher heading.\n"
            f"Observed text: {restored_switcher.switcher_text!r}",
        )
    if (
        restored_panel.container_kind != "anchored-panel"
        or not restored_panel.anchored_to_trigger
        or restored_panel.background_dimmed
    ):
        raise AssertionError(
            "Step 5 failed: the still-open workspace switcher did not return to the "
            "anchored desktop panel after the viewport expanded.\n"
            f"Observed container kind: {restored_panel.container_kind}\n"
            f"Anchored to trigger: {restored_panel.anchored_to_trigger}\n"
            f"Background dimmed: {restored_panel.background_dimmed}\n"
            f"Observed bounds: left={restored_panel.left:.1f}, top={restored_panel.top:.1f}, "
            f"width={restored_panel.width:.1f}, height={restored_panel.height:.1f}",
        )
    _assert_monitor_continuity(
        monitor,
        step="Step 5",
    )


def _assert_same_switcher_state(
    *,
    reference: WorkspaceSwitcherObservation,
    candidate: WorkspaceSwitcherObservation,
    step: str,
    scenario: str,
) -> None:
    if candidate.row_count != reference.row_count:
        raise AssertionError(
            f"{step} failed: the workspace switcher lost rows {scenario}.\n"
            f"Expected row count: {reference.row_count}\n"
            f"Observed row count: {candidate.row_count}",
        )
    reference_names = _workspace_names(reference)
    candidate_names = _workspace_names(candidate)
    if candidate_names != reference_names:
        raise AssertionError(
            f"{step} failed: the workspace list changed {scenario}.\n"
            f"Expected rows: {list(reference_names)!r}\n"
            f"Observed rows: {list(candidate_names)!r}",
        )
    reference_active = _selected_workspace_name(reference)
    candidate_active = _selected_workspace_name(candidate)
    if candidate_active != reference_active:
        raise AssertionError(
            f"{step} failed: the active workspace changed {scenario}.\n"
            f"Expected active workspace: {reference_active!r}\n"
            f"Observed active workspace: {candidate_active!r}",
        )


def _assert_monitor_continuity(
    monitor: WorkspaceSwitcherTransitionMonitorObservation,
    *,
    step: str,
) -> None:
    if monitor.sample_count <= 0 or monitor.visible_sample_count <= 0:
        raise AssertionError(
            f"{step} failed: no transition samples were captured while the open workspace "
            "switcher resized.",
        )
    if monitor.ever_hidden_after_visible:
        raise AssertionError(
            f"{step} failed: the open workspace switcher disappeared during the resize "
            "transition instead of staying visible.\n"
            f"Observed kinds: {list(monitor.observed_container_kinds)!r}\n"
            f"Hidden samples: {monitor.hidden_sample_count}",
        )


def _selected_workspace_name(observation: WorkspaceSwitcherObservation) -> str:
    for row in observation.rows:
        if row.selected and row.display_name:
            return row.display_name
    raise AssertionError(
        "The open workspace switcher did not expose a selected active workspace row.\n"
        f"Observed switcher text: {observation.switcher_text}",
    )


def _workspace_names(observation: WorkspaceSwitcherObservation) -> tuple[str, ...]:
    return tuple(row.display_name or "" for row in observation.rows)


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
    error = str(result.get("error", "AssertionError: TS-797 failed"))
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
            "* Opened the live workspace switcher on desktop, kept it open during both "
            "viewport changes, and validated the visible container type before and after "
            "each resize."
        ),
        (
            "* Verified the visible switcher state from a user perspective by checking the "
            "heading, active workspace row, and current workspace list before mobile, on "
            "mobile, and after returning to desktop."
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
            "- Opened the live workspace switcher on desktop and kept it open while the "
            "viewport changed to compact/mobile and back again."
        ),
        (
            "- Verified the user-visible heading, active workspace row, and workspace list "
            "before the resize, after the bottom-sheet transition, and after the anchored "
            "desktop panel returned."
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
            "- Added TS-797 live Playwright coverage for the already-open workspace "
            "switcher resize flow, including continuity checks so the container must stay "
            "visible while it morphs between desktop and mobile layouts."
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
            else "- Outcome: the open switcher stayed visible, changed from the desktop anchored panel to a bottom sheet on mobile, preserved its workspace state, and returned to the anchored desktop panel."
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
            f"# {TICKET_KEY} - Open workspace switcher does not transform correctly during viewport resize",
            "",
            "## Steps to reproduce",
            "1. Launch the application on a desktop browser.",
            "2. Click the workspace switcher trigger to open the anchored panel.",
            "3. While the panel remains visible, resize the browser window to a compact mobile width.",
            "4. Observe the switcher container transition.",
            "5. Resize the window back to desktop width.",
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
                "Click the workspace switcher trigger to open the anchored panel.",
            ),
            _annotated_step_line(
                result,
                3,
                "Resize the browser while the panel stays open to a compact mobile width.",
            ),
            _annotated_step_line(
                result,
                4,
                "Observe the switcher container transition on the compact/mobile layout.",
            ),
            _annotated_step_line(
                result,
                5,
                "Resize the browser back to desktop width while the switcher stays open.",
            ),
            "",
            "## Actual vs Expected",
            (
                "- Expected: the already-open workspace switcher stays visible, morphs from "
                "an anchored desktop panel into a mobile bottom sheet when the viewport "
                "shrinks, preserves its current workspace state, and then returns to an "
                "anchored desktop panel when the viewport expands again."
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
            "## Failing command",
            "```bash",
            RUN_COMMAND,
            "```",
            "",
            "## Observations",
            "```json",
            json.dumps(
                {
                    "desktop_open_observation": result.get("desktop_open_observation", {}),
                    "to_mobile_observation": result.get("to_mobile_observation", {}),
                    "back_to_desktop_observation": result.get(
                        "back_to_desktop_observation",
                        {},
                    ),
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
