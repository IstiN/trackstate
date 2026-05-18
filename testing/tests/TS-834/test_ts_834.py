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
    BackgroundScrollObservation,
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherSavedWorkspaceRowObservation,
    WorkspaceSwitcherTransitionMonitorObservation,
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

TICKET_KEY = "TS-834"
TEST_CASE_TITLE = (
    "Press Arrow Down in workspace switcher — background page scroll is prevented"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-834/test_ts_834.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 760}
KEY_STABILITY_MS = 1_000
SCROLL_TOLERANCE_PX = 1.0
MIN_SCROLL_TARGET_Y = 240.0
DEFAULT_BRANCH = "main"
ACTIVE_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECONDARY_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
SECONDARY_WRITE_BRANCH = "ts-834-alt"

PRECONDITIONS = [
    "The application page content exceeds the viewport height, making the background scrollable.",
    "The workspace switcher panel is open.",
]
REQUEST_STEPS = [
    "Note the current vertical scroll position of the background page.",
    "Press the 'Arrow Down' key to navigate through the saved workspaces.",
]
EXPECTED_RESULT = (
    "The selection index within the switcher increments correctly, but the "
    "background page remains at its original scroll position without moving."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts834_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts834_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-834 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "key_stability_ms": KEY_STABILITY_MS,
        "scroll_tolerance_px": SCROLL_TOLERANCE_PX,
        "preconditions": PRECONDITIONS,
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
                        "desktop state before the Arrow Down scroll-prevention scenario began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.navigate_to_section("Settings")
                page.set_viewport(**DESKTOP_VIEWPORT)
                trigger = page.observe_trigger()
                result["trigger_observation"] = _trigger_payload(trigger)

                try:
                    baseline_scroll = _prepare_scrollable_open_switcher(page=page, result=result)
                except Exception as error:
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
                        f"trigger_text={trigger.visible_text!r}; "
                        f"scroll_before_arrow={baseline_scroll.scroll_y:.1f}px; "
                        f"max_scroll={baseline_scroll.max_scroll_y:.1f}px; "
                        f"viewport_height={baseline_scroll.viewport_height:.1f}px; "
                        f"active_workspace={result['active_workspace_before_arrow']!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live desktop page in a visibly scrolled state and "
                        "confirmed the workspace switcher stayed open on top of the "
                        "Settings content before pressing Arrow Down."
                    ),
                    observed=(
                        f"scroll_before_arrow={baseline_scroll.scroll_y:.1f}px; "
                        f"title='Workspace switcher'; "
                        f"text_excerpt={_snippet(str(result.get('switcher_text_before_arrow', '')))}"
                    ),
                )

                arrow_down = _press_arrow_down_and_observe(
                    page=page,
                    before_scroll=baseline_scroll,
                )
                result["arrow_down_observation"] = arrow_down
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Arrow Down from the visible saved-workspace surface and "
                        "watched for both the active-row change and any jump in the "
                        "background page position."
                    ),
                    observed=(
                        f"active_before={result['active_workspace_before_arrow']!r}; "
                        f"active_after={arrow_down['active_workspace_name']!r}; "
                        f"scroll_before={arrow_down['before_scroll']['scroll_y']:.1f}px; "
                        f"scroll_after={arrow_down['after_scroll']['scroll_y']:.1f}px; "
                        f"text_excerpt={_snippet(arrow_down['switcher']['switcher_text'])}"
                    ),
                )
                try:
                    _assert_arrow_down_navigated_without_background_scroll(
                        observation=arrow_down,
                        before_active_workspace=str(
                            result.get("active_workspace_before_arrow"),
                        ),
                        expected_active_workspace=SECONDARY_WORKSPACE_DISPLAY_NAME,
                        expected_scroll_y=baseline_scroll.scroll_y,
                    )
                except Exception as error:
                    result["product_gap"] = (
                        "On the scrollable Settings surface, pressing Arrow Down inside "
                        "the desktop workspace switcher leaves the active saved "
                        f"workspace on {result['active_workspace_before_arrow']!r} "
                        f"instead of moving to {SECONDARY_WORKSPACE_DISPLAY_NAME!r}, "
                        "even though the background scroll position stays fixed."
                    )
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
                        f"active_workspace_after={arrow_down['active_workspace_name']!r}; "
                        f"scroll_after_arrow={arrow_down['after_scroll']['scroll_y']:.1f}px; "
                        f"scroll_delta={arrow_down['scroll_delta']:.1f}px; "
                        f"panel_kind={arrow_down['panel']['container_kind']!r}; "
                        f"monitor_hidden_after_visible="
                        f"{arrow_down['monitor']['ever_hidden_after_visible']}"
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


def _prepare_scrollable_open_switcher(
    *,
    page: LiveWorkspaceSwitcherPage,
    result: dict[str, object],
) -> BackgroundScrollObservation:
    initial_scroll = page.observe_background_scroll()
    result["initial_scroll"] = _background_scroll_payload(initial_scroll)
    if initial_scroll.max_scroll_y <= SCROLL_TOLERANCE_PX:
        raise AssertionError(
            "Step 1 failed: the live page background was not scrollable enough to "
            "verify Arrow Down scroll prevention.\n"
            f"Observed scroll metrics: {json.dumps(_background_scroll_payload(initial_scroll), indent=2)}",
        )

    target_scroll_y = min(
        max(MIN_SCROLL_TARGET_Y, initial_scroll.viewport_height * 0.6),
        initial_scroll.max_scroll_y,
    )
    scrolled = page.scroll_background_to(y=target_scroll_y)
    result["scrolled_background"] = _background_scroll_payload(scrolled)
    if scrolled.scroll_y <= SCROLL_TOLERANCE_PX:
        raise AssertionError(
            "Step 1 failed: the background page did not reach a non-zero vertical "
            "scroll position before opening the workspace switcher.\n"
            f"Observed scroll metrics: {json.dumps(_background_scroll_payload(scrolled), indent=2)}",
        )

    switcher = page.open_and_observe()
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
    )
    saved_workspace_rows = page.observe_saved_workspace_rows()
    _assert_desktop_panel_open(
        switcher=switcher,
        panel=panel,
    )
    active_workspace = _assert_saved_workspace_navigation_ready(saved_workspace_rows)
    page.click_saved_workspace_row_surface(ACTIVE_WORKSPACE_DISPLAY_NAME)
    baseline_scroll = page.observe_background_scroll()

    result["switcher_text_before_arrow"] = switcher.switcher_text
    result["open_switcher_observation"] = _switcher_payload(switcher)
    result["open_panel_observation"] = asdict(panel)
    result["saved_workspace_rows_before_arrow"] = _saved_workspace_rows_payload(
        saved_workspace_rows,
    )
    result["active_workspace_before_arrow"] = active_workspace.display_name
    result["scroll_before_arrow"] = _background_scroll_payload(baseline_scroll)
    return baseline_scroll


def _press_arrow_down_and_observe(
    *,
    page: LiveWorkspaceSwitcherPage,
    before_scroll: BackgroundScrollObservation,
) -> dict[str, object]:
    page.start_transition_monitor()
    page.press_key("ArrowDown")
    switcher = page.observe_open_switcher(timeout_ms=4_000)
    panel = page.observe_open_panel(
        expected_container_kinds=("anchored-panel", "surface"),
        timeout_ms=4_000,
    )
    saved_workspace_rows = page.observe_saved_workspace_rows(timeout_ms=4_000)
    monitor = page.read_transition_monitor(clear=True)
    active_workspace = _selected_saved_workspace(saved_workspace_rows)
    after_scroll = page.observe_background_scroll()
    return {
        "key": "ArrowDown",
        "switcher": _switcher_payload(switcher),
        "panel": asdict(panel),
        "saved_workspace_rows": _saved_workspace_rows_payload(saved_workspace_rows),
        "active_workspace_name": (
            active_workspace.display_name if active_workspace is not None else None
        ),
        "before_scroll": _background_scroll_payload(before_scroll),
        "after_scroll": _background_scroll_payload(after_scroll),
        "scroll_delta": after_scroll.scroll_y - before_scroll.scroll_y,
        "monitor": _monitor_payload(monitor),
    }


def _assert_desktop_panel_open(
    *,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
) -> None:
    if "Workspace switcher" not in switcher.switcher_text:
        raise AssertionError(
            "Step 1 failed: opening the workspace switcher did not expose the visible "
            "Workspace switcher title.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 1 failed: opening the workspace switcher did not expose the expected "
            "desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )


def _assert_saved_workspace_navigation_ready(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation:
    if len(rows) < 2:
        raise AssertionError(
            "Step 1 failed: the open workspace switcher did not expose at least two "
            "saved workspace rows needed to exercise Arrow Down navigation.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    active_workspace = _selected_saved_workspace(rows)
    if active_workspace is None:
        raise AssertionError(
            "Step 1 failed: none of the visible saved workspace rows was marked "
            "active before pressing Arrow Down.\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    if active_workspace.display_name != ACTIVE_WORKSPACE_DISPLAY_NAME:
        raise AssertionError(
            "Step 1 failed: the preloaded active saved workspace was not the expected "
            "Arrow Down starting point.\n"
            f"Observed active workspace: {active_workspace.display_name!r}\n"
            f"Observed rows: {json.dumps(_saved_workspace_rows_payload(rows), indent=2)}",
        )
    return active_workspace


def _assert_arrow_down_navigated_without_background_scroll(
    *,
    observation: dict[str, object],
    before_active_workspace: str,
    expected_active_workspace: str,
    expected_scroll_y: float,
) -> None:
    switcher = observation["switcher"]
    panel = observation["panel"]
    monitor = observation["monitor"]
    saved_workspace_rows = observation["saved_workspace_rows"]
    active_workspace_name = observation["active_workspace_name"]
    before_scroll = observation["before_scroll"]
    after_scroll = observation["after_scroll"]
    scroll_delta = float(observation["scroll_delta"])
    assert isinstance(switcher, dict)
    assert isinstance(panel, dict)
    assert isinstance(monitor, dict)
    assert isinstance(saved_workspace_rows, list)
    assert isinstance(before_scroll, dict)
    assert isinstance(after_scroll, dict)

    failures: list[str] = []
    if "Workspace switcher" not in str(switcher.get("switcher_text", "")):
        failures.append("the visible Workspace switcher title was not present after Arrow Down")
    if str(panel.get("container_kind")) not in {"anchored-panel", "surface"}:
        failures.append(
            f"the visible container kind became {panel.get('container_kind')!r}",
        )
    if bool(monitor.get("ever_hidden_after_visible")):
        failures.append(
            "the transition monitor observed the panel become hidden after Arrow Down",
        )
    if len(saved_workspace_rows) < 2:
        failures.append("fewer than two saved workspace rows remained visible after Arrow Down")
    if active_workspace_name == before_active_workspace:
        failures.append(
            f"the active saved workspace stayed on {before_active_workspace!r} instead of moving",
        )
    if active_workspace_name != expected_active_workspace:
        failures.append(
            f"the active saved workspace became {active_workspace_name!r} instead of "
            f"{expected_active_workspace!r}",
        )
    after_scroll_y = float(after_scroll.get("scroll_y", 0.0))
    if abs(after_scroll_y - expected_scroll_y) > SCROLL_TOLERANCE_PX:
        failures.append(
            f"the background page scroll moved from {expected_scroll_y:.1f}px to "
            f"{after_scroll_y:.1f}px (delta {scroll_delta:.1f}px)",
        )

    if failures:
        raise AssertionError(
            "Step 2 failed: pressing Arrow Down did not deliver the expected in-panel "
            "workspace navigation outcome on the scrollable background surface.\n"
            f"Active workspace before Arrow Down: {before_active_workspace!r}\n"
            f"Active workspace after Arrow Down: {active_workspace_name!r}\n"
            f"Background scroll before Arrow Down: {before_scroll.get('scroll_y')!r}\n"
            f"Background scroll after Arrow Down: {after_scroll.get('scroll_y')!r}\n"
            f"Observed saved rows: {json.dumps(saved_workspace_rows, indent=2)}\n"
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
    error = str(result.get("error", "AssertionError: TS-834 failed"))
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
        "h4. Preconditions checked",
        *[f"* {item}" for item in PRECONDITIONS],
        "",
        "h4. What was tested",
        "* Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved hosted workspaces.",
        "* Resized the browser to a desktop viewport and scrolled the live Settings background surface to a non-zero position.",
        "* Opened the workspace switcher from Settings and started Arrow Down from the visible saved-workspace surface.",
        "* Verified the active saved workspace changed to the next row while the background page scroll position remained unchanged.",
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failed_step_summary(result)}"
        ),
        f"* Expected result: {EXPECTED_RESULT}",
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
        "## Preconditions checked",
        *[f"- {item}" for item in PRECONDITIONS],
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored hosted token and two preloaded saved hosted workspaces.",
        "- Resized to a desktop viewport where the Settings background surface is scrollable and moved it to a non-zero scroll position.",
        "- Opened the workspace switcher from Settings and started Arrow Down from the visible saved-workspace surface.",
        "- Verified that Arrow Down changed the active saved workspace and did not change the background page scroll position.",
        "",
        "## Result",
        (
            "- Matched the expected result."
            if passed
            else f"- Did not match the expected result. {_failed_step_summary(result)}"
        ),
        f"- Expected result: {EXPECTED_RESULT}",
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
        "- Added TS-834 live desktop coverage for Arrow Down in the workspace switcher.",
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
            else "- Outcome: Arrow Down moved the active saved workspace from Hosted main workspace to Hosted alt workspace while the background page stayed at the same scroll position."
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
            f"# {TICKET_KEY} - Arrow Down in workspace switcher does not advance selection on the scrollable Settings surface",
            "",
            "## Steps to reproduce",
            *[f"{index}. {step}" for index, step in enumerate(REQUEST_STEPS, start=1)],
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
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
            "## Missing or broken production capability",
            (
                f"- {result.get('product_gap')}"
                if result.get("product_gap")
                else "- The desktop workspace switcher does not keep Arrow Down fully scoped to in-panel navigation."
            ),
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
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return "<no observation recorded>"
    for step in steps:
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "<no observation recorded>"))
    return "<no observation recorded>"


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


def _selected_saved_workspace(
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
) -> WorkspaceSwitcherSavedWorkspaceRowObservation | None:
    for row in rows:
        if row.selected:
            return row
    return None


def _trigger_payload(trigger: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": trigger.semantic_label,
        "visible_text": trigger.visible_text,
        "display_name": trigger.display_name,
        "workspace_type": trigger.workspace_type,
        "state_label": trigger.state_label,
        "top_button_labels": list(trigger.top_button_labels),
        "bounds": {
            "left": trigger.left,
            "top": trigger.top,
            "width": trigger.width,
            "height": trigger.height,
        },
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


def _background_scroll_payload(observation: BackgroundScrollObservation) -> dict[str, float]:
    return {
        "scroll_y": observation.scroll_y,
        "viewport_height": observation.viewport_height,
        "scroll_height": observation.scroll_height,
        "max_scroll_y": observation.max_scroll_y,
    }


def _monitor_payload(
    observation: WorkspaceSwitcherTransitionMonitorObservation,
) -> dict[str, object]:
    return {
        "sample_count": observation.sample_count,
        "visible_sample_count": observation.visible_sample_count,
        "hidden_sample_count": observation.hidden_sample_count,
        "ever_hidden_after_visible": observation.ever_hidden_after_visible,
        "observed_container_kinds": list(observation.observed_container_kinds),
        "observed_row_counts": list(observation.observed_row_counts),
        "observed_active_workspace_names": list(
            observation.observed_active_workspace_names,
        ),
        "latest_visible_container_kind": observation.latest_visible_container_kind,
        "latest_visible_row_count": observation.latest_visible_row_count,
        "latest_visible_active_workspace_name": (
            observation.latest_visible_active_workspace_name
        ),
    }


def _snippet(text: str, *, length: int = 220) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= length:
        return normalized
    return normalized[: length - 3] + "..."


if __name__ == "__main__":
    main()
