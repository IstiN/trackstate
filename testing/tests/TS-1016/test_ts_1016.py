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
    WorkspaceSwitcherDisabledOutsideTargetObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherOutsideDismissObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.core.interfaces.web_app_session import ElementBoundingBox  # noqa: E402
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    build_annotated_steps,
    format_human_lines,
    format_step_lines,
    record_human_verification,
    record_not_reached_steps,
    record_step,
    snippet,
    write_test_automation_result,
)
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-1016"
TEST_CASE_TITLE = (
    "Click on a disabled element outside the workspace switcher — panel closes"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1016/test_ts_1016.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
DEFAULT_BRANCH = "main"
FIRST_WORKSPACE_DISPLAY_NAME = "Hosted main workspace"
SECOND_WORKSPACE_DISPLAY_NAME = "Hosted alt workspace"
THIRD_WORKSPACE_DISPLAY_NAME = "Hosted third workspace"
SECOND_WORKSPACE_WRITE_BRANCH = "ts-1016-alt"
THIRD_WORKSPACE_WRITE_BRANCH = "ts-1016-third"
SURFACE_TIMEOUT_MS = 4_000
DISMISS_TIMEOUT_MS = 4_000
PANEL_RECHECK_TIMEOUT_MS = 1_200
LINKED_BUGS = ["TS-1010"]

PRECONDITIONS = [
    "The workspace switcher is open.",
    "There is a disabled interactive element visible in the application background (outside the switcher's DOM tree).",
]
REQUEST_STEPS = [
    "Click on a disabled button or interactive element located outside the workspace switcher container.",
]
AUTOMATION_STEPS = [
    "Launch the deployed desktop app and open the workspace switcher in a pristine state.",
    "Verify a visible disabled interactive element exists outside the switcher container in the application background.",
    "Click that disabled background control with a real pointer action.",
    "Verify the workspace switcher closes and the dashboard shell remains visible to the user.",
]
EXPECTED_RESULT = (
    "The workspace switcher panel closes immediately. The focus-management "
    "utility's \"contains\" check must return false for the element under the "
    "pointer, correctly identifying it as an external interaction."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1016_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1016_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1016 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )

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
        "linked_bugs": LINKED_BUGS,
        "preconditions": PRECONDITIONS,
        "request_steps": REQUEST_STEPS,
        "automation_steps": AUTOMATION_STEPS,
        "surface_timeout_ms": SURFACE_TIMEOUT_MS,
        "dismiss_timeout_ms": DISMISS_TIMEOUT_MS,
        "panel_recheck_timeout_ms": PANEL_RECHECK_TIMEOUT_MS,
        "preloaded_workspace_state": workspace_state,
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
                trigger_before = None
                panel_before = None
                switcher_before = None
                target = None

                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the disabled-outside-click scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )
                    page.dismiss_connection_banner()
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    page.navigate_to_section("Dashboard")
                    trigger_before = page.observe_trigger()
                    page.open_switcher()
                    panel_before = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    switcher_before = page.observe_open_switcher(
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    result["trigger_before_click"] = _trigger_payload(trigger_before)
                    result["panel_before_click"] = asdict(panel_before)
                    result["switcher_before_click"] = _switcher_payload(switcher_before)
                    _assert_switcher_open_state(
                        panel=panel_before,
                        switcher=switcher_before,
                    )
                except Exception as error:
                    record_step(
                        result,
                        step=1,
                        status="failed",
                        action=AUTOMATION_STEPS[0],
                        observed=str(error),
                    )
                    raise
                record_step(
                    result,
                    step=1,
                    status="passed",
                    action=AUTOMATION_STEPS[0],
                    observed=(
                        f"Opened {config.app_url} in Chromium at "
                        f"{DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}; "
                        f"trigger_label={trigger_before.semantic_label!r}; "
                        f"panel_kind={panel_before.container_kind!r}; "
                        f"row_count={switcher_before.row_count}."
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Opened the live desktop switcher and visually confirmed the "
                        "workspace-switcher panel was layered above the Dashboard shell."
                    ),
                    observed=(
                        f"title_visible={'Workspace switcher' in switcher_before.switcher_text}; "
                        f"dashboard_visible={'Dashboard' in page.current_body_text()}; "
                        f"switcher_excerpt={snippet(switcher_before.switcher_text)!r}"
                    ),
                )

                try:
                    target = page.observe_disabled_interactive_outside_panel(
                        panel=panel_before,
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    result["disabled_outside_target"] = _outside_target_payload(target)
                    _assert_disabled_external_target(target)
                except Exception as error:
                    record_step(
                        result,
                        step=2,
                        status="failed",
                        action=AUTOMATION_STEPS[1],
                        observed=str(error),
                    )
                    raise
                record_step(
                    result,
                    step=2,
                    status="passed",
                    action=AUTOMATION_STEPS[1],
                    observed=(
                        f"target_tag={target.target_tag_name!r}; "
                        f"target_disabled={target.target_disabled}; "
                        f"aria_disabled={target.target_aria_disabled!r}; "
                        f"within_switcher_dom={target.target_within_switcher_dom}; "
                        f"point_target_within_switcher_dom={target.point_target_within_switcher_dom}; "
                        f"context={target.context_text!r}."
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Verified the background control itself before clicking and "
                        "confirmed it was outside the open panel rather than part of the switcher."
                    ),
                    observed=(
                        f"target_tag={target.target_tag_name!r}; "
                        f"point_target_tag={target.point_target_tag_name!r}; "
                        f"context={target.context_text!r}; "
                        f"target_html={_compact_html(target.target_outer_html)!r}"
                    ),
                )

                try:
                    clicked_target = page.click_disabled_interactive_outside_panel(
                        panel=panel_before,
                        observation=target,
                        timeout_ms=SURFACE_TIMEOUT_MS,
                    )
                    result["clicked_target"] = _outside_target_payload(clicked_target)
                except Exception as error:
                    record_step(
                        result,
                        step=3,
                        status="failed",
                        action=AUTOMATION_STEPS[2],
                        observed=str(error),
                    )
                    raise
                record_step(
                    result,
                    step=3,
                    status="passed",
                    action=AUTOMATION_STEPS[2],
                    observed=(
                        f"clicked_point=({clicked_target.click_x:.1f}, {clicked_target.click_y:.1f}); "
                        f"point_target_tag={clicked_target.point_target_tag_name!r}; "
                        f"point_target_text={clicked_target.point_target_text!r}."
                    ),
                )

                dismissal = None
                trigger_after = None
                try:
                    dismissal = page.wait_for_dismissal_after_outside_click(
                        click_target=_click_target_box(clicked_target),
                        timeout_ms=DISMISS_TIMEOUT_MS,
                    )
                    trigger_after = page.observe_trigger()
                    result["dismissal_observation"] = _dismissal_payload(dismissal)
                    result["trigger_after_click"] = _trigger_payload(trigger_after)
                    _assert_switcher_closed_after_click(
                        page=page,
                        dismissal=dismissal,
                        trigger_after=trigger_after,
                    )
                except Exception as error:
                    record_step(
                        result,
                        step=4,
                        status="failed",
                        action=AUTOMATION_STEPS[3],
                        observed=str(error),
                    )
                    raise
                record_step(
                    result,
                    step=4,
                    status="passed",
                    action=AUTOMATION_STEPS[3],
                    observed=(
                        f"dashboard_visible={dismissal.dashboard_visible}; "
                        f"trigger_visible_probe={dismissal.trigger_visible}; "
                        f"trigger_after_label={trigger_after.semantic_label!r}; "
                        f"body_text_contains_save_and_switch={'Save and switch' in dismissal.body_text}."
                    ),
                )
                record_human_verification(
                    result,
                    check=(
                        "Clicked the disabled background control like a user and watched "
                        "the workspace switcher disappear while the Dashboard shell stayed visible."
                    ),
                    observed=(
                        f"dashboard_visible={dismissal.dashboard_visible}; "
                        f"trigger_after={trigger_after.visible_text!r}; "
                        f"body_excerpt={snippet(dismissal.body_text)!r}"
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
                _record_not_reached_steps_if_needed(result)
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


def _assert_switcher_open_state(
    *,
    panel: WorkspaceSwitcherPanelObservation,
    switcher: WorkspaceSwitcherObservation,
) -> None:
    failures: list[str] = []
    if panel.container_kind not in {"anchored-panel", "surface"}:
        failures.append(
            f"container_kind was {panel.container_kind!r} instead of an anchored desktop panel",
        )
    if panel.background_dimmed:
        failures.append("the workspace switcher dimmed the background like a modal")
    if switcher.row_count <= 0:
        failures.append("no visible saved workspace rows were rendered")
    if "Workspace switcher" not in switcher.switcher_text:
        failures.append('the visible "Workspace switcher" heading was missing')
    if failures:
        raise AssertionError(
            "Step 1 failed: the live app did not expose the expected pristine desktop "
            "workspace switcher surface.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed panel: {json.dumps(asdict(panel), indent=2)}\n"
            + f"Observed switcher text:\n{switcher.switcher_text}"
        )


def _assert_disabled_external_target(
    observation: WorkspaceSwitcherDisabledOutsideTargetObservation,
) -> None:
    failures: list[str] = []
    if observation.click_x <= 0 or observation.click_y <= 0:
        failures.append("the pointer target resolved to invalid coordinates")
    if not observation.target_disabled and observation.target_aria_disabled != "true":
        failures.append("the resolved background control did not report a disabled state")
    if observation.target_within_switcher_dom:
        failures.append("the disabled target was still inside the switcher DOM tree")
    if observation.point_target_within_switcher_dom:
        failures.append("document.elementFromPoint resolved to a switcher-owned element")
    if observation.target_within_panel_bounds:
        failures.append("the disabled target coordinates were still inside the panel bounds")
    if observation.point_target_within_panel_bounds:
        failures.append("the element under the pointer still fell inside the panel bounds")
    if failures:
        raise AssertionError(
            "Step 2 failed: the live page did not expose a disabled external interaction "
            "target outside the workspace switcher.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed target: {json.dumps(_outside_target_payload(observation), indent=2)}"
        )


def _assert_switcher_closed_after_click(
    *,
    page: LiveWorkspaceSwitcherPage,
    dismissal: WorkspaceSwitcherOutsideDismissObservation,
    trigger_after: WorkspaceSwitcherTriggerObservation,
) -> None:
    failures: list[str] = []
    if not dismissal.dashboard_visible:
        failures.append("the dashboard shell was not visible after the click")
    if "Save and switch" in dismissal.body_text:
        failures.append("the dismissed page still showed the switcher footer text")
    if "Saved workspaces" in dismissal.body_text:
        failures.append("the dismissed page still showed the saved-workspaces panel text")
    if "Branch:" in dismissal.body_text and "Delete" in dismissal.body_text:
        failures.append("the dismissed page still showed saved-workspace row content")
    if not trigger_after.semantic_label.startswith("Workspace switcher:"):
        failures.append(
            f"the workspace trigger did not return with the expected label: {trigger_after.semantic_label!r}",
        )
    if failures:
        raise AssertionError(
            "Step 4 failed: clicking the disabled element outside the workspace "
            "switcher did not dismiss the panel as expected.\n"
            + "\n".join(f"- {failure}" for failure in failures)
            + "\n"
            + f"Observed dismissal: {json.dumps(_dismissal_payload(dismissal), indent=2)}\n"
            + f"Observed trigger after click: {json.dumps(_trigger_payload(trigger_after), indent=2)}\n"
            + f"Observed body text after click:\n{dismissal.body_text}"
        )


def _workspace_state(repository: str) -> dict[str, object]:
    first_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}"
    second_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{SECOND_WORKSPACE_WRITE_BRANCH}"
    third_id = f"hosted:{repository.lower()}@{DEFAULT_BRANCH}:{THIRD_WORKSPACE_WRITE_BRANCH}"
    return {
        "activeWorkspaceId": first_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": first_id,
                "displayName": FIRST_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": FIRST_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": DEFAULT_BRANCH,
                "lastOpenedAt": "2026-05-23T00:00:00.000Z",
            },
            {
                "id": second_id,
                "displayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": SECOND_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": SECOND_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-22T23:50:00.000Z",
            },
            {
                "id": third_id,
                "displayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "customDisplayName": THIRD_WORKSPACE_DISPLAY_NAME,
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": DEFAULT_BRANCH,
                "writeBranch": THIRD_WORKSPACE_WRITE_BRANCH,
                "lastOpenedAt": "2026-05-22T23:40:00.000Z",
            },
        ],
    }


def _switcher_payload(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": observation.row_count,
        "switcher_text": observation.switcher_text,
        "rows": [asdict(row) for row in observation.rows],
    }


def _outside_target_payload(
    observation: WorkspaceSwitcherDisabledOutsideTargetObservation,
) -> dict[str, object]:
    return {
        "click_x": observation.click_x,
        "click_y": observation.click_y,
        "target_tag_name": observation.target_tag_name,
        "target_role": observation.target_role,
        "target_label": observation.target_label,
        "target_text": observation.target_text,
        "target_outer_html": observation.target_outer_html,
        "target_disabled": observation.target_disabled,
        "target_aria_disabled": observation.target_aria_disabled,
        "target_pointer_events": observation.target_pointer_events,
        "target_within_switcher_dom": observation.target_within_switcher_dom,
        "target_within_panel_bounds": observation.target_within_panel_bounds,
        "point_target_tag_name": observation.point_target_tag_name,
        "point_target_role": observation.point_target_role,
        "point_target_label": observation.point_target_label,
        "point_target_text": observation.point_target_text,
        "point_target_outer_html": observation.point_target_outer_html,
        "point_target_within_switcher_dom": observation.point_target_within_switcher_dom,
        "point_target_within_panel_bounds": observation.point_target_within_panel_bounds,
        "context_text": observation.context_text,
    }


def _dismissal_payload(observation: WorkspaceSwitcherOutsideDismissObservation) -> dict[str, object]:
    return {
        "click_x": observation.click_x,
        "click_y": observation.click_y,
        "body_text": observation.body_text,
        "dashboard_visible": observation.dashboard_visible,
        "trigger_visible": observation.trigger_visible,
    }


def _trigger_payload(observation: WorkspaceSwitcherTriggerObservation) -> dict[str, object]:
    return {
        "semantic_label": observation.semantic_label,
        "visible_text": observation.visible_text,
        "display_name": observation.display_name,
        "workspace_type": observation.workspace_type,
        "state_label": observation.state_label,
        "top_button_labels": list(observation.top_button_labels),
    }


def _click_target_box(
    observation: WorkspaceSwitcherDisabledOutsideTargetObservation,
) -> ElementBoundingBox:
    return ElementBoundingBox(
        x=observation.click_x,
        y=observation.click_y,
        width=0.0,
        height=0.0,
    )


def _compact_html(value: str, *, limit: int = 280) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


def _record_not_reached_steps_if_needed(result: dict[str, object]) -> None:
    recorded_steps = [
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    ]
    if not recorded_steps:
        return
    highest_step = max(recorded_steps)
    if highest_step < len(AUTOMATION_STEPS):
        record_not_reached_steps(
            result,
            starting_step=highest_step + 1,
            request_steps=AUTOMATION_STEPS,
        )


def _write_pass_outputs(result: dict[str, object]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-1016 failed"))
    write_test_automation_result(RESULT_PATH, passed=False, error=error)
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    if _is_product_failure(result):
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _is_product_failure(result: dict[str, object]) -> bool:
    error = str(result.get("error", ""))
    if not error:
        return False
    infrastructure_prefixes = (
        "RuntimeError:",
        "ModuleNotFoundError:",
        "ImportError:",
        "SyntaxError:",
    )
    return not error.startswith(infrastructure_prefixes)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Ticket:* {TICKET_KEY}",
        f"*Status:* {status}",
        f"*Test case:* {TEST_CASE_TITLE}",
        f"*Environment:* {{code}}{_environment_summary(result)}{{code}}",
        f"*Linked bugs covered:* {', '.join(result.get('linked_bugs', []))}",
        "",
        "h4. Automated checks",
        *format_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *format_human_lines(result, jira=True),
        "",
        "h4. Observed result",
        f"{{code}}{_result_summary(result, passed=passed)}{{code}}",
    ]
    screenshot = result.get("screenshot")
    if screenshot:
        lines.extend(["", f"*Screenshot:* {{code}}{screenshot}{{code}}"])
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        f"## {status} {TICKET_KEY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        "",
        f"**Environment:** `{_environment_summary(result)}`",
        "",
        "### Automated checks",
        *format_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *format_human_lines(result, jira=False),
        "",
        "### Observed result",
        _result_summary(result, passed=passed),
    ]
    screenshot = result.get("screenshot")
    if screenshot:
        lines.extend(["", f"**Screenshot:** `{screenshot}`"])
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    return (
        f"# {TICKET_KEY} {status}\n\n"
        f"{_result_summary(result, passed=passed)}\n\n"
        f"Environment: `{_environment_summary(result)}`\n"
    )


def _result_summary(result: dict[str, object], *, passed: bool) -> str:
    if passed:
        target = result.get("disabled_outside_target", {})
        dismissal = result.get("dismissal_observation", {})
        return (
            "Clicked a real disabled background control outside the open workspace "
            "switcher and the live panel closed as expected: the external pointer target "
            "was outside the switcher DOM/container, the Dashboard remained visible, and "
            "the dismissed page no longer showed the switcher footer or saved-workspaces "
            f"content. Observed target context={target.get('context_text')!r}; "
            f"trigger_visible_probe={dismissal.get('trigger_visible')!r}."
        )
    return str(result.get("error", "TS-1016 failed."))


def _environment_summary(result: dict[str, object]) -> str:
    viewport = result.get("desktop_viewport", {})
    width = viewport.get("width")
    height = viewport.get("height")
    return (
        f"URL={result.get('app_url')} | browser={result.get('browser')} | "
        f"OS={result.get('os')} | viewport={width}x{height} | "
        f"repo={result.get('repository')}@{result.get('repository_ref')}"
    )


def _bug_description(result: dict[str, object]) -> str:
    annotated_steps = build_annotated_steps(
        {
            "steps": [
                {
                    "step": 1,
                    "status": "failed",
                    "action": REQUEST_STEPS[0],
                    "observed": str(result.get("error", "")),
                },
            ],
        },
        request_steps=REQUEST_STEPS,
    )
    screenshot = result.get("screenshot", "No screenshot captured.")
    return "\n".join(
        [
            f"# {TICKET_KEY}: Clicking a disabled external control does not dismiss the workspace switcher",
            "",
            "## Preconditions",
            *[f"- {item}" for item in PRECONDITIONS],
            "",
            "## Steps to reproduce",
            *annotated_steps,
            "",
            "## Exact error message / assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual result",
            _actual_failure_details(result),
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Environment",
            f"- {_environment_summary(result)}",
            "",
            "## Evidence",
            f"- Screenshot: {screenshot}",
            f"- Disabled outside target: {json.dumps(result.get('disabled_outside_target', {}), indent=2)}",
            f"- Clicked target: {json.dumps(result.get('clicked_target', {}), indent=2)}",
            f"- Dismissal observation: {json.dumps(result.get('dismissal_observation', {}), indent=2)}",
            f"- Trigger after click: {json.dumps(result.get('trigger_after_click', {}), indent=2)}",
        ],
    ) + "\n"


def _actual_failure_details(result: dict[str, object]) -> str:
    return (
        "After clicking a disabled interactive control outside the open workspace "
        "switcher in the live deployed app, the visible outcome did not match the "
        "expected external-interaction dismissal behavior. "
        + str(result.get("error", ""))
        + "\n\nObserved disabled target:\n"
        + json.dumps(result.get("disabled_outside_target", {}), indent=2)
        + "\n\nObserved dismissal state:\n"
        + json.dumps(result.get("dismissal_observation", {}), indent=2)
    )


if __name__ == "__main__":
    main()
