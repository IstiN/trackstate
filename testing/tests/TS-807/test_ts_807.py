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
    WorkspaceSwitcherInternalClickObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-807"
TEST_CASE_TITLE = "Interact with workspace switcher internal area - panel remains open"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-807/test_ts_807.py"
TEST_FILE_PATH = "testing/tests/TS-807/test_ts_807.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
REQUEST_STEPS = [
    "Launch the application on a desktop browser.",
    "Click the workspace switcher trigger to open the panel.",
    "Click on a non-interactive area or a blank space inside the opened switcher panel.",
    "Observe the state of the workspace switcher panel.",
]
EXPECTED_RESULT = "The workspace switcher panel remains open and functional."

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts807_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts807_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-807 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "test_file": TEST_FILE_PATH,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "expected_result": EXPECTED_RESULT,
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
                try:
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop tracker state before the workspace-switcher scenario "
                            "started.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )
                    page.dismiss_connection_banner()
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger = page.observe_trigger()
                    result["desktop_trigger_observation"] = asdict(trigger)
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
                        f"trigger_label={trigger.semantic_label!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop tracker shell before opening the switcher and "
                        "confirmed the user-facing workspace switcher trigger was visible."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"trigger_label={trigger.semantic_label!r}"
                    ),
                )

                try:
                    page.open_switcher()
                    panel_before = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                    )
                    switcher_before = page.observe_open_switcher()
                    _assert_desktop_panel_open(
                        panel=panel_before,
                        switcher=switcher_before,
                    )
                    result["panel_before_click"] = asdict(panel_before)
                    result["switcher_before_click"] = _switcher_to_dict(switcher_before)
                except AssertionError as error:
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
                        f"container_kind={panel_before.container_kind}; "
                        f"row_count={switcher_before.row_count}; "
                        f"active_workspace={_selected_workspace_name(switcher_before)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the desktop workspace switcher and looked at the visible "
                        "panel title and saved workspace rows as a user would."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"active_workspace={_selected_workspace_name(switcher_before)!r}; "
                        f"text_excerpt={_snippet(switcher_before.switcher_text)}"
                    ),
                )

                try:
                    inside_click = page.click_blank_area_inside_open_panel()
                    result["inside_click_observation"] = asdict(inside_click)
                    _assert_inside_click_target(inside_click)
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
                        f"clicked_point=({inside_click.click_x:.1f}, {inside_click.click_y:.1f}); "
                        "the inside-click probe completed and the workspace switcher "
                        "remained visible through the post-click stability window."
                    ),
                )

                try:
                    panel_after = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=10_000,
                    )
                    switcher_after = page.observe_open_switcher(timeout_ms=10_000)
                    _assert_switcher_still_open_and_functional(
                        before_panel=panel_before,
                        after_panel=panel_after,
                        before_switcher=switcher_before,
                        after_switcher=switcher_after,
                    )
                    result["panel_after_click"] = asdict(panel_after)
                    result["switcher_after_click"] = _switcher_to_dict(switcher_after)
                except AssertionError as error:
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
                        f"container_kind={panel_after.container_kind}; "
                        f"row_count={switcher_after.row_count}; "
                        f"active_workspace={_selected_workspace_name(switcher_after)!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "After clicking the blank internal panel area, looked again at the "
                        "visible switcher heading and workspace rows to confirm the panel "
                        "stayed on screen instead of dismissing."
                    ),
                    observed=(
                        "title='Workspace switcher'; "
                        f"active_workspace={_selected_workspace_name(switcher_after)!r}; "
                        f"text_excerpt={_snippet(switcher_after.switcher_text)}"
                    ),
                )

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                if page is not None:
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


def _assert_desktop_panel_open(
    *,
    panel: WorkspaceSwitcherPanelObservation,
    switcher: WorkspaceSwitcherObservation,
) -> None:
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 2 failed: clicking the desktop workspace switcher did not open the "
            "expected desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed container text: {panel.container_text}",
        )
    if panel.background_dimmed:
        raise AssertionError(
            "Step 2 failed: opening the desktop workspace switcher dimmed the "
            "background like a modal dialog.\n"
            f"Observed container kind: {panel.container_kind}",
        )
    if switcher.row_count <= 0:
        raise AssertionError(
            "Step 2 failed: opening the workspace switcher did not expose any visible "
            "workspace rows.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if "Workspace switcher" not in switcher.switcher_text:
        raise AssertionError(
            "Step 2 failed: the open desktop surface did not show the visible "
            '"Workspace switcher" heading.\n'
            f"Observed switcher text:\n{switcher.switcher_text}",
        )


def _assert_inside_click_target(
    observation: WorkspaceSwitcherInternalClickObservation,
) -> None:
    if observation.panel_width <= 0 or observation.panel_height <= 0:
        raise AssertionError(
            "Step 3 failed: the inside-click probe did not resolve a valid workspace "
            "switcher panel area.\n"
            f"Observed panel bounds: left={observation.panel_left:.1f}, "
            f"top={observation.panel_top:.1f}, width={observation.panel_width:.1f}, "
            f"height={observation.panel_height:.1f}",
        )


def _assert_switcher_still_open_and_functional(
    *,
    before_panel: WorkspaceSwitcherPanelObservation,
    after_panel: WorkspaceSwitcherPanelObservation,
    before_switcher: WorkspaceSwitcherObservation,
    after_switcher: WorkspaceSwitcherObservation,
) -> None:
    if after_panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 4 failed: after clicking inside the open switcher, the desktop panel "
            "changed into an unexpected container or disappeared.\n"
            f"Observed container kind: {after_panel.container_kind}\n"
            f"Observed container text: {after_panel.container_text}",
        )
    if after_panel.background_dimmed:
        raise AssertionError(
            "Step 4 failed: after the inside click, the desktop workspace switcher "
            "started dimming the background like a modal.\n"
            f"Observed container kind: {after_panel.container_kind}",
        )
    if after_switcher.row_count <= 0:
        raise AssertionError(
            "Step 4 failed: after clicking a non-interactive area inside the panel, the "
            "workspace switcher no longer exposed any visible workspace rows.\n"
            f"Observed switcher text:\n{after_switcher.switcher_text}",
        )
    if "Workspace switcher" not in after_switcher.switcher_text:
        raise AssertionError(
            "Step 4 failed: after clicking inside the panel, the visible workspace "
            'switcher heading disappeared.\n'
            f"Observed switcher text:\n{after_switcher.switcher_text}",
        )
    before_active = _selected_workspace_name(before_switcher)
    after_active = _selected_workspace_name(after_switcher)
    if before_active and after_active and before_active != after_active:
        raise AssertionError(
            "Step 4 failed: clicking a non-interactive area inside the workspace "
            "switcher unexpectedly changed the active workspace selection.\n"
            f"Observed active workspace before click: {before_active!r}\n"
            f"Observed active workspace after click: {after_active!r}",
        )
    if before_switcher.row_count != after_switcher.row_count:
        raise AssertionError(
            "Step 4 failed: clicking a non-interactive area inside the workspace "
            "switcher changed the visible workspace row count instead of keeping the "
            "panel stable.\n"
            f"Observed row count before click: {before_switcher.row_count}\n"
            f"Observed row count after click: {after_switcher.row_count}",
        )
    if before_panel.container_kind != after_panel.container_kind:
        raise AssertionError(
            "Step 4 failed: clicking a non-interactive area inside the workspace "
            "switcher changed the desktop container type unexpectedly.\n"
            f"Observed container kind before click: {before_panel.container_kind}\n"
            f"Observed container kind after click: {after_panel.container_kind}",
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
    error = str(result.get("error", "AssertionError: TS-807 failed"))
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
        "* Opened the desktop workspace switcher panel.",
        (
            "* Clicked a non-interactive internal panel area and verified the live "
            "workspace switcher stayed open instead of dismissing."
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
        "h4. Test file",
        "{code}",
        TEST_FILE_PATH,
        "{code}",
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
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
        "- Opened the desktop workspace switcher panel.",
        (
            "- Clicked a non-interactive or blank internal panel area and verified the "
            "workspace switcher stayed open and readable."
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
            "- Added TS-807 live desktop coverage for workspace-switcher inside-click "
            "stability in the deployed web app."
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
            f"# {TICKET_KEY} - Clicking inside the desktop workspace switcher dismisses or destabilizes the panel",
            "",
            "h4. Environment",
            f"* URL: {result.get('app_url')}",
            (
                f"* Repository: {result.get('repository')} @ "
                f"{result.get('repository_ref')}"
            ),
            f"* Browser: {result.get('browser')}",
            f"* OS: {result.get('os')}",
            f"* Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"* Run command: {RUN_COMMAND}",
            "",
            "h4. Steps to Reproduce",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            "",
            "h4. Expected Result",
            EXPECTED_RESULT,
            "",
            "h4. Actual Result",
            str(result.get("error", "<missing error>")),
            "",
            "h4. Logs / Error Output",
            "{code}",
            str(result.get("traceback", result.get("error", ""))),
            "{code}",
            "",
            "h4. Notes",
            f"* Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
        ],
    ) + "\n"


def _annotated_step_line(
    result: dict[str, object],
    step_number: int,
    action: str,
) -> str:
    marker = "✅" if _step_status(result, step_number) == "passed" else "❌"
    return (
        f"# {marker} Step {step_number}: {action}\n"
        f"  Actual: {_step_observation(result, step_number)}"
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
    click_observation = result.get("inside_click_observation")
    if isinstance(click_observation, dict):
        return (
            "the desktop workspace switcher stayed open after a non-interactive "
            f"inside click at ({click_observation.get('click_x')}, "
            f"{click_observation.get('click_y')}) and kept exposing the same "
            "workspace rows."
        )
    return (
        "the desktop workspace switcher stayed open and functional after clicking "
        "a non-interactive area inside the panel."
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


def _selected_workspace_name(switcher: WorkspaceSwitcherObservation) -> str | None:
    for row in switcher.rows:
        if row.selected and row.display_name:
            return row.display_name
    return None


def _switcher_to_dict(
    switcher: WorkspaceSwitcherObservation,
) -> dict[str, object]:
    return {
        "body_text": switcher.body_text,
        "switcher_text": switcher.switcher_text,
        "row_count": switcher.row_count,
        "rows": [asdict(row) for row in switcher.rows],
    }


def _snippet(text: str, *, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


if __name__ == "__main__":
    main()
