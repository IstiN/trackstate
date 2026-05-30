from __future__ import annotations

from dataclasses import asdict
import json
import platform
import re
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_workspace_switcher_page import (  # noqa: E402
    BackgroundScrollObservation,
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherFocusTargetObservation,
    WorkspaceSwitcherInternalFocusObservation,
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
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts834_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts834_failure.png"

REVIEW_THREAD_REPLIES: tuple[dict[str, object], ...] = ()


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
                page.open_settings()
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
                        f"active_workspace={result['active_workspace_before_arrow']!r}; "
                        f"focus_before_arrow={result['focus_before_arrow']['active_label']!r}; "
                        "focus_owned_by_switcher="
                        f"{result['focus_before_arrow']['focus_owned_by_switcher']}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live desktop page in a visibly scrolled state and "
                        "confirmed the workspace switcher stayed open on top of the "
                        "Settings content with keyboard focus on a real in-panel button "
                        "before pressing Arrow Down."
                    ),
                    observed=(
                        f"scroll_before_arrow={baseline_scroll.scroll_y:.1f}px; "
                        f"focus_before_arrow={result['focus_before_arrow']['active_label']!r}; "
                        f"title='Workspace switcher'; "
                        f"text_excerpt={_snippet(str(result.get('switcher_text_before_arrow', '')))}"
                    ),
                )

                arrow_down = _press_arrow_down_and_observe(
                    page=page,
                    panel=WorkspaceSwitcherPanelObservation(
                        **result["open_panel_observation"],  # type: ignore[arg-type]
                    ),
                    before_scroll=baseline_scroll,
                )
                result["arrow_down_observation"] = arrow_down
                _record_human_verification(
                    result,
                    check=(
                        "Pressed Arrow Down from the verified switcher-owned in-panel "
                        "button and watched for both the active-row change and any jump "
                        "in the background page position."
                    ),
                    observed=(
                        f"focus_before_arrow={arrow_down['before_key_focus']['active_label']!r}; "
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
                    result["product_gap"] = _product_gap_summary(result)
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
    focus_before_arrow = _focus_saved_workspace_action_button(
        page=page,
        panel=panel,
        active_workspace=active_workspace,
        rows=saved_workspace_rows,
    )
    baseline_scroll = page.observe_background_scroll()

    result["switcher_text_before_arrow"] = switcher.switcher_text
    result["open_switcher_observation"] = _switcher_payload(switcher)
    result["open_panel_observation"] = asdict(panel)
    result["saved_workspace_rows_before_arrow"] = _saved_workspace_rows_payload(
        saved_workspace_rows,
    )
    result["active_workspace_before_arrow"] = active_workspace.display_name
    result["focus_before_arrow"] = focus_before_arrow
    result["scroll_before_arrow"] = _background_scroll_payload(baseline_scroll)
    return baseline_scroll


def _focus_saved_workspace_action_button(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    active_workspace: WorkspaceSwitcherSavedWorkspaceRowObservation,
    rows: tuple[WorkspaceSwitcherSavedWorkspaceRowObservation, ...],
    max_tabs: int = 12,
) -> dict[str, object]:
    preferred_labels: list[str] = ["Save and switch"]
    preferred_labels.extend(
        label for label in active_workspace.action_labels if label != "Active"
    )
    for row in rows:
        preferred_labels.extend(
            label
            for label in row.action_labels
            if label != "Active" and label not in preferred_labels
        )
    for label in preferred_labels:
        try:
            observation = page.focus_switcher_button(
                label,
                panel=panel,
                timeout_ms=2_000,
            )
        except AssertionError:
            continue
        payload = _switcher_focus_payload(observation)
        payload["focus_strategy"] = "direct-button-focus"
        payload["target_button_label"] = label
        return payload

    page.focus_workspace_trigger(panel=panel)
    focus_steps: list[dict[str, object]] = []
    for tab_index in range(1, max_tabs + 1):
        observation = page.observe_internal_focus_after_tab(panel=panel)
        payload = _internal_focus_payload(observation, tab_index=tab_index)
        focus_steps.append(payload)
        active_label = str(payload.get("active_label") or "")
        if (
            bool(payload.get("focus_owned_by_switcher"))
            and bool(payload.get("active_within_switcher"))
            and not bool(payload.get("active_on_trigger"))
            and payload.get("active_role") == "button"
        ):
            payload["focus_steps"] = focus_steps
            payload["focus_strategy"] = "tab-navigation"
            return payload
    raise AssertionError(
        "Step 1 failed: keyboard Tab navigation did not reach any in-panel button "
        "before Arrow Down.\n"
        f"Observed focus steps: {json.dumps(focus_steps, indent=2)}",
    )


def _press_arrow_down_and_observe(
    *,
    page: LiveWorkspaceSwitcherPage,
    panel: WorkspaceSwitcherPanelObservation,
    before_scroll: BackgroundScrollObservation,
) -> dict[str, object]:
    before_key_focus = page.observe_switcher_focus_target(panel=panel)
    page.start_transition_monitor()
    page.press_key("ArrowDown")
    page.wait_for_surface_to_remain_open(
        stability_ms=KEY_STABILITY_MS,
        timeout_ms=4_000,
    )
    active_workspace_wait_error: str | None = None
    try:
        page.wait_for_active_saved_workspace(
            SECONDARY_WORKSPACE_DISPLAY_NAME,
            timeout_ms=10_000,
        )
    except AssertionError as error:
        active_workspace_wait_error = str(error)
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
        "before_key_focus": _switcher_focus_payload(before_key_focus),
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
        "active_workspace_wait_error": active_workspace_wait_error,
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
    before_key_focus = observation["before_key_focus"]
    before_scroll = observation["before_scroll"]
    after_scroll = observation["after_scroll"]
    scroll_delta = float(observation["scroll_delta"])
    active_workspace_wait_error = observation.get("active_workspace_wait_error")
    assert isinstance(switcher, dict)
    assert isinstance(panel, dict)
    assert isinstance(monitor, dict)
    assert isinstance(saved_workspace_rows, list)
    assert isinstance(before_key_focus, dict)
    assert isinstance(before_scroll, dict)
    assert isinstance(after_scroll, dict)

    failures: list[str] = []
    if not bool(before_key_focus.get("focus_owned_by_switcher")):
        failures.append("keyboard focus was not owned by the open workspace switcher before Arrow Down")
    if not bool(before_key_focus.get("active_within_switcher")):
        failures.append("keyboard focus was not inside the visible switcher panel before Arrow Down")
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
    if active_workspace_wait_error:
        failures.append(str(active_workspace_wait_error))
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
            f"Focus before Arrow Down: {json.dumps(before_key_focus, indent=2)}\n"
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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(passed=True),
        encoding="utf-8",
    )


def _write_failure_outputs(result: dict[str, object]) -> None:
    raw_error = str(result.get("error", "TS-834 failed"))
    first_line = raw_error.splitlines()[0] if raw_error else ""
    has_error_prefix = bool(
        re.match(r"^[A-Za-z_][A-Za-z0-9_]*(Error|Exception): ", first_line),
    )
    error = raw_error if has_error_prefix else f"AssertionError: {raw_error}"
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
    REVIEW_REPLIES_PATH.write_text(
        _review_replies_payload(passed=False),
        encoding="utf-8",
    )
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
        "* Opened the workspace switcher from Settings, tabbed to a real in-panel button, and asserted switcher-owned keyboard focus before Arrow Down.",
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
        "- Opened the workspace switcher from Settings, tabbed to a real in-panel button, and asserted switcher-owned keyboard focus before Arrow Down.",
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
    status = "passed" if passed else "failed"
    screenshot_path = result.get(
        "screenshot",
        SUCCESS_SCREENSHOT_PATH if passed else FAILURE_SCREENSHOT_PATH,
    )
    failure_summary = _response_failure_summary(result)
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        "## Issues/Notes",
        (
            "- No outstanding harness issues. The verified in-panel keyboard path is in place."
            if passed
            else (
                "- Resolved the merge conflict in "
                "`testing/components/pages/live_workspace_switcher_page.py` and kept the "
                "switcher-owned focus helpers used by TS-834.\n"
                f"- Re-run failed: {failure_summary}"
            )
        ),
        "",
        "## Approach",
        "- Exercised the deployed hosted TrackState app in Chromium against the live setup repository.",
        "- Scrolled the Settings background surface to a non-zero position before opening the workspace switcher.",
        "- Tabbed to a real visible in-panel button, asserted switcher-owned focus, then sent `ArrowDown` and compared both selection and background scroll state.",
        "",
        "## Files Modified",
        "- `testing/components/pages/live_workspace_switcher_page.py`",
        "- `testing/tests/TS-834/test_ts_834.py`",
        "",
        "## Test Coverage",
        f"- Test case: `{TICKET_KEY} - {TEST_CASE_TITLE}`",
        f"- Result: `{status}`",
        f"- Command: `{RUN_COMMAND}`",
        f"- Screenshot: `{screenshot_path}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({result['os']}) against `{result['repository']}` @ "
            f"`{result['repository_ref']}`."
        ),
        (
            f"- Outcome: {failure_summary}"
            if not passed
            else "- Outcome: Arrow Down moved the active saved workspace from Hosted main workspace to Hosted alt workspace while the background page stayed at the same scroll position."
        ),
        f"- Step results: {', '.join(_step_status_summary(result))}",
    ]
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
            f"# {_bug_title(result)}",
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
            "",
            "## Failing command",
            "```bash",
            RUN_COMMAND,
            "```",
            "",
            "## Failing command output",
            "```text",
            str(result.get("traceback", result.get("error", "<missing error>"))),
            "```",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
        ],
    ) + "\n"


def _review_replies_payload(*, passed: bool) -> str:
    status_reply = (
        "Re-run passed with the verified in-panel keyboard path."
        if passed
        else "Re-run still fails with the verified in-panel keyboard path, so the remaining failure is a product bug rather than a focus-harness issue."
    )
    replies = [
        {
            **item,
            "reply": f"{item['reply']} {status_reply}",
        }
        for item in REVIEW_THREAD_REPLIES
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


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


def _step_status_summary(result: dict[str, object]) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return ["no step data recorded"]
    summary: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        status = "passed" if step.get("status") == "passed" else "failed"
        summary.append(f"Step {step.get('step')}: {status}")
    return summary or ["no step data recorded"]


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


def _response_failure_summary(result: dict[str, object]) -> str:
    analysis = _arrow_down_failure_analysis(result)
    focus_label = analysis["focus_label"]
    focus_owned = analysis["focus_owned"]
    active_after = analysis["active_after"]
    scroll_before = analysis["scroll_before"]
    scroll_after = analysis["scroll_after"]
    selection_ok = analysis["selection_ok"]
    scroll_ok = analysis["scroll_ok"]
    focus_prefix = (
        f"focus was on {focus_label!r} with switcher-owned focus={focus_owned}; "
    )
    if selection_ok and not scroll_ok:
        return (
            f"{focus_prefix}`ArrowDown` moved the active workspace to "
            f"{active_after!r}, but background scroll jumped from "
            f"{scroll_before!r}px to {scroll_after!r}px."
        )
    if not selection_ok and scroll_ok:
        return (
            f"{focus_prefix}`ArrowDown` kept the active workspace on "
            f"{result.get('active_workspace_before_arrow')!r} instead of "
            f"{SECONDARY_WORKSPACE_DISPLAY_NAME!r}, while background scroll stayed at "
            f"{scroll_after!r}px."
        )
    if not selection_ok and not scroll_ok:
        return (
            f"{focus_prefix}`ArrowDown` left the active workspace on "
            f"{result.get('active_workspace_before_arrow')!r} instead of "
            f"{SECONDARY_WORKSPACE_DISPLAY_NAME!r}, and background scroll jumped from "
            f"{scroll_before!r}px to {scroll_after!r}px."
        )
    arrow_down = result.get("arrow_down_observation")
    if not isinstance(arrow_down, dict):
        return _failed_step_summary(result)
    return (
        f"focus was on {focus_label!r} with switcher-owned focus={focus_owned}; "
        f"`ArrowDown` preserved the expected selection and background scroll state."
    )


def _arrow_down_failure_analysis(result: dict[str, object]) -> dict[str, object]:
    arrow_down = result.get("arrow_down_observation")
    active_after = None
    focus_label = None
    focus_owned = None
    scroll_before = None
    scroll_after = None
    if isinstance(arrow_down, dict):
        active_after = arrow_down.get("active_workspace_name")
        before_focus = arrow_down.get("before_key_focus")
        before_scroll = arrow_down.get("before_scroll")
        after_scroll = arrow_down.get("after_scroll")
        if isinstance(before_focus, dict):
            focus_label = before_focus.get("active_label")
            focus_owned = before_focus.get("focus_owned_by_switcher")
        if isinstance(before_scroll, dict):
            scroll_before = before_scroll.get("scroll_y")
        if isinstance(after_scroll, dict):
            scroll_after = after_scroll.get("scroll_y")
    selection_ok = active_after == SECONDARY_WORKSPACE_DISPLAY_NAME
    scroll_ok = False
    if scroll_before is not None and scroll_after is not None:
        scroll_ok = abs(float(scroll_after) - float(scroll_before)) <= SCROLL_TOLERANCE_PX
    return {
        "active_after": active_after,
        "focus_label": focus_label,
        "focus_owned": focus_owned,
        "scroll_before": scroll_before,
        "scroll_after": scroll_after,
        "selection_ok": selection_ok,
        "scroll_ok": scroll_ok,
    }


def _product_gap_summary(result: dict[str, object]) -> str:
    analysis = _arrow_down_failure_analysis(result)
    before_active = result.get("active_workspace_before_arrow")
    active_after = analysis["active_after"]
    scroll_before = analysis["scroll_before"]
    scroll_after = analysis["scroll_after"]
    selection_ok = analysis["selection_ok"]
    scroll_ok = analysis["scroll_ok"]
    if selection_ok and not scroll_ok:
        return (
            "On the scrollable Settings surface, pressing Arrow Down inside the "
            "desktop workspace switcher advances the active saved workspace from "
            f"{before_active!r} to {active_after!r}, but the background page scroll "
            f"jumps from {scroll_before!r}px to {scroll_after!r}px instead of staying fixed."
        )
    if not selection_ok and scroll_ok:
        return (
            "On the scrollable Settings surface, pressing Arrow Down inside the "
            "desktop workspace switcher leaves the active saved workspace selection "
            "unchanged even when the key is driven from a verified in-panel button "
            f"inside the switcher. The active workspace stays on {before_active!r} "
            f"instead of moving to {SECONDARY_WORKSPACE_DISPLAY_NAME!r}, while the "
            f"background scroll position stays fixed at {scroll_after!r}px."
        )
    if not selection_ok and not scroll_ok:
        return (
            "On the scrollable Settings surface, pressing Arrow Down inside the "
            "desktop workspace switcher does not keep the interaction scoped to the "
            "expected in-panel behavior: the active saved workspace stays on "
            f"{before_active!r} instead of moving to {SECONDARY_WORKSPACE_DISPLAY_NAME!r}, "
            f"and the background page scroll jumps from {scroll_before!r}px to "
            f"{scroll_after!r}px."
        )
    return (
        "The desktop workspace switcher does not keep Arrow Down fully scoped to the "
        "expected in-panel navigation behavior on the scrollable Settings surface."
    )


def _bug_title(result: dict[str, object]) -> str:
    analysis = _arrow_down_failure_analysis(result)
    selection_ok = analysis["selection_ok"]
    scroll_ok = analysis["scroll_ok"]
    if selection_ok and not scroll_ok:
        return (
            f"{TICKET_KEY} - Arrow Down in workspace switcher scrolls the background "
            "Settings surface"
        )
    if not selection_ok and scroll_ok:
        return (
            f"{TICKET_KEY} - Arrow Down in workspace switcher does not advance "
            "selection on the scrollable Settings surface"
        )
    return (
        f"{TICKET_KEY} - Arrow Down in workspace switcher does not keep navigation "
        "scoped to the scrollable Settings surface"
    )


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


def _switcher_focus_payload(
    observation: WorkspaceSwitcherFocusTargetObservation,
) -> dict[str, object]:
    return {
        "active_label": observation.active_label,
        "active_role": observation.active_role,
        "active_tag_name": observation.active_tag_name,
        "active_outer_html": observation.active_outer_html,
        "active_visible": observation.active_visible,
        "active_in_viewport": observation.active_in_viewport,
        "active_within_switcher": observation.active_within_switcher,
        "active_on_trigger": observation.active_on_trigger,
        "focus_owned_by_switcher": observation.focus_owned_by_switcher,
    }


def _internal_focus_payload(
    observation: WorkspaceSwitcherInternalFocusObservation,
    *,
    tab_index: int,
) -> dict[str, object]:
    return {
        "tab_index": tab_index,
        "active_label": observation.after_label,
        "active_role": observation.after_role,
        "active_tag_name": observation.after_tag_name,
        "active_outer_html": observation.after_outer_html,
        "active_visible": observation.after_visible,
        "active_in_viewport": observation.after_in_viewport,
        "active_within_switcher": observation.after_within_switcher,
        "active_on_trigger": observation.after_on_trigger,
        "focus_owned_by_switcher": observation.after_owned_by_switcher,
        "after_different_from_before": observation.after_different_from_before,
    }


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
