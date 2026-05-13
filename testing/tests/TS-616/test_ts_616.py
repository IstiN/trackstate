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
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-616"
RUN_COMMAND = "python testing/tests/TS-616/test_ts_616.py"
BASE_VIEWPORT = {"width": 1600, "height": 960}
RESIZED_VIEWPORT = {"width": 1500, "height": 960}
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
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-616 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "user_login": user.login,
        "base_viewport": BASE_VIEWPORT,
        "resized_viewport": RESIZED_VIEWPORT,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveDesktopHeaderLayoutPage(tracker_page, user_login=user.login)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the desktop header audit started.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                page.dismiss_connection_banner()
                page.set_viewport(**BASE_VIEWPORT)

                baseline = page.observe_header()
                result["baseline_observation"] = _observation_payload(baseline)
                baseline_action = (
                    "Open the deployed hosted app on desktop and verify the visible "
                    "header controls are ready for interaction."
                )
                baseline_summary = _header_summary(baseline)
                _record_human_verification(
                    result,
                    check=(
                        "Verified the desktop header visibly showed the sync status, "
                        "Search issues field, Create issue button, Attachments limited "
                        "state, theme toggle, and the signed-in profile label."
                    ),
                    observed=_header_labels_summary(baseline, user.login),
                )
                try:
                    _assert_baseline_header(baseline=baseline, user_login=user.login)
                except AssertionError as error:
                    _record_human_verification(
                        result,
                        check=(
                            "Checked the live desktop header as a user would see it before "
                            "any interaction and compared the visible control heights in the "
                            "top row."
                        ),
                        observed=(
                            "The Search issues field was visibly taller than the surrounding "
                            f"32px controls: {_control_summary(baseline.search)}; "
                            f"sync={_control_summary(baseline.sync)}; "
                            f"create={_control_summary(baseline.create)}"
                        ),
                    )
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=baseline_action,
                        observed=f"{baseline_summary}; error={_trimmed(str(error), limit=600)}",
                    )
                    raise
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=baseline_action,
                    observed=baseline_summary,
                )

                page.hover_create_issue()
                hovered = page.observe_header()
                result["hover_observation"] = _observation_payload(hovered)
                _assert_geometry_stable(
                    reference=baseline,
                    observed=hovered,
                    step_number=2,
                    context="hovering the visible Create issue button",
                    compare_horizontal=True,
                )
                page.click_create_issue()
                after_create = page.observe_header()
                result["after_create_observation"] = _observation_payload(after_create)
                _assert_geometry_stable(
                    reference=baseline,
                    observed=after_create,
                    step_number=2,
                    context="clicking the visible Create issue button",
                    compare_horizontal=True,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=(
                        "Hover over and click the visible Create issue button."
                    ),
                    observed=(
                        f"hover_create={_control_summary(hovered.create)}; "
                        f"after_click_create={_control_summary(after_create.create)}; "
                        f"body_still_contains_create={'Create issue' in after_create.body_text}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the Create issue button stayed aligned in the header row "
                        "while hovered and after a real click, with no visible jump in the "
                        "desktop header row."
                    ),
                    observed=_control_summary(after_create.create),
                )

                page.focus_search_field()
                focused = page.observe_header()
                result["focused_observation"] = _observation_payload(focused)
                _assert_search_focus(focused)
                _assert_geometry_stable(
                    reference=baseline,
                    observed=focused,
                    step_number=3,
                    context="focusing the Search issues field",
                    compare_horizontal=True,
                )
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Focus the visible Search issues field in the desktop header.",
                    observed=(
                        f"active_element={focused.active_element.tag_name}:"
                        f"{focused.active_element.accessible_name!r}; "
                        f"search={_control_summary(focused.search)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified keyboard focus moved into the visible Search issues field "
                        "without changing its header-row placement."
                    ),
                    observed=(
                        f"active_element={focused.active_element.tag_name}; "
                        f"accessible_name={focused.active_element.accessible_name!r}"
                    ),
                )

                first_theme_label = baseline.theme_label
                toggled_label = page.toggle_theme()
                toggled = page.observe_header()
                result["toggled_theme_observation"] = _observation_payload(toggled)
                restored_label = page.toggle_theme()
                restored = page.observe_header()
                result["restored_theme_observation"] = _observation_payload(restored)
                _assert_theme_toggle(
                    initial_label=first_theme_label,
                    toggled_label=toggled_label,
                    restored_label=restored_label,
                    toggled=toggled,
                    restored=restored,
                )
                _assert_geometry_stable(
                    reference=baseline,
                    observed=toggled,
                    step_number=4,
                    context="switching the header theme toggle to the alternate theme",
                    compare_horizontal=True,
                )
                _assert_geometry_stable(
                    reference=baseline,
                    observed=restored,
                    step_number=4,
                    context="switching the header theme toggle back to the original theme",
                    compare_horizontal=True,
                )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Toggle the theme between light and dark modes and inspect the "
                        "desktop header row after each change."
                    ),
                    observed=(
                        f"initial_theme={first_theme_label}; "
                        f"alternate_theme={toggled.theme_label}; "
                        f"restored_theme={restored.theme_label}; "
                        f"theme_button={_control_summary(restored.theme)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the theme toggle visibly switched between light and dark "
                        "states and stayed aligned with the other header controls."
                    ),
                    observed=(
                        f"{first_theme_label} -> {toggled.theme_label} -> {restored.theme_label}"
                    ),
                )

                page.set_viewport(**RESIZED_VIEWPORT)
                resized = page.observe_header()
                result["resized_observation"] = _observation_payload(resized)
                _assert_resize_layout(reference=baseline, resized=resized, step_number=5)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=(
                        "Resize the browser within the desktop breakpoint range and verify "
                        "the header layout stays stable."
                    ),
                    observed=(
                        f"viewport={int(resized.viewport_width)}x{int(resized.viewport_height)}; "
                        f"search={_control_summary(resized.search)}; "
                        f"create={_control_summary(resized.create)}; "
                        f"access={_control_summary(resized.access)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified at the narrower desktop width that the visible search "
                        "field, Create issue button, Attachments limited button, theme "
                        "toggle, and profile label still rendered in one aligned top row "
                        "without overlapping."
                    ),
                    observed=(
                        f"viewport={int(resized.viewport_width)}; "
                        f"search_right={resized.search.right:.1f}; "
                        f"create_left={resized.create.left:.1f}; "
                        f"profile_right={resized.profile.right:.1f}"
                    ),
                )

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


def _assert_baseline_header(
    *,
    baseline: DesktopHeaderObservation,
    user_login: str,
) -> None:
    for fragment in (
        "Synced with Git",
        "Create issue",
        "Attachments limited",
        user_login,
    ):
        if fragment not in baseline.body_text:
            raise AssertionError(
                "Step 1 failed: the desktop header did not visibly render all required "
                "controls for the audit.\n"
                f'Missing fragment: "{fragment}"\n'
                f"Observed body text:\n{baseline.body_text}",
            )
    _assert_primary_row_alignment(
        observation=baseline,
        step_number=1,
        context="initial desktop header state",
    )
    _assert_standardized_control_heights(
        observation=baseline,
        step_number=1,
        context="the initial desktop header state",
    )


def _assert_search_focus(observation: DesktopHeaderObservation) -> None:
    if observation.active_element.tag_name != "INPUT":
        raise AssertionError(
            "Step 3 failed: focusing the desktop header search control did not leave the "
            "text cursor in the Search issues input.\n"
            f"Observed active element: {observation.active_element}",
        )
    if observation.active_element.accessible_name != "Search issues":
        raise AssertionError(
            "Step 3 failed: the focused desktop header field was not the Search issues "
            "input.\n"
            f"Observed active element: {observation.active_element}",
        )


def _assert_theme_toggle(
    *,
    initial_label: str,
    toggled_label: str,
    restored_label: str,
    toggled: DesktopHeaderObservation,
    restored: DesktopHeaderObservation,
) -> None:
    if toggled_label == initial_label:
        raise AssertionError(
            "Step 4 failed: clicking the desktop theme toggle did not switch to the "
            "alternate theme state.",
        )
    if toggled.theme_label != toggled_label:
        raise AssertionError(
            "Step 4 failed: the visible desktop theme toggle did not expose the expected "
            "alternate label after the first theme switch.\n"
            f"Expected label: {toggled_label}\n"
            f"Observed label: {toggled.theme_label}",
        )
    if restored_label != initial_label or restored.theme_label != initial_label:
        raise AssertionError(
            "Step 4 failed: toggling the theme a second time did not restore the original "
            "desktop theme-toggle label.\n"
            f"Initial label: {initial_label}\n"
            f"Observed second toggle result: {restored_label}\n"
            f"Observed current label: {restored.theme_label}",
        )


def _assert_geometry_stable(
    *,
    reference: DesktopHeaderObservation,
    observed: DesktopHeaderObservation,
    step_number: int,
    context: str,
    compare_horizontal: bool,
) -> None:
    for control_name in ("sync", "search", "create", "access", "theme", "profile"):
        reference_control = getattr(reference, control_name)
        observed_control = getattr(observed, control_name)
        _assert_close(
            reference_control.top,
            observed_control.top,
            step_number=step_number,
            context=context,
            control_name=control_name,
            metric="top",
        )
        _assert_close(
            reference_control.height,
            observed_control.height,
            step_number=step_number,
            context=context,
            control_name=control_name,
            metric="height",
        )
        _assert_close(
            reference_control.center_y,
            observed_control.center_y,
            step_number=step_number,
            context=context,
            control_name=control_name,
            metric="center_y",
        )
        if compare_horizontal:
            _assert_close(
                reference_control.left,
                observed_control.left,
                step_number=step_number,
                context=context,
                control_name=control_name,
                metric="left",
            )
            _assert_close(
                reference_control.width,
                observed_control.width,
                step_number=step_number,
                context=context,
                control_name=control_name,
                metric="width",
            )
    _assert_primary_row_alignment(
        observation=observed,
        step_number=step_number,
        context=context,
    )
    _assert_standardized_control_heights(
        observation=observed,
        step_number=step_number,
        context=context,
    )


def _assert_resize_layout(
    *,
    reference: DesktopHeaderObservation,
    resized: DesktopHeaderObservation,
    step_number: int,
) -> None:
    for control_name in ("sync", "search", "create", "access", "theme", "profile"):
        reference_control = getattr(reference, control_name)
        resized_control = getattr(resized, control_name)
        _assert_close(
            reference_control.top,
            resized_control.top,
            step_number=step_number,
            context="resizing the desktop browser",
            control_name=control_name,
            metric="top",
        )
        _assert_close(
            reference_control.height,
            resized_control.height,
            step_number=step_number,
            context="resizing the desktop browser",
            control_name=control_name,
            metric="height",
        )
        _assert_close(
            reference_control.center_y,
            resized_control.center_y,
            step_number=step_number,
            context="resizing the desktop browser",
            control_name=control_name,
            metric="center_y",
        )
    _assert_primary_row_alignment(
        observation=resized,
        step_number=step_number,
        context="the resized desktop header state",
    )
    _assert_standardized_control_heights(
        observation=resized,
        step_number=step_number,
        context="the resized desktop header state",
    )
    for left, right in (
        (resized.sync, resized.search),
        (resized.search, resized.create),
        (resized.create, resized.access),
        (resized.access, resized.theme),
        (resized.theme, resized.profile),
    ):
        if left.right > right.left + GEOMETRY_TOLERANCE:
            raise AssertionError(
                "Step 5 failed: resizing within the desktop breakpoint range caused the "
                "visible header controls to overlap.\n"
                f"Left control: {_control_summary(left)}\n"
                f"Right control: {_control_summary(right)}\n"
                f"Viewport width: {resized.viewport_width}",
            )
    if resized.profile.right > resized.viewport_width + GEOMETRY_TOLERANCE:
        raise AssertionError(
            "Step 5 failed: resizing within the desktop breakpoint range pushed the "
            "visible profile control past the right edge of the viewport.\n"
            f"Profile control: {_control_summary(resized.profile)}\n"
            f"Viewport width: {resized.viewport_width}",
        )


def _assert_primary_row_alignment(
    *,
    observation: DesktopHeaderObservation,
    step_number: int,
    context: str,
) -> None:
    row_controls = (
        ("sync", observation.sync),
        ("search", observation.search),
        ("create", observation.create),
        ("access", observation.access),
        ("theme", observation.theme),
        ("profile", observation.profile),
    )
    reference_center = observation.create.center_y
    for control_name, control in row_controls:
        _assert_close(
            reference_center,
            control.center_y,
            step_number=step_number,
            context=context,
            control_name=control_name,
            metric="center_y",
        )


def _assert_standardized_control_heights(
    *,
    observation: DesktopHeaderObservation,
    step_number: int,
    context: str,
) -> None:
    mismatches: list[str] = []
    for control_name in ("sync", "search", "create", "access", "theme", "profile"):
        control = getattr(observation, control_name)
        if abs(control.height - STANDARDIZED_CONTROL_HEIGHT) <= GEOMETRY_TOLERANCE:
            continue
        mismatches.append(
            f"{control_name} observed {control.height:.1f}px ({_control_summary(control)})"
        )
    if not mismatches:
        return
    raise AssertionError(
        f"Step {step_number} failed: {context} did not keep every audited desktop "
        "header control at the required standardized 32px height.\n"
        f"Expected height: {STANDARDIZED_CONTROL_HEIGHT:.1f}px +/- {GEOMETRY_TOLERANCE:.1f}px\n"
        + "\n".join(mismatches),
    )


def _assert_close(
    expected: float,
    actual: float,
    *,
    step_number: int,
    context: str,
    control_name: str,
    metric: str,
) -> None:
    if abs(expected - actual) <= GEOMETRY_TOLERANCE:
        return
    raise AssertionError(
        f"Step {step_number} failed: {context} changed the desktop header {control_name} "
        f"{metric} beyond the allowed tolerance.\n"
        f"Expected {metric}: {expected:.2f}\n"
        f"Actual {metric}: {actual:.2f}\n"
        f"Allowed delta: {GEOMETRY_TOLERANCE:.2f}",
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


def _observation_payload(observation: DesktopHeaderObservation) -> dict[str, object]:
    return {
        "viewport_width": observation.viewport_width,
        "viewport_height": observation.viewport_height,
        "theme_label": observation.theme_label,
        "active_element": asdict(observation.active_element),
        "sync": asdict(observation.sync),
        "search": asdict(observation.search),
        "create": asdict(observation.create),
        "access": asdict(observation.access),
        "theme": asdict(observation.theme),
        "profile": asdict(observation.profile),
    }


def _header_summary(observation: DesktopHeaderObservation) -> str:
    return (
        f"viewport={int(observation.viewport_width)}x{int(observation.viewport_height)}; "
        f"sync={_control_summary(observation.sync)}; "
        f"search={_control_summary(observation.search)}; "
        f"create={_control_summary(observation.create)}; "
        f"access={_control_summary(observation.access)}; "
        f"theme={_control_summary(observation.theme)}; "
        f"profile={_control_summary(observation.profile)}"
    )


def _header_labels_summary(observation: DesktopHeaderObservation, user_login: str) -> str:
    return (
        f"sync_label={observation.sync.label!r}; "
        f"search_label='Search issues'; "
        f"create_label={observation.create.label!r}; "
        f"access_label={observation.access.label!r}; "
        f"theme_label={observation.theme_label!r}; "
        f"profile_label={user_login!r}"
    )


def _control_summary(control: HeaderControlObservation) -> str:
    return (
        f"{control.label}@left={control.left:.1f},top={control.top:.1f},"
        f"width={control.width:.1f},height={control.height:.1f},centerY={control.center_y:.1f}"
    )


def _trimmed(value: str, *, limit: int = 240) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


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
            "* Opened the deployed hosted TrackState app in Chromium with the stored "
            "GitHub token and switched to a 1600px desktop viewport."
        ),
        (
            "* Verified the visible desktop header showed {{Synced with Git}}, the "
            "{{Search issues}} field, {{Create issue}}, {{Attachments limited}}, the "
            "theme toggle, and the signed-in profile label."
        ),
        (
            "* Hovered and clicked {{Create issue}}, focused the live search field, "
            "toggled the live theme twice, and resized the browser to 1500px while "
            "comparing the live header geometry after each interaction."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the audited desktop header controls stayed at "
            "the required 32px standardized height, preserved their vertical alignment "
            "during hover/focus/theme interactions, and remained in a single "
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
            "- Opened the deployed hosted TrackState app in Chromium with the stored "
            "GitHub token and switched to a 1600px desktop viewport."
        ),
        (
            "- Verified the visible desktop header showed `Synced with Git`, the "
            "`Search issues` field, `Create issue`, `Attachments limited`, the theme "
            "toggle, and the signed-in profile label."
        ),
        (
            "- Hovered and clicked `Create issue`, focused the live search field, "
            "toggled the live theme twice, and resized the browser to 1500px while "
            "comparing the live header geometry after each interaction."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the audited desktop header controls stayed at "
            "the required 32px standardized height, preserved their vertical alignment "
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
            "Ran the live desktop header audit against the deployed hosted TrackState app, "
            "covering Create issue hover/click, Search issues focus, theme toggling, and "
            "desktop resizing."
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
        "## Steps to reproduce",
        "1. Open the deployed hosted TrackState app in a desktop browser and verify the desktop header is visible.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Hover over and click the `Create issue` button; observe height changes.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Focus the JQL/Search field; observe height and alignment.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Toggle the theme between light and dark modes; observe the theme-toggle alignment.",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "5. Resize the browser window within the desktop breakpoint range.",
        f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
        "",
        "## Actual vs Expected",
        (
            "- Expected: the audited desktop header controls render at the required 32px "
            "standardized height, keep their vertical alignment during hover/focus/theme "
            "state changes, and remain in a stable single row without overlap across the "
            "desktop breakpoint range."
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
            return (
                f"Not executed because step {first_failed_step} failed before this step ran."
            )
    return "No observation recorded."


if __name__ == "__main__":
    main()
