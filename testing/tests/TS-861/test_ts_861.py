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
    WorkspaceSwitcherSurfaceObservation,
    WorkspaceSwitcherSurfaceReferenceObservation,
    WorkspaceSwitcherTriggerDismissObservation,
    WorkspaceSwitcherTriggerObservation,
    WorkspaceTriggerAriaControlsObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-861"
TEST_CASE_TITLE = (
    "Repeated workspace switcher toggles - aria-controls to surface ID relationship remains persistent"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-861/test_ts_861.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
TRIGGER_ATTRIBUTE_TIMEOUT_MS = 4_000
SURFACE_TIMEOUT_MS = 6_000
DISMISSAL_TIMEOUT_MS = 4_000
LINKED_BUGS = ["TS-854"]

PRECONDITIONS = [
    "The deployed TrackState app is open in a desktop browser with Dashboard visible.",
    "A hosted GitHub token is available so the live app can render an interactive session.",
]
REQUEST_STEPS = [
    "Open the application and locate the workspace switcher trigger.",
    "Record the initial value of the 'aria-controls' attribute.",
    "Click the trigger to open the workspace switcher surface.",
    "Confirm the surface 'id' matches the 'aria-controls' value.",
    "Click the trigger (or a close button) to hide the surface.",
    "Click the trigger again to re-open the surface.",
    "Re-verify that the surface 'id' still matches the initial 'aria-controls' value.",
]
EXPECTED_RESULT = (
    "The 'aria-controls' value remains persistent and the link to the surface ID "
    "is consistently maintained across multiple UI state changes."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts861_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts861_failure.png"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-861 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "expected_result": EXPECTED_RESULT,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "trigger_attribute_timeout_ms": TRIGGER_ATTRIBUTE_TIMEOUT_MS,
        "surface_timeout_ms": SURFACE_TIMEOUT_MS,
        "dismissal_timeout_ms": DISMISSAL_TIMEOUT_MS,
        "linked_bugs": LINKED_BUGS,
        "preconditions": PRECONDITIONS,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)

            trigger: WorkspaceSwitcherTriggerObservation | None = None
            initial_trigger_aria: WorkspaceTriggerAriaControlsObservation | None = None
            first_surface: WorkspaceSwitcherSurfaceObservation | None = None
            first_reference: WorkspaceSwitcherSurfaceReferenceObservation | None = None
            dismissal: WorkspaceSwitcherTriggerDismissObservation | None = None
            post_close_trigger_aria: WorkspaceTriggerAriaControlsObservation | None = None
            reopened_surface: WorkspaceSwitcherSurfaceObservation | None = None
            reopened_trigger_aria: WorkspaceTriggerAriaControlsObservation | None = None
            reopened_reference: WorkspaceSwitcherSurfaceReferenceObservation | None = None

            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the repeated toggle inspection began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)
                trigger = page.observe_trigger()
                result["trigger_observation"] = _trigger_payload(trigger)
            except Exception as error:
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=str(error),
                )
                _capture_failure_screenshot(page, result)
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
                    f"trigger_text={trigger.visible_text!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Viewed the desktop Dashboard shell and confirmed the visible workspace "
                    "switcher trigger text before any toggle interaction."
                ),
                observed=(
                    f"trigger_text={trigger.visible_text!r}; "
                    f"display_name={trigger.display_name!r}; "
                    f"state_label={trigger.state_label!r}"
                ),
            )

            try:
                initial_trigger_aria = page.observe_trigger_aria_controls(
                    timeout_ms=TRIGGER_ATTRIBUTE_TIMEOUT_MS,
                )
                _assert_trigger_aria_controls_present(initial_trigger_aria, step=2)
                result["initial_trigger_aria_controls_observation"] = _trigger_aria_controls_payload(
                    initial_trigger_aria,
                )
            except Exception as error:
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=str(error),
                )
                _capture_failure_screenshot(page, result)
                raise
            _record_step(
                result,
                step=2,
                status="passed",
                action=REQUEST_STEPS[1],
                observed=(
                    f"Recorded initial aria-controls={initial_trigger_aria.aria_controls!r}; "
                    f"role={initial_trigger_aria.role!r}; "
                    f"tabindex={initial_trigger_aria.tabindex!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Inspected the visible trigger before opening the panel and noted the "
                    "accessibility relationship a user-assistive technology depends on."
                ),
                observed=f"initial_aria_controls={initial_trigger_aria.aria_controls!r}",
            )

            try:
                page.open_surface_with_click(timeout_ms=SURFACE_TIMEOUT_MS)
                first_surface = page.observe_surface(timeout_ms=SURFACE_TIMEOUT_MS)
                first_reference = page.observe_surface_reference(timeout_ms=SURFACE_TIMEOUT_MS)
                _assert_surface_opened(first_surface, step=3)
                result["first_surface_observation"] = _surface_payload(first_surface)
                result["first_surface_reference_observation"] = _surface_reference_payload(
                    first_reference,
                )
            except Exception as error:
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=str(error),
                )
                _capture_failure_screenshot(page, result)
                raise
            _record_step(
                result,
                step=3,
                status="passed",
                action=REQUEST_STEPS[2],
                observed=(
                    f"Opened surface heading={first_surface.heading_text!r}; "
                    f"visible_surface_id={first_reference.visible_surface_id!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Opened the workspace switcher through the real trigger and confirmed the "
                    "Workspace switcher surface became visible to the user."
                ),
                observed=(
                    f"heading={first_surface.heading_text!r}; "
                    f"surface_text_excerpt={_snippet(first_reference.visible_surface_text)!r}"
                ),
            )

            try:
                _assert_surface_matches_initial_aria(
                    initial_trigger=initial_trigger_aria,
                    current_trigger=initial_trigger_aria,
                    reference=first_reference,
                    step=4,
                )
            except Exception as error:
                _record_step(
                    result,
                    step=4,
                    status="failed",
                    action=REQUEST_STEPS[3],
                    observed=str(error),
                )
                _capture_failure_screenshot(page, result)
                raise
            _record_step(
                result,
                step=4,
                status="passed",
                action=REQUEST_STEPS[3],
                observed=(
                    f"initial_aria_controls={initial_trigger_aria.aria_controls!r}; "
                    f"visible_surface_id={first_reference.visible_surface_id!r}"
                ),
            )

            try:
                page.toggle_switcher_via_trigger(timeout_ms=DISMISSAL_TIMEOUT_MS)
                dismissal = page.wait_for_dismissal_after_trigger_click(
                    timeout_ms=DISMISSAL_TIMEOUT_MS,
                )
                _assert_trigger_dismissal(dismissal)
                post_close_trigger_aria = page.observe_trigger_aria_controls(
                    timeout_ms=TRIGGER_ATTRIBUTE_TIMEOUT_MS,
                )
                _assert_trigger_aria_controls_present(post_close_trigger_aria, step=5)
                _assert_trigger_aria_controls_persist(
                    initial=initial_trigger_aria,
                    current=post_close_trigger_aria,
                    step=5,
                )
                result["trigger_dismissal_observation"] = _trigger_dismissal_payload(
                    dismissal,
                )
                result["post_close_trigger_aria_controls_observation"] = _trigger_aria_controls_payload(
                    post_close_trigger_aria,
                )
            except Exception as error:
                _record_step(
                    result,
                    step=5,
                    status="failed",
                    action=REQUEST_STEPS[4],
                    observed=str(error),
                )
                _capture_failure_screenshot(page, result)
                raise
            _record_step(
                result,
                step=5,
                status="passed",
                action=REQUEST_STEPS[4],
                observed=(
                    f"Panel dismissed via trigger toggle; "
                    f"dashboard_visible_after={dismissal.dashboard_visible}; "
                    f"aria_controls_after_close={post_close_trigger_aria.aria_controls!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Closed the switcher the same way a desktop user would and checked the "
                    "panel disappeared while the trigger stayed visible."
                ),
                observed=(
                    f"dashboard_visible_after={dismissal.dashboard_visible}; "
                    f"trigger_visible_after={dismissal.trigger_visible}; "
                    f"trigger_label_after={dismissal.trigger_label!r}"
                ),
            )

            try:
                page.open_surface_with_click(timeout_ms=SURFACE_TIMEOUT_MS)
                reopened_surface = page.observe_surface(timeout_ms=SURFACE_TIMEOUT_MS)
                reopened_trigger_aria = page.observe_trigger_aria_controls(
                    timeout_ms=TRIGGER_ATTRIBUTE_TIMEOUT_MS,
                )
                _assert_trigger_aria_controls_present(reopened_trigger_aria, step=6)
                reopened_reference = page.observe_surface_reference(timeout_ms=SURFACE_TIMEOUT_MS)
                _assert_trigger_aria_controls_persist(
                    initial=initial_trigger_aria,
                    current=reopened_trigger_aria,
                    step=6,
                )
                _assert_surface_opened(reopened_surface, step=6)
                result["reopened_trigger_aria_controls_observation"] = _trigger_aria_controls_payload(
                    reopened_trigger_aria,
                )
                result["reopened_surface_observation"] = _surface_payload(reopened_surface)
                result["reopened_surface_reference_observation"] = _surface_reference_payload(
                    reopened_reference,
                )
            except Exception as error:
                _record_step(
                    result,
                    step=6,
                    status="failed",
                    action=REQUEST_STEPS[5],
                    observed=str(error),
                )
                _capture_failure_screenshot(page, result)
                raise
            _record_step(
                result,
                step=6,
                status="passed",
                action=REQUEST_STEPS[5],
                observed=(
                    f"Re-opened surface heading={reopened_surface.heading_text!r}; "
                    f"reopened_aria_controls={reopened_trigger_aria.aria_controls!r}; "
                    f"visible_surface_id={reopened_reference.visible_surface_id!r}"
                ),
            )

            try:
                _assert_surface_matches_initial_aria(
                    initial_trigger=initial_trigger_aria,
                    current_trigger=reopened_trigger_aria,
                    reference=reopened_reference,
                    step=7,
                )
                _assert_surface_id_persisted(
                    first_reference=first_reference,
                    reopened_reference=reopened_reference,
                    step=7,
                )
            except Exception as error:
                _record_step(
                    result,
                    step=7,
                    status="failed",
                    action=REQUEST_STEPS[6],
                    observed=str(error),
                )
                _capture_failure_screenshot(page, result)
                raise
            _record_step(
                result,
                step=7,
                status="passed",
                action=REQUEST_STEPS[6],
                observed=(
                    f"initial_aria_controls={initial_trigger_aria.aria_controls!r}; "
                    f"reopened_aria_controls={reopened_trigger_aria.aria_controls!r}; "
                    f"reopened_reference_trigger_aria_controls={reopened_reference.trigger_aria_controls!r}; "
                    f"first_surface_id={first_reference.visible_surface_id!r}; "
                    f"reopened_surface_id={reopened_reference.visible_surface_id!r}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Re-opened the switcher and confirmed the same user-visible surface "
                    "relationship came back, with the Workspace switcher heading and content "
                    "still attached to the same accessibility id."
                ),
                observed=(
                    f"reopened_heading={reopened_surface.heading_text!r}; "
                    f"reopened_aria_controls={reopened_trigger_aria.aria_controls!r}; "
                    f"reopened_surface_id={reopened_reference.visible_surface_id!r}; "
                    f"surface_text_excerpt={_snippet(reopened_reference.visible_surface_text)!r}"
                ),
            )

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _capture_failure_screenshot(page, result)
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _capture_failure_screenshot(page, result)
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _assert_trigger_aria_controls_present(
    observation: WorkspaceTriggerAriaControlsObservation,
    *,
    step: int,
) -> None:
    if observation.aria_controls:
        return
    raise AssertionError(
        f"Step {step} failed: the workspace switcher trigger did not expose an "
        "aria-controls attribute.\n"
        f"Observed label: {observation.label!r}\n"
        f"Observed role: {observation.role!r}\n"
        f"Observed aria-controls: {observation.aria_controls!r}\n"
        f"Observed trigger HTML: {observation.outer_html}",
    )


def _assert_surface_opened(
    observation: WorkspaceSwitcherSurfaceObservation,
    *,
    step: int,
) -> None:
    failures: list[str] = []
    if not observation.dialog_visible:
        failures.append("the opened switcher surface was not reported as visible")
    if observation.heading_text.strip() != "Workspace switcher":
        failures.append(
            f"the visible heading was {observation.heading_text!r} instead of 'Workspace switcher'",
        )
    if not observation.interactive_elements:
        failures.append("the visible switcher surface did not expose any interactive elements")
    if failures:
        raise AssertionError(
            f"Step {step} failed: opening the workspace switcher did not expose the "
            "expected visible surface.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed body text:\n{observation.body_text}",
        )


def _assert_surface_matches_initial_aria(
    *,
    initial_trigger: WorkspaceTriggerAriaControlsObservation,
    current_trigger: WorkspaceTriggerAriaControlsObservation,
    reference: WorkspaceSwitcherSurfaceReferenceObservation,
    step: int,
) -> None:
    failures: list[str] = []
    initial_aria = initial_trigger.aria_controls
    current_aria = current_trigger.aria_controls
    if not initial_aria:
        failures.append("the initial trigger aria-controls attribute was missing")
    if not current_aria:
        failures.append("the current trigger aria-controls attribute was missing")
    if initial_aria and current_aria and current_aria != initial_aria:
        failures.append(
            f"the trigger aria-controls value changed ({current_aria!r} != {initial_aria!r})",
        )
    if not reference.trigger_aria_controls:
        failures.append(
            "the reopened switcher reference did not report the trigger aria-controls value",
        )
    if (
        current_aria
        and reference.trigger_aria_controls
        and reference.trigger_aria_controls != current_aria
    ):
        failures.append(
            "the reopened switcher reference did not match the live trigger aria-controls "
            f"value ({reference.trigger_aria_controls!r} != {current_aria!r})",
        )
    if not reference.visible_surface_id:
        failures.append("the visible workspace switcher surface did not expose an id attribute")
    if initial_aria and not reference.controlled_surface_found:
        failures.append(
            f"no DOM element with id {initial_aria!r} existed when the switcher was open",
        )
    if initial_aria and not reference.controlled_surface_visible:
        failures.append(
            f"the DOM element referenced by aria-controls={initial_aria!r} was not visible",
        )
    if (
        initial_aria
        and reference.visible_surface_id
        and reference.visible_surface_id != initial_aria
    ):
        failures.append(
            "the visible workspace switcher surface id did not match the initial "
            f"aria-controls value ({reference.visible_surface_id!r} != {initial_aria!r})",
        )
    if failures:
        raise AssertionError(
            f"Step {step} failed: the workspace switcher aria-controls relationship did not "
            "stay aligned with the opened surface.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed initial aria-controls: {initial_aria!r}\n"
            + f"Observed current aria-controls: {current_aria!r}\n"
            + f"Observed reference trigger aria-controls: {reference.trigger_aria_controls!r}\n"
            + f"Observed visible surface id: {reference.visible_surface_id!r}\n"
            + f"Observed visible surface role/tag: {reference.visible_surface_role!r} / "
            + f"{reference.visible_surface_tag_name!r}\n"
            + f"Observed visible surface text: {_snippet(reference.visible_surface_text)!r}\n"
            + f"Observed trigger HTML: {current_trigger.outer_html}\n"
            + f"Observed visible surface HTML: {reference.visible_surface_outer_html}",
        )


def _assert_trigger_aria_controls_persist(
    *,
    initial: WorkspaceTriggerAriaControlsObservation,
    current: WorkspaceTriggerAriaControlsObservation,
    step: int,
) -> None:
    if current.aria_controls == initial.aria_controls:
        return
    raise AssertionError(
        f"Step {step} failed: the workspace switcher trigger aria-controls value changed "
        "after the panel was closed.\n"
        f"Observed initial aria-controls: {initial.aria_controls!r}\n"
        f"Observed aria-controls after close: {current.aria_controls!r}\n"
        f"Observed trigger HTML after close: {current.outer_html}",
    )


def _assert_trigger_dismissal(observation: WorkspaceSwitcherTriggerDismissObservation) -> None:
    failures: list[str] = []
    if not observation.dashboard_visible:
        failures.append("Dashboard was not visible after dismissing the switcher")
    if not observation.trigger_visible:
        failures.append("the workspace switcher trigger was not visible after dismissal")
    if failures:
        raise AssertionError(
            "Step 5 failed: clicking the workspace switcher trigger to close the panel did "
            "not leave the user back on the Dashboard shell.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed body text:\n{observation.body_text}",
        )


def _assert_surface_id_persisted(
    *,
    first_reference: WorkspaceSwitcherSurfaceReferenceObservation,
    reopened_reference: WorkspaceSwitcherSurfaceReferenceObservation,
    step: int,
) -> None:
    if first_reference.visible_surface_id == reopened_reference.visible_surface_id:
        return
    raise AssertionError(
        f"Step {step} failed: the workspace switcher surface id changed after the panel was "
        "closed and reopened.\n"
        f"Observed first surface id: {first_reference.visible_surface_id!r}\n"
        f"Observed reopened surface id: {reopened_reference.visible_surface_id!r}\n"
        f"Observed first surface text: {_snippet(first_reference.visible_surface_text)!r}\n"
        f"Observed reopened surface text: {_snippet(reopened_reference.visible_surface_text)!r}",
    )


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
        _review_replies_payload(result, passed=True),
        encoding="utf-8",
    )


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-861 failed"))
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
        _review_replies_payload(result, passed=False),
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _capture_failure_screenshot(
    page: LiveWorkspaceSwitcherPage | None,
    result: dict[str, object],
) -> None:
    if page is None or result.get("screenshot"):
        return
    try:
        page.screenshot(str(FAILURE_SCREENSHOT_PATH))
        result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
    except Exception as screenshot_error:
        result["screenshot_error"] = (
            f"{type(screenshot_error).__name__}: {screenshot_error}"
        )


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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "* Located the visible workspace switcher trigger on Dashboard in a desktop viewport.",
        "* Recorded the trigger aria-controls value before opening the switcher.",
        "* Opened, closed, and reopened the workspace switcher through the real trigger.",
        "* Checked that the opened surface id matched the original aria-controls value on both openings.",
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
        "## Preconditions checked",
        *[f"- {item}" for item in PRECONDITIONS],
        "",
        "## What was automated",
        "- Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "- Located the visible workspace switcher trigger on Dashboard in a desktop viewport.",
        "- Recorded the trigger `aria-controls` value before opening the switcher.",
        "- Opened, closed, and reopened the workspace switcher through the real trigger.",
        "- Verified the opened surface `id` stayed aligned with the original trigger `aria-controls` value.",
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
            "- Added TS-861 live desktop coverage for repeated workspace switcher toggles "
            "and persistent `aria-controls` to surface-id linkage."
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
            "- Outcome: the visible workspace switcher trigger kept the same "
            "`aria-controls` value and the reopened surface kept the matching id."
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
            f"# {TICKET_KEY} - Workspace switcher aria-controls relationship is not persistent across repeated toggles",
            "",
            "## Steps to reproduce",
            "1. Open the deployed TrackState app on a desktop browser and navigate to Dashboard.",
            "2. Locate the visible workspace switcher trigger in the header.",
            "3. Record the trigger aria-controls attribute value before opening the switcher.",
            "4. Open the workspace switcher surface from the trigger and compare the visible surface id.",
            "5. Close the switcher by clicking the trigger again.",
            "6. Reopen the switcher by clicking the same trigger.",
            "7. Compare the reopened visible surface id with the initial trigger aria-controls value.",
            "",
            "## Exact steps from the test case with observations",
            *[_annotated_step_line(result, index + 1, action) for index, action in enumerate(REQUEST_STEPS)],
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            f"- Expected: {EXPECTED_RESULT}",
            f"- Actual: {_failed_step_summary(result)}",
            "",
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Run command: {RUN_COMMAND}",
            "",
            "## Missing or broken production capability",
            *_missing_capability_lines(result),
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
            "```json",
            json.dumps(
                {
                    "trigger_observation": result.get("trigger_observation"),
                    "initial_trigger_aria_controls_observation": result.get(
                        "initial_trigger_aria_controls_observation",
                    ),
                    "first_surface_reference_observation": result.get(
                        "first_surface_reference_observation",
                    ),
                    "trigger_dismissal_observation": result.get(
                        "trigger_dismissal_observation",
                    ),
                    "post_close_trigger_aria_controls_observation": result.get(
                        "post_close_trigger_aria_controls_observation",
                    ),
                    "reopened_trigger_aria_controls_observation": result.get(
                        "reopened_trigger_aria_controls_observation",
                    ),
                    "reopened_surface_reference_observation": result.get(
                        "reopened_surface_reference_observation",
                    ),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


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


def _review_replies_payload(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(passed=passed, result=result),
        }
        for thread in _discussion_threads()
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("resolved") is False
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(*, passed: bool, result: dict[str, object]) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else (
            "Re-ran "
            f"`{RUN_COMMAND}`: still failing. Current failure: {_failed_step_summary(result)}"
        )
    )
    return (
        "Fixed: step 6 now re-observes the live workspace switcher trigger "
        "`aria-controls` value after reopening, records it in the test artifacts, and "
        "step 7 compares that live reopened value plus the reopened surface reference "
        f"against the initial observation. {rerun_summary}"
    )


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _missing_capability_lines(result: dict[str, object]) -> list[str]:
    failed_step = _first_failed_step_number(result)
    failure_detail = _failed_step_detail(result)
    reasons = _failure_reasons(failure_detail)
    if failed_step in (2, 5):
        intro = (
            "The production desktop workspace switcher trigger does not preserve a stable "
            "`aria-controls` attribute across the required toggle cycle:"
        )
        return [intro, *[f"- {reason}" for reason in reasons]] if reasons else [intro]
    if failed_step in (4, 7):
        intro = (
            "The production desktop workspace switcher does not keep a persistent "
            "`aria-controls` to surface-id relationship across repeated openings:"
        )
        return [intro, *[f"- {reason}" for reason in reasons]] if reasons else [intro]
    if failed_step in (3, 6):
        intro = (
            "The production desktop workspace switcher does not reopen the expected visible "
            "Workspace switcher surface during the repeated toggle flow:"
        )
        return [intro, *[f"- {reason}" for reason in reasons]] if reasons else [intro]
    primary_detail = _primary_failure_detail(failure_detail)
    return [
        "The production desktop workspace switcher does not satisfy the TS-861 repeated "
        f"toggle accessibility contract in this run: {primary_detail}"
    ]


def _failed_step_detail(result: dict[str, object]) -> str:
    failed_step = _first_failed_step_number(result)
    if failed_step is None:
        return str(result.get("error", "No failed step recorded."))
    return _step_observation(result, failed_step)


def _failure_reasons(detail: str) -> list[str]:
    reasons: list[str] = []
    for line in detail.splitlines()[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Observed "):
            break
        if stripped.startswith("- "):
            reasons.append(stripped[2:])
    return reasons


def _primary_failure_detail(detail: str) -> str:
    first_line = detail.splitlines()[0].strip() if detail else "Unknown failure."
    if ": " in first_line:
        return first_line.split(": ", 1)[1]
    return first_line


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
    first_failed = _first_failed_step_number(result)
    if first_failed is not None and step_number > first_failed:
        return f"Not reached because Step {first_failed} failed."
    return "<no observation recorded>"


def _first_failed_step_number(result: dict[str, object]) -> int | None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("status") != "passed":
            return int(step.get("step", -1))
    return None


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
        "left": observation.left,
        "top": observation.top,
        "width": observation.width,
        "height": observation.height,
        "top_button_labels": list(observation.top_button_labels),
    }


def _trigger_aria_controls_payload(
    observation: WorkspaceTriggerAriaControlsObservation,
) -> dict[str, object]:
    return {
        "label": observation.label,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "tabindex": observation.tabindex,
        "keyboard_focusable": observation.keyboard_focusable,
        "aria_controls": observation.aria_controls,
        "outer_html": observation.outer_html,
    }


def _surface_payload(observation: WorkspaceSwitcherSurfaceObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "dialog_visible": observation.dialog_visible,
        "heading_text": observation.heading_text,
        "interactive_elements": [asdict(item) for item in observation.interactive_elements],
        "semantics_nodes": [asdict(item) for item in observation.semantics_nodes],
        "missing_interactive_labels": list(observation.missing_interactive_labels),
        "missing_semantics_labels": list(observation.missing_semantics_labels),
        "badges": [asdict(item) for item in observation.badges],
        "interactive_icons": [asdict(item) for item in observation.interactive_icons],
        "interactive_texts": [asdict(item) for item in observation.interactive_texts],
    }


def _surface_reference_payload(
    observation: WorkspaceSwitcherSurfaceReferenceObservation,
) -> dict[str, object]:
    return {
        "trigger_label": observation.trigger_label,
        "trigger_aria_controls": observation.trigger_aria_controls,
        "controlled_surface_found": observation.controlled_surface_found,
        "controlled_surface_visible": observation.controlled_surface_visible,
        "controlled_surface_id": observation.controlled_surface_id,
        "controlled_surface_role": observation.controlled_surface_role,
        "controlled_surface_tag_name": observation.controlled_surface_tag_name,
        "controlled_surface_text": observation.controlled_surface_text,
        "visible_surface_id": observation.visible_surface_id,
        "visible_surface_role": observation.visible_surface_role,
        "visible_surface_tag_name": observation.visible_surface_tag_name,
        "visible_surface_text": observation.visible_surface_text,
        "trigger_outer_html": observation.trigger_outer_html,
        "visible_surface_outer_html": observation.visible_surface_outer_html,
    }


def _trigger_dismissal_payload(
    observation: WorkspaceSwitcherTriggerDismissObservation,
) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "dashboard_visible": observation.dashboard_visible,
        "trigger_visible": observation.trigger_visible,
        "trigger_label": observation.trigger_label,
    }


def _snippet(text: str, *, max_length: int = 160) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."


if __name__ == "__main__":
    main()
