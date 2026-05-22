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
    FocusNavigationStep,
    LiveWorkspaceSwitcherPage,
    WorkspaceSwitcherTriggerObservation,
    WorkspaceTriggerFocusabilityObservation,
    WorkspaceTriggerKeyboardFocusObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-830"
TEST_CASE_TITLE = (
    "Sequential top-bar navigation — workspace switcher trigger is focusable in "
    "logical order"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-830/test_ts_830.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
TOP_BAR_TAB_COUNT = 20
TRIGGER_TAB_COUNT = 24
INPUT_DIR = REPO_ROOT / "input" / TICKET_KEY
FIRST_TOP_BAR_CONTROL_LABEL = "Create issue"

REQUEST_STEPS = [
    "Launch the application in a desktop browser.",
    "Start keyboard navigation from the first control in the top bar (e.g., 'Create issue').",
    "Press the 'Tab' key repeatedly to cycle through all primary navigation controls.",
    "Observe the focus sequence and the visible focus state of the workspace switcher trigger.",
]
EXPECTED_RESULT = (
    "The workspace switcher trigger receives keyboard focus in its correct logical "
    "sequence after 'Settings' and immediately before the Search control, and the "
    "trigger shows a visible focus indicator when focused."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
DISCUSSIONS_RAW_PATH = INPUT_DIR / "pr_discussions_raw.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts830_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts830_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-830 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "top_bar_tab_count": TOP_BAR_TAB_COUNT,
        "trigger_tab_count": TRIGGER_TAB_COUNT,
        "expected_result": EXPECTED_RESULT,
        "user_login": user.login,
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
                        "desktop state before the top-bar keyboard navigation scenario "
                        "began.\n"
                        f"Observed runtime state: {runtime.kind}\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                page.dismiss_connection_banner()
                page.navigate_to_section("Dashboard")
                page.set_viewport(**DESKTOP_VIEWPORT)
                trigger = page.observe_trigger()
                result["trigger_observation"] = _trigger_payload(trigger)
            except Exception as error:
                _capture_failure_screenshot(page, result)
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
                    "Viewed the desktop app shell before tabbing and confirmed the visible "
                    "top-bar controls, including the workspace switcher trigger text."
                ),
                observed=(
                    f"trigger_text={trigger.visible_text!r}; "
                    f"top_buttons={list(trigger.top_button_labels)!r}"
                ),
            )

            try:
                focusability = page.observe_trigger_focusability()
                _assert_keyboard_focusable(focusability)
                result["trigger_focusability_observation"] = _focusability_payload(
                    focusability,
                )
            except Exception as error:
                _capture_failure_screenshot(page, result)
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
                    f"Trigger is keyboard-focusable with tabindex={focusability.tabindex!r}; "
                    f"role={focusability.role!r}; tag={focusability.tag_name!r}"
                ),
            )

            try:
                sequence = page.collect_tab_sequence_from_first_top_bar_control(
                    tab_count=TOP_BAR_TAB_COUNT,
                )
                order_summary = _assert_top_bar_focus_order(sequence)
                result["top_bar_focus_sequence"] = [asdict(step) for step in sequence]
            except Exception as error:
                _capture_failure_screenshot(page, result)
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
                observed=order_summary,
            )
            _record_human_verification(
                result,
                check=(
                    "Tabbed through the desktop top bar like a user and observed the "
                    "actual visible keyboard sequence."
                ),
                observed=order_summary,
            )

            try:
                page.focus_first_top_bar_control()
                trigger_focus = page.observe_trigger_keyboard_focus(
                    tab_count=TRIGGER_TAB_COUNT,
                )
                focus_summary = _assert_visible_focus_indicator(trigger_focus)
                result["trigger_keyboard_focus_observation"] = (
                    _trigger_keyboard_focus_payload(trigger_focus)
                )
                page.screenshot(str(SUCCESS_SCREENSHOT_PATH), full_page=False)
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH.relative_to(REPO_ROOT))
            except Exception as error:
                _capture_failure_screenshot(page, result)
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
                observed=focus_summary,
            )
            _record_human_verification(
                result,
                check=(
                    "Observed the focused workspace switcher trigger itself, not just DOM "
                    "presence, and confirmed a visible keyboard focus indicator was shown."
                ),
                observed=focus_summary,
            )

        _write_pass_outputs(result)
        print("TS-830 passed")
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        if page is not None:
            try:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH), full_page=True)
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH.relative_to(REPO_ROOT))
            except Exception:
                pass
        _write_failure_outputs(result)
        raise


def _assert_keyboard_focusable(
    observation: WorkspaceTriggerFocusabilityObservation,
) -> None:
    if not observation.keyboard_focusable or observation.tabindex in (None, "-1"):
        raise AssertionError(
            "Step 2 failed: the visible workspace switcher trigger is not keyboard-"
            "focusable in the desktop tab order.\n"
            f"Observed label={observation.label!r}; role={observation.role!r}; "
            f"tag={observation.tag_name!r}; tabindex={observation.tabindex!r}; "
            f"keyboard_focusable={observation.keyboard_focusable}\n"
            f"Observed trigger HTML: {observation.outer_html}"
        )


def _assert_top_bar_focus_order(
    sequence: tuple[FocusNavigationStep, ...],
) -> str:
    distinct_labels = _distinct_focus_labels(sequence)
    if not distinct_labels:
        raise AssertionError(
            "Step 3 failed: no keyboard focus sequence was captured from the top bar.",
        )
    _assert_started_from_first_top_bar_control(sequence, step_number=3)
    if _label_index(distinct_labels, lambda label: label == "Settings") is None:
        raise AssertionError(
            "Step 3 failed: the captured top-bar keyboard sequence did not include "
            "Settings.\n"
            f"Observed focus sequence: {_focus_sequence_summary(sequence)}\n"
            f"Observed distinct sequence: {_distinct_focus_sequence_summary(sequence)}",
        )
    trigger_index = _label_index(
        distinct_labels,
        lambda label: label.startswith("Workspace switcher:"),
    )
    if trigger_index is None:
        raise AssertionError(
            "Step 3 failed: the captured top-bar keyboard sequence did not include "
            "the workspace switcher trigger.\n"
            f"Observed focus sequence: {_focus_sequence_summary(sequence)}\n"
            f"Observed distinct sequence: {_distinct_focus_sequence_summary(sequence)}",
        )
    if _label_index(distinct_labels, _is_search_control_label) is None:
        raise AssertionError(
            "Step 3 failed: the captured top-bar keyboard sequence did not include "
            "the Search control.\n"
            f"Observed focus sequence: {_focus_sequence_summary(sequence)}\n"
            f"Observed distinct sequence: {_distinct_focus_sequence_summary(sequence)}",
        )
    adjacent_triplet = _adjacent_workspace_triplet(distinct_labels)
    if adjacent_triplet is None:
        previous_label = distinct_labels[trigger_index - 1] if trigger_index > 0 else "<none>"
        next_label = (
            distinct_labels[trigger_index + 1]
            if trigger_index + 1 < len(distinct_labels)
            else "<none>"
        )
        raise AssertionError(
            "Step 3 failed: the workspace switcher trigger was not reached in the "
            "required logical sequence immediately after Settings and immediately "
            "before the Search control.\n"
            f"Observed trigger neighbors: previous={previous_label!r}, "
            f"next={next_label!r}\n"
            f"Observed focus sequence: {_focus_sequence_summary(sequence)}\n"
            f"Observed distinct sequence: {_distinct_focus_sequence_summary(sequence)}",
        )
    settings_label, trigger_label, search_label = adjacent_triplet
    return (
        "Observed focus sequence: "
        f"{_focus_sequence_summary(sequence)}; "
        "distinct keyboard order: "
        f"{_distinct_focus_sequence_summary(sequence)}; "
        "workspace switcher remained in the required adjacent order: "
        f"{settings_label} -> {trigger_label} -> {search_label}."
    )


def _distinct_focus_labels(sequence: tuple[FocusNavigationStep, ...]) -> list[str]:
    distinct: list[str] = []
    for step in sequence:
        label = (step.after_label or "").replace("\n", " ").strip()
        if not label:
            continue
        if not distinct or distinct[-1] != label:
            distinct.append(label)
    return distinct


def _distinct_focus_sequence_summary(
    sequence: tuple[FocusNavigationStep, ...],
    *,
    final_active_label: str | None = None,
) -> str:
    labels = _distinct_focus_labels(sequence)
    normalized_final_label = (final_active_label or "").replace("\n", " ").strip()
    if normalized_final_label and (not labels or labels[-1] != normalized_final_label):
        labels.append(normalized_final_label)
    return " -> ".join(labels)


def _adjacent_workspace_triplet(labels: list[str]) -> tuple[str, str, str] | None:
    for index in range(1, len(labels) - 1):
        current = labels[index]
        if not current.startswith("Workspace switcher:"):
            continue
        previous = labels[index - 1]
        following = labels[index + 1]
        if previous == "Settings" and _is_search_control_label(following):
            return previous, current, following
    return None


def _label_index(
    labels: list[str],
    predicate: callable,
) -> int | None:
    for index, label in enumerate(labels):
        if predicate(label):
            return index
    return None


def _assert_visible_focus_indicator(
    observation: WorkspaceTriggerKeyboardFocusObservation,
) -> str:
    _assert_started_from_first_top_bar_control(observation.focus_sequence, step_number=4)
    if observation.active_label_after_focus is None or not observation.active_label_after_focus.startswith(
        "Workspace switcher:"
    ):
        raise AssertionError(
            "Step 4 failed: keyboard Tab navigation never moved focus onto the visible "
            "workspace switcher trigger.\n"
            f"{_trigger_focus_summary(observation)}",
        )
    outline_width = observation.after_outline_width.strip().lower()
    outline_visible = outline_width not in {"", "0", "0px"} and "none" not in observation.after_outline.lower()
    box_shadow_visible = observation.after_box_shadow.strip().lower() != "none"
    if not outline_visible and not box_shadow_visible:
        raise AssertionError(
            "Step 4 failed: the focused workspace switcher trigger did not show a "
            "visible focus indicator.\n"
            f"{_trigger_focus_summary(observation)}",
        )
    return _trigger_focus_summary(observation)


def _assert_started_from_first_top_bar_control(
    sequence: tuple[FocusNavigationStep, ...],
    *,
    step_number: int,
) -> None:
    if not sequence:
        raise AssertionError(
            f"Step {step_number} failed: no keyboard focus sequence was captured from "
            "the first top-bar control.",
        )
    starting_label = _normalize_focus_label(sequence[0].before_label)
    if starting_label != FIRST_TOP_BAR_CONTROL_LABEL:
        raise AssertionError(
            f"Step {step_number} failed: keyboard navigation did not start from the "
            f'first top-bar control "{FIRST_TOP_BAR_CONTROL_LABEL}".\n'
            f"Observed starting label: {starting_label or '<none>'!r}\n"
            f"Observed focus sequence: {_focus_sequence_summary(sequence)}\n"
            f"Observed distinct sequence: {_distinct_focus_sequence_summary(sequence)}",
        )


def _normalize_focus_label(label: str | None) -> str:
    return (label or "").replace("\n", " ").strip()


def _focus_sequence_summary(sequence: tuple[FocusNavigationStep, ...]) -> str:
    return " -> ".join(
        f"{step.step}:{_normalize_focus_label(step.after_label or '<none>')}"
        for step in sequence
    )


def _trigger_focus_summary(
    observation: WorkspaceTriggerKeyboardFocusObservation,
) -> str:
    return (
        f"focus_sequence={_focus_sequence_summary(observation.focus_sequence)}; "
        f"distinct_focus_sequence={_distinct_focus_sequence_summary(observation.focus_sequence, final_active_label=observation.active_label_after_focus)}; "
        f"trigger_text={observation.trigger_text!r}; "
        f"active_after_focus={observation.active_label_after_focus!r}; "
        f"active_role_after_focus={observation.active_role_after_focus!r}; "
        f"active_tag_after_focus={observation.active_tag_name_after_focus!r}; "
        f"before_outline={observation.before_outline!r}; "
        f"before_outline_width={observation.before_outline_width!r}; "
        f"before_box_shadow={observation.before_box_shadow!r}; "
        f"after_outline={observation.after_outline!r}; "
        f"after_outline_width={observation.after_outline_width!r}; "
        f"after_box_shadow={observation.after_box_shadow!r}"
    )


def _is_search_control_label(label: str) -> bool:
    normalized = label.strip()
    return (
        normalized in {"Search", "Search issues", "JQL Search"}
        or normalized.startswith("Search ")
        or normalized.endswith(" Search")
    )


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


def _focusability_payload(
    observation: WorkspaceTriggerFocusabilityObservation,
) -> dict[str, object]:
    return {
        "label": observation.label,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "tabindex": observation.tabindex,
        "keyboard_focusable": observation.keyboard_focusable,
        "outer_html": observation.outer_html,
    }


def _trigger_keyboard_focus_payload(
    observation: WorkspaceTriggerKeyboardFocusObservation,
) -> dict[str, object]:
    return {
        "trigger_label": observation.trigger_label,
        "trigger_text": observation.trigger_text,
        "bounds": {
            "x": observation.trigger_x,
            "y": observation.trigger_y,
            "width": observation.trigger_width,
            "height": observation.trigger_height,
        },
        "before_outline": observation.before_outline,
        "before_outline_color": observation.before_outline_color,
        "before_outline_width": observation.before_outline_width,
        "before_box_shadow": observation.before_box_shadow,
        "after_outline": observation.after_outline,
        "after_outline_color": observation.after_outline_color,
        "after_outline_width": observation.after_outline_width,
        "after_box_shadow": observation.after_box_shadow,
        "active_label_after_focus": observation.active_label_after_focus,
        "active_role_after_focus": observation.active_role_after_focus,
        "active_tag_name_after_focus": observation.active_tag_name_after_focus,
        "active_outer_html_after_focus": observation.active_outer_html_after_focus,
        "focus_sequence": [asdict(step) for step in observation.focus_sequence],
    }


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


def _capture_failure_screenshot(
    page: LiveWorkspaceSwitcherPage | None,
    result: dict[str, object],
) -> None:
    if page is None:
        return
    try:
        page.screenshot(str(FAILURE_SCREENSHOT_PATH), full_page=True)
    except Exception:
        return
    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH.relative_to(REPO_ROOT))


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
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": str(result.get("error", "AssertionError: TS-830 failed")),
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


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_TITLE}",
        "",
        "h4. What was checked by automation",
        "* Opened the deployed desktop TrackState app in Chromium with a stored hosted token.",
        "* Verified the visible workspace switcher trigger exposes keyboard-focusable semantics.",
        "* Collected the real Tab sequence across the primary top-bar controls.",
        "* Verified the workspace switcher trigger shows a visible focus indicator when focused.",
        "",
        "h4. Real user-style verification",
        "* Confirmed the visible top-bar labels rendered in the desktop shell before tabbing.",
        "* Observed the live keyboard order as a user would experience it, not just DOM presence.",
        "* Confirmed the focus indicator on the actual trigger element after keyboard focus landed on it.",
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
        "h4. Human-style verification observations",
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
        "## What was checked by automation",
        "- Opened the deployed desktop TrackState app in Chromium with a stored hosted token.",
        "- Verified the workspace switcher trigger was keyboard-focusable.",
        "- Collected the real Tab sequence across the top-bar controls.",
        "- Verified the focused trigger showed a visible focus indicator.",
        "",
        "## Real user-style verification",
        "- Confirmed the visible top-bar labels rendered in the desktop shell before tabbing.",
        "- Observed the live keyboard order as a user would experience it.",
        "- Confirmed the visible focus treatment on the actual workspace switcher trigger.",
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
        "## Human-style verification observations",
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
            "- Outcome: the workspace switcher trigger was reached in logical order "
            "after Settings and before the Search control, and the focused trigger showed "
            "a visible focus indicator."
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
            f"# {TICKET_KEY} - Desktop top-bar keyboard order misses or misrenders the workspace switcher trigger",
            "",
            "## Steps to reproduce",
            "1. Open the deployed TrackState app in a desktop browser.",
            "2. Go to Dashboard and use keyboard navigation across the top bar.",
            "3. Start from the first visible top-bar control and press `Tab` repeatedly.",
            "4. Observe where focus goes around `Settings`, the workspace switcher trigger, and the Search control.",
            "5. When focus lands on the workspace switcher trigger, observe whether a visible focus indicator is shown.",
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
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps(
                {
                    "trigger_observation": result.get("trigger_observation"),
                    "trigger_focusability_observation": result.get(
                        "trigger_focusability_observation",
                    ),
                    "top_bar_focus_sequence": result.get("top_bar_focus_sequence"),
                    "trigger_keyboard_focus_observation": result.get(
                        "trigger_keyboard_focus_observation",
                    ),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _annotated_step_line(result: dict[str, object], step_number: int, action: str) -> str:
    marker = "✅" if _step_status(result, step_number) == "passed" else "❌"
    return (
        f"{step_number}. {marker} {action}\n"
        f"   Actual: {_step_observation(result, step_number)}"
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
    last_failed_step: int | None = None
    for step in steps:
        if not isinstance(step, dict):
            continue
        current_step = int(step.get("step", -1))
        if current_step == step_number:
            return str(step.get("observed", "<no observation recorded>"))
        if step.get("status") != "passed":
            last_failed_step = current_step
    if last_failed_step is not None and step_number > last_failed_step:
        return f"Not reached because step {last_failed_step} failed."
    return "<no observation recorded>"


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return [f"{prefix} <no step data recorded>"]
    return [
        (
            f"{prefix} {'✅' if step.get('status') == 'passed' else '❌'} "
            f"Step {step.get('step')}: {step.get('action')} "
            f"Observed: {step.get('observed')}"
        )
        for step in steps
        if isinstance(step, dict)
    ] or [f"{prefix} <no step data recorded>"]


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    prefix = "*" if jira else "-"
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return [f"{prefix} <no human-style verification recorded>"]
    return [
        f"{prefix} {check.get('check')}: {check.get('observed')}"
        for check in checks
        if isinstance(check, dict)
    ] or [f"{prefix} <no human-style verification recorded>"]


def _artifact_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    screenshot = result.get("screenshot")
    if not screenshot:
        return []
    if jira:
        return [f"* Screenshot: {{{{{screenshot}}}}}"]
    return [f"- Screenshot: `{screenshot}`"]


def _review_replies_payload(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(result=result, passed=passed),
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


def _review_reply_text(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else (
            "Re-ran "
            f"`{RUN_COMMAND}`: still failing. Current failure: {_failed_step_summary(result)}"
        )
    )
    return (
        "Fixed: Steps 3 and 4 now explicitly anchor keyboard navigation at the first "
        "top-bar control (`Create issue`) before tabbing, so the captured order and "
        "focus-ring evidence match the exact TS-830 user journey instead of starting "
        "from the Search field. "
        f"{rerun_summary}"
    )


if __name__ == "__main__":
    main()
