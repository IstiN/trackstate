from __future__ import annotations

import json
import platform
import sys
import traceback
from dataclasses import asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_desktop_header_layout_page import (  # noqa: E402
    DesktopHeaderObservation,
    HeaderControlObservation,
    LiveDesktopHeaderLayoutPage,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402

TICKET_KEY = "TS-616"
RUN_COMMAND = "python testing/tests/TS-616/test_ts_616.py"
BASE_VIEWPORT = {"width": 1440, "height": 900}
RESIZED_VIEWPORT = {"width": 1280, "height": 900}
GEOMETRY_TOLERANCE = 1.0
STANDARDIZED_CONTROL_HEIGHT = 32.0
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts616_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts616_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": config.repository,
        "repository_ref": config.ref,
        "browser": "Chromium via Playwright",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "base_viewport": BASE_VIEWPORT,
        "resized_viewport": RESIZED_VIEWPORT,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(config) as tracker_page:
            page = LiveDesktopHeaderLayoutPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the hosted "
                        "tracker shell before the desktop header audit started.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                dashboard = page.open_dashboard()
                result["dashboard_observation"] = asdict(dashboard)
                page.set_viewport(**BASE_VIEWPORT)

                baseline = page.observe_header()
                result["baseline_observation"] = _observation_payload(baseline)
                _record_human_verification(
                    result,
                    check=(
                        "Verified the desktop Dashboard header visibly showed the sync status, "
                        "Create issue action, workspace switcher, Search issues field, and "
                        "theme toggle in one top row."
                    ),
                    observed=_header_labels_summary(baseline),
                )

                failures: list[str] = []

                step_one_errors = _baseline_expectation_errors(
                    baseline=baseline,
                    expected_body_fragments=("Dashboard", "Open Issues", "Team Velocity"),
                )
                page.hover_create_issue()
                hovered = page.observe_header()
                result["hover_observation"] = _observation_payload(hovered)
                step_one_errors.extend(
                    _geometry_stability_errors(
                        reference=baseline,
                        observed=hovered,
                        step_number=1,
                        context="hovering the visible Create issue button",
                        compare_horizontal=True,
                    ),
                )
                page.click_create_issue()
                after_create = page.observe_header()
                result["after_create_observation"] = _observation_payload(after_create)
                page.dismiss_create_issue_dialog()
                step_one_errors.extend(
                    _geometry_stability_errors(
                        reference=baseline,
                        observed=after_create,
                        step_number=1,
                        context="clicking the visible Create issue button",
                        compare_horizontal=True,
                    ),
                )
                _record_step(
                    result,
                    step=1,
                    status="passed" if not step_one_errors else "failed",
                    action="Hover over and click the `Create issue` button; observe height changes.",
                    observed=(
                        f"baseline={_header_summary(baseline)}; "
                        f"hover_create={_control_summary(hovered.create)}; "
                        f"after_click_create={_control_summary(after_create.create)}"
                        if not step_one_errors
                        else "\n".join(step_one_errors)
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Create issue action stayed aligned in the desktop "
                        "header during hover and after a real click."
                    ),
                    observed=(
                        f"baseline={_control_summary(baseline.create)}; "
                        f"hover={_control_summary(hovered.create)}; "
                        f"after_click={_control_summary(after_create.create)}"
                    ),
                )
                failures.extend(step_one_errors)

                page.focus_search_field()
                focused = page.observe_header()
                result["focused_observation"] = _observation_payload(focused)
                step_two_errors = _search_focus_errors(focused)
                step_two_errors.extend(
                    _geometry_stability_errors(
                        reference=baseline,
                        observed=focused,
                        step_number=2,
                        context="focusing the Search issues field",
                        compare_horizontal=True,
                    ),
                )
                _record_step(
                    result,
                    step=2,
                    status="passed" if not step_two_errors else "failed",
                    action="Focus the JQL search field; observe height and alignment.",
                    observed=(
                        f"active_element={focused.active_element.tag_name}:"
                        f"{focused.active_element.accessible_name!r}; "
                        f"search={_control_summary(focused.search)}"
                        if not step_two_errors
                        else "\n".join(step_two_errors)
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified keyboard focus moved into the visible Search issues field "
                        "without shifting the desktop header row."
                    ),
                    observed=(
                        f"active_element={focused.active_element.tag_name}; "
                        f"accessible_name={focused.active_element.accessible_name!r}; "
                        f"search_wrapper={_control_summary(focused.search)}"
                    ),
                )
                failures.extend(step_two_errors)

                first_theme_label = baseline.theme_label
                toggled_label = page.toggle_theme()
                toggled = page.observe_header()
                result["toggled_theme_observation"] = _observation_payload(toggled)
                restored_label = page.toggle_theme()
                restored = page.observe_header()
                result["restored_theme_observation"] = _observation_payload(restored)
                step_three_errors = _theme_toggle_errors(
                    initial_label=first_theme_label,
                    toggled_label=toggled_label,
                    restored_label=restored_label,
                )
                step_three_errors.extend(
                    _geometry_stability_errors(
                        reference=baseline,
                        observed=toggled,
                        step_number=3,
                        context="switching the header theme toggle to the alternate theme",
                        compare_horizontal=True,
                    ),
                )
                step_three_errors.extend(
                    _geometry_stability_errors(
                        reference=baseline,
                        observed=restored,
                        step_number=3,
                        context="switching the header theme toggle back to the original theme",
                        compare_horizontal=True,
                    ),
                )
                _record_step(
                    result,
                    step=3,
                    status="passed" if not step_three_errors else "failed",
                    action=(
                        "Toggle the theme between light and dark modes; observe the theme "
                        "toggle alignment."
                    ),
                    observed=(
                        f"initial_theme={first_theme_label}; "
                        f"alternate_theme={toggled_label}; "
                        f"restored_theme={restored_label}; "
                        f"theme_button={_control_summary(restored.theme)}"
                        if not step_three_errors
                        else "\n".join(step_three_errors)
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible theme toggle switched between dark and light "
                        "states and stayed centered with the other header controls."
                    ),
                    observed=(
                        f"{first_theme_label} -> {toggled_label} -> {restored_label}; "
                        f"theme={_control_summary(restored.theme)}"
                    ),
                )
                failures.extend(step_three_errors)

                page.set_viewport(**RESIZED_VIEWPORT)
                resized = page.observe_header()
                result["resized_observation"] = _observation_payload(resized)
                step_four_errors = _resize_layout_errors(
                    reference=baseline,
                    resized=resized,
                    step_number=4,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed" if not step_four_errors else "failed",
                    action="Resize the browser window within the desktop breakpoint range.",
                    observed=(
                        f"viewport={int(resized.viewport_width)}x{int(resized.viewport_height)}; "
                        f"sync={_control_summary(resized.sync)}; "
                        f"create={_control_summary(resized.create)}; "
                        f"workspace={_control_summary(resized.workspace)}; "
                        f"search={_control_summary(resized.search)}; "
                        f"theme={_control_summary(resized.theme)}"
                        if not step_four_errors
                        else "\n".join(step_four_errors)
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified at a narrower desktop width that the sync pill, Create "
                        "issue action, workspace switcher, Search issues field, and theme "
                        "toggle still rendered in one aligned row without overlap."
                    ),
                    observed=(
                        f"viewport={int(resized.viewport_width)}x{int(resized.viewport_height)}; "
                        f"create_right={resized.create.right:.1f}; "
                        f"workspace_left={resized.workspace.left:.1f}; "
                        f"search_right={resized.search.right:.1f}; "
                        f"theme_left={resized.theme.left:.1f}"
                    ),
                )
                failures.extend(step_four_errors)

                if failures:
                    page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                    result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                    raise AssertionError("\n\n".join(failures))

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                if "screenshot" not in result:
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


def _baseline_expectation_errors(
    *,
    baseline: DesktopHeaderObservation,
    expected_body_fragments: tuple[str, ...],
) -> list[str]:
    errors: list[str] = []
    for fragment in expected_body_fragments:
        if fragment in baseline.body_text:
            continue
        errors.append(
            "Step 1 failed: the desktop app did not stay on a readable Dashboard view "
            "before the interactive-state audit.\n"
            f'Missing fragment: "{fragment}"\n'
            f"Observed body text:\n{baseline.body_text}"
        )
    errors.extend(
        _standardized_control_height_errors(
            observation=baseline,
            step_number=1,
            context="the baseline desktop header state",
        ),
    )
    errors.extend(
        _primary_row_alignment_errors(
            observation=baseline,
            step_number=1,
            context="the baseline desktop header state",
        ),
    )
    return errors


def _search_focus_errors(observation: DesktopHeaderObservation) -> list[str]:
    errors: list[str] = []
    if observation.active_element.tag_name != "INPUT":
        errors.append(
            "Step 2 failed: focusing the desktop header search control did not leave the "
            "text cursor in the Search issues input.\n"
            f"Observed active element: {observation.active_element}"
        )
    if observation.active_element.accessible_name not in {"Search issues", "Search", "JQL Search"}:
        errors.append(
            "Step 2 failed: the focused desktop header field was not the Search issues "
            "input.\n"
            f"Observed active element: {observation.active_element}"
        )
    return errors


def _theme_toggle_errors(
    *,
    initial_label: str,
    toggled_label: str,
    restored_label: str,
) -> list[str]:
    errors: list[str] = []
    if toggled_label == initial_label:
        errors.append(
            "Step 3 failed: clicking the desktop theme toggle did not switch to the "
            "alternate theme state."
        )
    if restored_label != initial_label:
        errors.append(
            "Step 3 failed: toggling the theme a second time did not restore the original "
            "desktop theme-toggle label.\n"
            f"Initial label: {initial_label}\n"
            f"Observed restored label: {restored_label}"
        )
    return errors


def _geometry_stability_errors(
    *,
    reference: DesktopHeaderObservation,
    observed: DesktopHeaderObservation,
    step_number: int,
    context: str,
    compare_horizontal: bool,
) -> list[str]:
    errors: list[str] = []
    for control_name in ("sync", "create", "workspace", "search", "theme"):
        reference_control = getattr(reference, control_name)
        observed_control = getattr(observed, control_name)
        errors.extend(
            _close_errors(
                reference_control.top,
                observed_control.top,
                step_number=step_number,
                context=context,
                control_name=control_name,
                metric="top",
            ),
        )
        errors.extend(
            _close_errors(
                reference_control.height,
                observed_control.height,
                step_number=step_number,
                context=context,
                control_name=control_name,
                metric="height",
            ),
        )
        errors.extend(
            _close_errors(
                reference_control.center_y,
                observed_control.center_y,
                step_number=step_number,
                context=context,
                control_name=control_name,
                metric="center_y",
            ),
        )
        if compare_horizontal:
            errors.extend(
                _close_errors(
                    reference_control.left,
                    observed_control.left,
                    step_number=step_number,
                    context=context,
                    control_name=control_name,
                    metric="left",
                ),
            )
            errors.extend(
                _close_errors(
                    reference_control.width,
                    observed_control.width,
                    step_number=step_number,
                    context=context,
                    control_name=control_name,
                    metric="width",
                ),
            )
    errors.extend(
        _primary_row_alignment_errors(
            observation=observed,
            step_number=step_number,
            context=context,
        ),
    )
    errors.extend(
        _standardized_control_height_errors(
            observation=observed,
            step_number=step_number,
            context=context,
        ),
    )
    return errors


def _resize_layout_errors(
    *,
    reference: DesktopHeaderObservation,
    resized: DesktopHeaderObservation,
    step_number: int,
) -> list[str]:
    errors: list[str] = []
    for control_name in ("sync", "create", "workspace", "search", "theme"):
        reference_control = getattr(reference, control_name)
        resized_control = getattr(resized, control_name)
        errors.extend(
            _close_errors(
                reference_control.top,
                resized_control.top,
                step_number=step_number,
                context="resizing the desktop browser",
                control_name=control_name,
                metric="top",
            ),
        )
        errors.extend(
            _close_errors(
                reference_control.height,
                resized_control.height,
                step_number=step_number,
                context="resizing the desktop browser",
                control_name=control_name,
                metric="height",
            ),
        )
        errors.extend(
            _close_errors(
                reference_control.center_y,
                resized_control.center_y,
                step_number=step_number,
                context="resizing the desktop browser",
                control_name=control_name,
                metric="center_y",
            ),
        )
    errors.extend(
        _primary_row_alignment_errors(
            observation=resized,
            step_number=step_number,
            context="the resized desktop header state",
        ),
    )
    errors.extend(
        _standardized_control_height_errors(
            observation=resized,
            step_number=step_number,
            context="the resized desktop header state",
        ),
    )
    for left, right in (
        (resized.sync, resized.create),
        (resized.create, resized.workspace),
        (resized.workspace, resized.search),
        (resized.search, resized.theme),
    ):
        if left.right <= right.left + GEOMETRY_TOLERANCE:
            continue
        errors.append(
            "Step 4 failed: resizing within the desktop breakpoint range caused the "
            "visible header controls to overlap.\n"
            f"Left control: {_control_summary(left)}\n"
            f"Right control: {_control_summary(right)}\n"
            f"Viewport width: {resized.viewport_width}"
        )
    if resized.theme.right <= resized.viewport_width + GEOMETRY_TOLERANCE:
        return errors
    errors.append(
        "Step 4 failed: resizing within the desktop breakpoint range pushed the "
        "visible theme toggle past the right edge of the viewport.\n"
        f"Theme control: {_control_summary(resized.theme)}\n"
        f"Viewport width: {resized.viewport_width}"
    )
    return errors


def _primary_row_alignment_errors(
    *,
    observation: DesktopHeaderObservation,
    step_number: int,
    context: str,
) -> list[str]:
    errors: list[str] = []
    reference_center = observation.create.center_y
    for control_name in ("sync", "create", "workspace", "search", "theme"):
        control = getattr(observation, control_name)
        errors.extend(
            _close_errors(
                reference_center,
                control.center_y,
                step_number=step_number,
                context=context,
                control_name=control_name,
                metric="center_y",
            ),
        )
    return errors


def _standardized_control_height_errors(
    *,
    observation: DesktopHeaderObservation,
    step_number: int,
    context: str,
) -> list[str]:
    mismatches: list[str] = []
    for control_name in ("sync", "create", "workspace", "search", "theme"):
        control = getattr(observation, control_name)
        if abs(control.height - STANDARDIZED_CONTROL_HEIGHT) <= GEOMETRY_TOLERANCE:
            continue
        mismatches.append(
            f"{control_name} observed {control.height:.1f}px ({_control_summary(control)})"
        )
    if not mismatches:
        return []
    return [
        f"Step {step_number} failed: {context} did not keep every audited desktop "
        "header control at the required standardized 32px height.\n"
        f"Expected height: {STANDARDIZED_CONTROL_HEIGHT:.1f}px +/- {GEOMETRY_TOLERANCE:.1f}px\n"
        + "\n".join(mismatches)
    ]


def _close_errors(
    expected: float,
    actual: float,
    *,
    step_number: int,
    context: str,
    control_name: str,
    metric: str,
) -> list[str]:
    if abs(expected - actual) <= GEOMETRY_TOLERANCE:
        return []
    return [
        f"Step {step_number} failed: {context} changed the desktop header {control_name} "
        f"{metric} beyond the allowed tolerance.\n"
        f"Expected {metric}: {expected:.2f}\n"
        f"Actual {metric}: {actual:.2f}\n"
        f"Allowed delta: {GEOMETRY_TOLERANCE:.2f}"
    ]


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


def _observation_payload(observation: DesktopHeaderObservation) -> dict[str, object]:
    return {
        "viewport_width": observation.viewport_width,
        "viewport_height": observation.viewport_height,
        "theme_label": observation.theme_label,
        "active_element": asdict(observation.active_element),
        "sync": asdict(observation.sync),
        "create": asdict(observation.create),
        "workspace": asdict(observation.workspace),
        "search": asdict(observation.search),
        "search_input": asdict(observation.search_input),
        "theme": asdict(observation.theme),
    }


def _header_summary(observation: DesktopHeaderObservation) -> str:
    return (
        f"viewport={int(observation.viewport_width)}x{int(observation.viewport_height)}; "
        f"sync={_control_summary(observation.sync)}; "
        f"create={_control_summary(observation.create)}; "
        f"workspace={_control_summary(observation.workspace)}; "
        f"search={_control_summary(observation.search)}; "
        f"theme={_control_summary(observation.theme)}"
    )


def _header_labels_summary(observation: DesktopHeaderObservation) -> str:
    return (
        f"sync_label={observation.sync.label!r}; "
        f"create_label={observation.create.label!r}; "
        f"workspace_label={observation.workspace.label!r}; "
        f"search_label={observation.search.label!r}; "
        f"theme_label={observation.theme_label!r}"
    )


def _control_summary(control: HeaderControlObservation) -> str:
    return (
        f"{control.label}@left={control.left:.1f},top={control.top:.1f},"
        f"width={control.width:.1f},height={control.height:.1f},centerY={control.center_y:.1f}"
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
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: unknown failure"))
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
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            "* Opened the deployed hosted TrackState app in Chromium, navigated to "
            "{{Dashboard}}, and set the browser to a {{1440x900}} desktop viewport."
        ),
        (
            "* Audited the visible desktop header controls shown in the live app: the "
            "sync status pill, {{Create issue}}, the workspace switcher, the visible "
            "{{Search issues}} field wrapper, and the theme toggle."
        ),
        (
            "* Hovered and clicked {{Create issue}}, focused the search field, toggled "
            "the live theme between dark and light, and resized the browser to "
            "{{1280x900}} while comparing the live header geometry after each step."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the audited desktop header controls stayed at "
            "the required {{32px}} standardized height, preserved their vertical "
            "alignment through hover/focus/theme interactions, and remained in a single "
            "non-overlapping row after the desktop resize."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Run command: {{{{{RUN_COMMAND}}}}}",
        f"* Screenshot: {{{{{screenshot_path}}}}}",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        (
            "- Opened the deployed hosted TrackState app in Chromium, navigated to "
            "`Dashboard`, and set the browser to a `1440x900` desktop viewport."
        ),
        (
            "- Audited the visible desktop header controls shown in the live app: the "
            "sync status pill, `Create issue`, the workspace switcher, the visible "
            "`Search issues` field wrapper, and the theme toggle."
        ),
        (
            "- Hovered and clicked `Create issue`, focused the search field, toggled the "
            "live theme between dark and light, and resized the browser to `1280x900` "
            "while comparing the live header geometry after each step."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the audited desktop header controls stayed at "
            "the required `32px` standardized height, preserved their vertical alignment "
            "during hover/focus/theme interactions, and remained in a single "
            "non-overlapping row after the desktop resize."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Run command: `{RUN_COMMAND}`",
        f"- Screenshot: `{screenshot_path}`",
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            "Ran the live desktop header audit against the deployed hosted TrackState app "
            "on Dashboard, covering Create issue hover/click, Search issues focus, theme "
            "toggling, and desktop resizing."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        (
            f"- Environment: `{result['app_url']}` on Chromium/Playwright "
            f"({platform.system()})"
        ),
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
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} - Desktop header layout audit regression",
        "",
        "## Preconditions",
        (
            f"- Open the deployed hosted TrackState app at `{result['app_url']}` in a "
            "desktop Chromium browser and navigate to `Dashboard`."
        ),
        f"- Base viewport: `{BASE_VIEWPORT['width']}x{BASE_VIEWPORT['height']}`",
        "",
        "## Steps to reproduce",
        "1. Hover over and click the `Create issue` button; observe height changes.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Focus the JQL search field; observe height and alignment.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Toggle the theme between light and dark modes; observe the theme-toggle alignment.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Resize the browser window within the desktop breakpoint range.",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "",
        "## Actual vs Expected",
        (
            "- Expected: the visible desktop header controls keep their required `32px` "
            "standardized height and centered vertical alignment through hover, focus, "
            "theme-toggle, and resize interactions, while remaining in a single stable row."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the desktop header changed geometry or alignment during the audited interaction."
            )
        ),
        "",
        "## Exact error message",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
        "",
        "## Environment",
        f"- URL: `{result['app_url']}`",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        f"- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        f"- Run command: `{RUN_COMMAND}`",
        f"- Base viewport: `{BASE_VIEWPORT['width']}x{BASE_VIEWPORT['height']}`",
        f"- Resized viewport: `{RESIZED_VIEWPORT['width']}x{RESIZED_VIEWPORT['height']}`",
        "",
        "## Screenshot / logs",
        f"- Screenshot: `{screenshot_path}`",
        "- Relevant log excerpt:",
        "```text",
        str(result.get("error", "")),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        marker = "PASS" if step.get("status") == "passed" else "FAIL"
        if jira:
            lines.append(
                f"* Step {step.get('step')} - *{marker}* - {step.get('action')}\n"
                f"** Observed: {step.get('observed')}"
            )
        else:
            lines.append(
                f"- Step {step.get('step')} - **{marker}** - {step.get('action')}\n"
                f"  - Observed: {step.get('observed')}"
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in result.get("human_verification", []):
        if not isinstance(item, dict):
            continue
        if jira:
            lines.append(
                f"* {item.get('check')}\n** Observed: {item.get('observed')}"
            )
        else:
            lines.append(
                f"- {item.get('check')}\n  - Observed: {item.get('observed')}"
            )
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("observed", "No observation recorded."))
    failed_steps = [
        int(step.get("step"))
        for step in result.get("steps", [])
        if isinstance(step, dict)
        and step.get("status") == "failed"
        and isinstance(step.get("step"), int)
    ]
    if failed_steps:
        first_failed_step = min(failed_steps)
        if step_number > first_failed_step:
            return f"Not executed because step {first_failed_step} failed before this step ran."
    return "No observation recorded."


if __name__ == "__main__":
    main()
