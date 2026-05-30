from __future__ import annotations

import json
import os
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_multi_view_refresh_page import (  # noqa: E402
    EditSurfaceObservation,
    LiveMultiViewRefreshPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import (  # noqa: E402
    load_live_setup_test_config,
)
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    build_annotated_steps,
    format_step_lines,
    write_test_automation_result,
)

TICKET_KEY = "TS-396"
TEST_CASE_TITLE = "Shared Edit Surface entry points - drawer/dialog opens with preloaded data"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts396_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts396_success.png"
TARGET_ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
COMPACT_VIEWPORT = {"width": 390, "height": 844}
REQUEST_STEPS = [
    "Open the deployed TrackState app at https://istin.github.io/trackstate-setup/.",
    "Navigate to Board (desktop viewport: 1440px) and click the Edit affordance on the DEMO-2 issue card.",
    "Observe the layout and verify the Summary, Description, and Priority fields are preloaded.",
    "Close the editor and navigate to Issue Detail for the same DEMO-2 issue.",
    "Click the Edit action in the detail pane and verify the desktop drawer opens with the same preloaded data.",
    "Set the viewport to 390px, trigger Edit again, and verify the compact full-width sheet still preloads the same issue data.",
]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-396 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    metadata = service.fetch_demo_metadata()
    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(TARGET_ISSUE_PATH)
    _assert_preconditions(issue_fixture=issue_fixture)

    expected_priority_label = _display_label(issue_fixture.priority_id)
    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": metadata.repository,
        "repository_ref": metadata.ref,
        "issue_key": issue_fixture.key,
        "issue_summary": issue_fixture.summary,
        "issue_description": issue_fixture.description,
        "issue_priority_id": issue_fixture.priority_id,
        "expected_priority_label": expected_priority_label,
        "steps": [],
    }
    step_failures: list[dict[str, object]] = []

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveMultiViewRefreshPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the shared edit-surface scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the hosted tracker shell.",
                    observed=runtime.body_text,
                )

                page.ensure_connected(
                    token=token,
                    repository=metadata.repository,
                    user_login=user.login,
                )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Confirm the hosted session is connected to the deployed repository.",
                    observed=page.current_body_text(),
                )

                page.set_viewport(**DESKTOP_VIEWPORT)
                board_dialog_open = False
                try:
                    board_edit_text = page.open_edit_dialog_from_board_card(
                        issue_key=issue_fixture.key,
                        issue_summary=issue_fixture.summary,
                    )
                    board_dialog_open = True
                    _record_step(
                        result,
                        step=3,
                        status="passed",
                        action=(
                            "Use the Board card Edit affordance to open the shared Edit issue "
                            "surface."
                        ),
                        observed=board_edit_text,
                    )
                except Exception as error:
                    _record_failure(
                        result,
                        step_failures,
                        step=3,
                        action=(
                            "Use the Board card Edit affordance to open the shared Edit issue "
                            "surface."
                        ),
                        error=error,
                    )

                if board_dialog_open:
                    try:
                        desktop_board_observation = page.observe_edit_surface(
                            viewport_width=DESKTOP_VIEWPORT["width"],
                            viewport_height=DESKTOP_VIEWPORT["height"],
                        )
                        result["desktop_board_observation"] = _observation_payload(
                            desktop_board_observation,
                        )
                        _assert_edit_surface_preloaded(
                            observation=desktop_board_observation,
                            issue_fixture=issue_fixture,
                            expected_priority_label=expected_priority_label,
                            step_number=4,
                            layout_mode="desktop Board card",
                        )
                        _assert_desktop_drawer_layout(
                            observation=desktop_board_observation,
                            step_number=4,
                        )
                        _record_step(
                            result,
                            step=4,
                            status="passed",
                            action=(
                                "Open Edit from the Board card and verify the desktop "
                                "drawer layout plus the preloaded Summary, Description, and "
                                "Priority."
                            ),
                            observed=_format_observation(desktop_board_observation),
                        )
                    except Exception as error:
                        _record_failure(
                            result,
                            step_failures,
                            step=4,
                            action=(
                                "Open Edit from the Board card and verify the desktop "
                                "drawer layout plus the preloaded Summary, Description, and "
                                "Priority."
                            ),
                            error=error,
                            observed=(
                                _format_observation(desktop_board_observation)
                                if "desktop_board_observation" in locals()
                                else None
                            ),
                        )
                    finally:
                        try:
                            page.close_edit_dialog()
                        except Exception as error:
                            _record_failure(
                                result,
                                step_failures,
                                step=4,
                                action="Close the desktop Board edit surface.",
                                error=error,
                            )

                detail_dialog_open = False
                try:
                    page.open_edit_dialog_for_issue(
                        issue_key=issue_fixture.key,
                        issue_summary=issue_fixture.summary,
                    )
                    detail_dialog_open = True
                except Exception as error:
                    _record_failure(
                        result,
                        step_failures,
                        step=5,
                        action=(
                            "Open Edit from the issue detail pane and verify the same issue "
                            "metadata is preloaded on desktop."
                        ),
                        error=error,
                    )

                if detail_dialog_open:
                    try:
                        desktop_detail_observation = page.observe_edit_surface(
                            viewport_width=DESKTOP_VIEWPORT["width"],
                            viewport_height=DESKTOP_VIEWPORT["height"],
                        )
                        result["desktop_issue_detail_observation"] = _observation_payload(
                            desktop_detail_observation,
                        )
                        _assert_edit_surface_preloaded(
                            observation=desktop_detail_observation,
                            issue_fixture=issue_fixture,
                            expected_priority_label=expected_priority_label,
                            step_number=5,
                            layout_mode="desktop issue detail",
                        )
                        _assert_desktop_drawer_layout(
                            observation=desktop_detail_observation,
                            step_number=5,
                        )
                        _record_step(
                            result,
                            step=5,
                            status="passed",
                            action=(
                                "Open Edit from the issue detail pane and verify the desktop "
                                "drawer layout plus the same issue metadata is preloaded."
                            ),
                            observed=_format_observation(desktop_detail_observation),
                        )
                    except Exception as error:
                        _record_failure(
                            result,
                            step_failures,
                            step=5,
                            action=(
                                "Open Edit from the issue detail pane and verify the desktop "
                                "drawer layout plus the same issue metadata is preloaded."
                            ),
                            error=error,
                            observed=(
                                _format_observation(desktop_detail_observation)
                                if "desktop_detail_observation" in locals()
                                else None
                            ),
                        )
                    finally:
                        try:
                            page.close_edit_dialog()
                        except Exception as error:
                            _record_failure(
                                result,
                                step_failures,
                                step=5,
                                action="Close the desktop issue-detail edit surface.",
                                error=error,
                            )

                compact_dialog_open = False
                try:
                    page.set_viewport(**COMPACT_VIEWPORT)
                    page.open_edit_dialog_for_issue(
                        issue_key=issue_fixture.key,
                        issue_summary=issue_fixture.summary,
                    )
                    compact_dialog_open = True
                except Exception as error:
                    _record_failure(
                        result,
                        step_failures,
                        step=6,
                        action=(
                            "Resize to 390px, open Edit again, and verify the compact sheet "
                            "stays nearly full-width with the same preloaded issue metadata."
                        ),
                        error=error,
                    )

                if compact_dialog_open:
                    try:
                        compact_observation = page.observe_edit_surface(
                            viewport_width=COMPACT_VIEWPORT["width"],
                            viewport_height=COMPACT_VIEWPORT["height"],
                        )
                        result["compact_observation"] = _observation_payload(compact_observation)
                        _assert_edit_surface_preloaded(
                            observation=compact_observation,
                            issue_fixture=issue_fixture,
                            expected_priority_label=expected_priority_label,
                            step_number=6,
                            layout_mode="compact issue detail",
                        )
                        _assert_compact_sheet_layout(
                            observation=compact_observation,
                            step_number=6,
                        )
                        _record_step(
                            result,
                            step=6,
                            status="passed",
                            action=(
                                "Resize to 390px, open Edit again, and verify the compact "
                                "sheet stays nearly full-width with the same preloaded issue "
                                "metadata."
                            ),
                            observed=_format_observation(compact_observation),
                        )
                    except Exception as error:
                        _record_failure(
                            result,
                            step_failures,
                            step=6,
                            action=(
                                "Resize to 390px, open Edit again, and verify the compact sheet "
                                "stays nearly full-width with the same preloaded issue metadata."
                            ),
                            error=error,
                            observed=(
                                _format_observation(compact_observation)
                                if "compact_observation" in locals()
                                else None
                            ),
                        )
                    finally:
                        try:
                            page.close_edit_dialog()
                        except Exception as error:
                            _record_failure(
                                result,
                                step_failures,
                                step=6,
                                action="Close the compact edit surface.",
                                error=error,
                            )

                if step_failures:
                    result["step_failures"] = step_failures
                    page.screenshot(str(SCREENSHOT_PATH))
                    result["screenshot"] = str(SCREENSHOT_PATH)
                    raise AssertionError(_build_combined_failure_message(step_failures))

                page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                if "screenshot" not in result:
                    page.screenshot(str(SCREENSHOT_PATH))
                    result["screenshot"] = str(SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = f"AssertionError: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified the deployed Edit issue surface opens from the Board card and "
            "issue-detail flows with preloaded Summary, Description, and Priority; "
            "desktop stays right-docked and compact expands to a near full-width sheet."
        )
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))


def _assert_preconditions(*, issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-396 expected the seeded DEMO-2 fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )
    if not issue_fixture.summary.strip():
        raise AssertionError(
            "Precondition failed: DEMO-2 does not expose a non-empty summary.",
        )
    if not issue_fixture.description.strip():
        raise AssertionError(
            "Precondition failed: DEMO-2 does not expose a non-empty description.",
        )
    if not issue_fixture.priority_id.strip():
        raise AssertionError(
            "Precondition failed: DEMO-2 does not expose a priority in front matter.",
        )


def _assert_edit_surface_preloaded(
    *,
    observation: EditSurfaceObservation,
    issue_fixture: LiveHostedIssueFixture,
    expected_priority_label: str,
    step_number: int,
    layout_mode: str,
) -> None:
    if "Edit issue" not in observation.body_text:
        raise AssertionError(
            f"Step {step_number} failed: the {layout_mode} flow did not leave the user on "
            "the visible Edit issue surface.\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.summary_value != issue_fixture.summary:
        raise AssertionError(
            f"Step {step_number} failed: the visible Summary field on the {layout_mode} "
            "Edit surface was not preloaded with the selected issue summary.\n"
            f"Expected Summary: {issue_fixture.summary!r}\n"
            f"Actual Summary: {observation.summary_value!r}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    if observation.description_value != issue_fixture.description:
        raise AssertionError(
            f"Step {step_number} failed: the visible Description field on the {layout_mode} "
            "Edit surface was not preloaded with the selected issue description.\n"
            f"Expected Description: {issue_fixture.description!r}\n"
            f"Actual Description: {observation.description_value!r}\n"
            f"Observed page text:\n{observation.body_text}",
        )
    priority_payload = "\n".join(
        [
            f"Priority label: {observation.priority_label!r}",
            f"Priority text: {observation.priority_text!r}",
        ],
    )
    if expected_priority_label not in observation.priority_text and (
        observation.priority_label is None
        or expected_priority_label not in observation.priority_label
    ):
        raise AssertionError(
            f"Step {step_number} failed: the visible Priority control on the {layout_mode} "
            "Edit surface did not show the selected issue priority.\n"
            f"Expected Priority label: {expected_priority_label!r}\n"
            f"{priority_payload}\n"
            f"Observed page text:\n{observation.body_text}",
        )


def _assert_desktop_drawer_layout(
    *,
    observation: EditSurfaceObservation,
    step_number: int,
) -> None:
    if observation.width_fraction > 0.55:
        raise AssertionError(
            f"Step {step_number} failed: on desktop the Edit issue surface should dock like "
            "a right-side drawer instead of expanding too wide.\n"
            f"Observed width fraction: {observation.width_fraction:.3f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )
    if observation.right_inset > 48:
        raise AssertionError(
            f"Step {step_number} failed: on desktop the Edit issue surface was not docked "
            "close enough to the right edge.\n"
            f"Observed right inset: {observation.right_inset:.1f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )
    if observation.left < 200:
        raise AssertionError(
            f"Step {step_number} failed: on desktop the Edit issue surface started too far "
            "left to behave like a drawer.\n"
            f"Observed left inset: {observation.left:.1f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )


def _assert_compact_sheet_layout(
    *,
    observation: EditSurfaceObservation,
    step_number: int,
) -> None:
    if observation.width_fraction < 0.88:
        raise AssertionError(
            f"Step {step_number} failed: at 390px the Edit issue surface did not expand to "
            "a near full-width sheet.\n"
            f"Observed width fraction: {observation.width_fraction:.3f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )
    if observation.height_fraction < 0.88:
        raise AssertionError(
            f"Step {step_number} failed: at 390px the Edit issue surface did not expand "
            "vertically like a full-height sheet.\n"
            f"Observed height fraction: {observation.height_fraction:.3f}\n"
            f"Observed geometry: {_format_geometry(observation)}",
        )
    for label, value in (
        ("left inset", observation.left),
        ("right inset", observation.right_inset),
        ("top inset", observation.top),
        ("bottom inset", observation.bottom_inset),
    ):
        if value > 24:
            raise AssertionError(
                f"Step {step_number} failed: at 390px the Edit issue surface left too much "
                f"space for a compact full-width sheet ({label} = {value:.1f}).\n"
                f"Observed geometry: {_format_geometry(observation)}",
            )


def _display_label(value: str) -> str:
    compact = value.replace("-", " ").replace("_", " ").strip()
    return " ".join(fragment.capitalize() for fragment in compact.split())


def _format_geometry(observation: EditSurfaceObservation) -> str:
    return (
        f"viewport={observation.viewport_width:.0f}x{observation.viewport_height:.0f}, "
        f"left={observation.left:.1f}, top={observation.top:.1f}, "
        f"width={observation.width:.1f}, height={observation.height:.1f}, "
        f"rightInset={observation.right_inset:.1f}, "
        f"bottomInset={observation.bottom_inset:.1f}"
    )


def _observation_payload(observation: EditSurfaceObservation) -> dict[str, object]:
    return {
        "viewport_width": observation.viewport_width,
        "viewport_height": observation.viewport_height,
        "left": observation.left,
        "top": observation.top,
        "width": observation.width,
        "height": observation.height,
        "width_fraction": observation.width_fraction,
        "height_fraction": observation.height_fraction,
        "right_inset": observation.right_inset,
        "bottom_inset": observation.bottom_inset,
        "summary_value": observation.summary_value,
        "description_value": observation.description_value,
        "priority_label": observation.priority_label,
        "priority_text": observation.priority_text,
    }


def _format_observation(observation: EditSurfaceObservation) -> str:
    return (
        f"Summary={observation.summary_value!r}; "
        f"Description={observation.description_value!r}; "
        f"Priority={observation.priority_label or observation.priority_text!r}; "
        f"{_format_geometry(observation)}"
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


def _record_failure(
    result: dict[str, object],
    step_failures: list[dict[str, object]],
    *,
    step: int,
    action: str,
    error: Exception,
    observed: str | None = None,
) -> None:
    error_text = f"{type(error).__name__}: {error}" if not str(error).strip() else str(error)
    observed_text = error_text if observed is None else f"{error_text}\nObserved:\n{observed}"
    _record_step(
        result,
        step=step,
        status="failed",
        action=action,
        observed=observed_text,
    )
    step_failures.append(
        {
            "step": step,
            "action": action,
            "error": error_text,
            "observed": observed,
            "traceback": traceback.format_exc(),
        },
    )


def _build_human_verification_lines(payload: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    board = payload.get("desktop_board_observation")
    if isinstance(board, dict):
        lines.append(
            _format_human_line(
                check=(
                    "Desktop Board entry point visibly opens as a right-side drawer for "
                    "DEMO-2."
                ),
                observed=_format_surface_observation(
                    "Drawer geometry",
                    board,
                ),
                jira=jira,
            ),
        )

    detail = payload.get("desktop_issue_detail_observation")
    if isinstance(detail, dict):
        lines.append(
            _format_human_line(
                check=(
                    "Desktop Issue Detail entry point shows the same right-docked Edit surface."
                ),
                observed=_format_surface_observation(
                    "Drawer geometry",
                    detail,
                ),
                jira=jira,
            ),
        )

    compact = payload.get("compact_observation")
    if isinstance(compact, dict):
        lines.append(
            _format_human_line(
                check=(
                    "Compact 390px entry point opens as a near full-width sheet from the "
                    "user's perspective."
                ),
                observed=_format_surface_observation(
                    "Sheet geometry",
                    compact,
                ),
                jira=jira,
            ),
        )

    return lines


def _format_human_line(*, check: str, observed: str, jira: bool) -> str:
    if jira:
        return f"* {check}\n** Observed: {observed}"
    return f"- **{check}**\n  - Observed: {observed}"


def _format_observation_dict(observation: dict[str, object]) -> str:
    return (
        "viewport="
        f"{_number(observation.get('viewport_width')):.0f}x"
        f"{_number(observation.get('viewport_height')):.0f}, "
        f"left={_number(observation.get('left')):.1f}, "
        f"top={_number(observation.get('top')):.1f}, "
        f"width={_number(observation.get('width')):.1f}, "
        f"height={_number(observation.get('height')):.1f}, "
        f"rightInset={_number(observation.get('right_inset')):.1f}, "
        f"bottomInset={_number(observation.get('bottom_inset')):.1f}"
    )


def _number(value: object) -> float:
    return float(value) if isinstance(value, (int, float)) else 0.0


def _display_priority_from_observation(observation: dict[str, object]) -> str:
    for key in ("priority_label", "priority_text"):
        value = observation.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return "<missing>"


def _format_surface_observation(prefix: str, observation: dict[str, object]) -> str:
    return (
        f"{prefix}: {_format_observation_dict(observation)}. "
        f"Summary rendered as {observation.get('summary_value', '')!r}, "
        f"Description rendered as {observation.get('description_value', '')!r}, "
        f"and Priority rendered as {_display_priority_from_observation(observation)!r}."
    )


def _build_jira_comment(payload: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    automation_lines = format_step_lines(payload, jira=True)
    human_lines = _build_human_verification_lines(payload, jira=True)
    expected_result = (
        "Desktop entry points open a right-side drawer; compact 390px opens a near "
        "full-width sheet; Summary, Description, and Priority are preloaded from DEMO-2."
    )
    actual_result = _build_actual_result(payload, passed=passed)
    screenshot = payload.get("screenshot")
    error = payload.get("error")
    traceback_text = payload.get("traceback")

    sections = [
        f"h1. {TICKET_KEY} {status}",
        "",
        f"*Test case:* {TEST_CASE_TITLE}",
        f"*Environment:* {payload.get('app_url', 'unknown')} in Chromium on {platform.platform()}",
        f"*Repository:* {payload.get('repository', 'unknown')} @ {payload.get('repository_ref', 'unknown')}",
        "*Viewport coverage:* desktop 1440x900, compact 390x844",
        "*Linked bugs reviewed:* TS-1086, TS-1067, TS-1169",
        "*Timing notes:* No additional async wait was required by the linked bug fixes.",
        "",
        "h2. What was automated",
        "* Open the hosted TrackState app and confirm the session is connected to the deployed repository.",
        "* Open the shared Edit issue surface from the Board card and from Issue Detail.",
        "* Verify desktop drawer geometry and compact sheet geometry.",
        "* Verify Summary, Description, and Priority preload for DEMO-2.",
        "",
        "h2. Automation checks",
        *(automation_lines or ["* No automation steps were recorded."]),
        "",
        "h2. Real user-style verification",
        *(human_lines or ["* No human-style verification observations were recorded."]),
        "",
        "h2. Expected vs Actual",
        f"*Expected:* {expected_result}",
        f"*Actual:* {actual_result}",
    ]

    if screenshot:
        sections.extend(["", "h2. Screenshot", str(screenshot)])

    if error:
        sections.extend(["", "h2. Failure", "{code}", str(error), "{code}"])
    if traceback_text:
        sections.extend(["", "h2. Traceback", "{code}", str(traceback_text), "{code}"])

    return "\n".join(sections) + "\n"


def _build_pr_body(payload: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    automation_lines = format_step_lines(payload, jira=False)
    human_lines = _build_human_verification_lines(payload, jira=False)
    expected_result = (
        "Desktop entry points open a right-side drawer; compact 390px opens a near "
        "full-width sheet; Summary, Description, and Priority are preloaded from DEMO-2."
    )
    actual_result = _build_actual_result(payload, passed=passed)
    screenshot = payload.get("screenshot")
    error = payload.get("error")
    traceback_text = payload.get("traceback")

    sections = [
        f"# {TICKET_KEY} {status}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        f"**Environment:** `{payload.get('app_url', 'unknown')}` in Chromium on `{platform.platform()}`",
        f"**Repository:** `{payload.get('repository', 'unknown')}` @ `{payload.get('repository_ref', 'unknown')}`",
        "**Viewport coverage:** `1440x900` desktop, `390x844` compact",
        "**Linked bugs reviewed:** `TS-1086`, `TS-1067`, `TS-1169`",
        "**Timing notes:** No additional async wait was required by the linked bug fixes.",
        "",
        "## What was automated",
        "- Open the hosted TrackState app and confirm the session is connected to the deployed repository.",
        "- Open the shared Edit issue surface from the Board card and from Issue Detail.",
        "- Verify desktop drawer geometry and compact sheet geometry.",
        "- Verify Summary, Description, and Priority preload for DEMO-2.",
        "",
        "## Automation checks",
        *(automation_lines or ["- No automation steps were recorded."]),
        "",
        "## Real user-style verification",
        *(human_lines or ["- No human-style verification observations were recorded."]),
        "",
        "## Expected vs Actual",
        f"- **Expected:** {expected_result}",
        f"- **Actual:** {actual_result}",
    ]

    if screenshot:
        sections.extend(["", "## Screenshot", f"`{screenshot}`"])
    if error:
        sections.extend(["", "## Failure", "```text", str(error), "```"])
    if traceback_text:
        sections.extend(["", "## Traceback", "```text", str(traceback_text), "```"])

    return "\n".join(sections) + "\n"


def _build_response_summary(payload: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed.\n\n"
            "The shared Edit issue surface opened from the Board card and Issue Detail on "
            "the deployed hosted app with the expected desktop and compact layouts, and the "
            "selected issue metadata stayed preloaded across entry points.\n"
        )

    return (
        f"{TICKET_KEY} failed.\n\n"
        f"{_build_actual_result(payload, passed=False)}\n\n"
        f"{payload.get('error', 'No error message was recorded.')}\n"
    )


def _build_bug_description(payload: dict[str, object]) -> str:
    failure_summary = _first_product_failure(payload)
    if failure_summary is None:
        raise AssertionError(
            "bug_description.md should only be written for verified product-visible failures.",
        )
    annotated_steps = build_annotated_steps(payload, request_steps=REQUEST_STEPS)
    screenshot = payload.get("screenshot", "No screenshot recorded.")
    traceback_text = payload.get("traceback", payload.get("error", "No traceback recorded."))
    expected_priority = payload.get("expected_priority_label", "Highest")

    return (
        f"# {TICKET_KEY} bug report\n\n"
        "## Steps to reproduce\n"
        + "\n".join(f"{line}" for line in annotated_steps)
        + "\n\n## Exact error message or assertion failure\n```text\n"
        + str(traceback_text)
        + "\n```\n\n## Actual vs Expected\n"
        + f"**Expected:** {payload.get('expected_result', _expected_result_text())}\n\n"
        + f"**Actual:** {_build_actual_result(payload, passed=False)}\n\n"
        + "## Missing or broken production capability\n"
        + f"The product did not satisfy step {failure_summary['step']}: "
        + f"{failure_summary['action']}\n\n"
        + f"Verified failure: {failure_summary['error']}\n\n"
        + "## Environment details\n"
        + f"- URL: `{payload.get('app_url', 'unknown')}`\n"
        + f"- Browser: `Chromium`\n"
        + f"- OS: `{platform.platform()}`\n"
        + "- Desktop viewport: `1440x900`\n"
        + "- Compact viewport: `390x844`\n"
        + f"- Repository: `{payload.get('repository', 'unknown')}`\n"
        + f"- Ref: `{payload.get('repository_ref', 'unknown')}`\n"
        + f"- Issue under test: `{payload.get('issue_key', 'DEMO-2')}`\n\n"
        + "## Failing command and evidence\n"
        + "- Command: `python testing/tests/TS-396/test_ts_396.py`\n"
        + f"- Screenshot: `{screenshot}`\n"
        + f"- Error: `{payload.get('error', 'No error message was recorded.')}`\n"
    )


def _build_actual_result(payload: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            "Board and Issue Detail both opened the shared Edit surface with the expected "
            "desktop drawer and compact sheet layouts, and Summary, Description, and Priority "
            "were preloaded from DEMO-2."
        )

    observation_summaries = _build_observation_summaries(payload)
    failure_summaries = _step_failure_summaries(payload)
    if observation_summaries and failure_summaries:
        return (
            f"{' '.join(observation_summaries)} "
            f"Recorded failure(s): {'; '.join(failure_summaries)}."
        )
    if failure_summaries:
        return f"Recorded failure(s): {'; '.join(failure_summaries)}."
    if observation_summaries:
        return " ".join(observation_summaries)
    return str(payload.get("error", "No failure details were recorded."))


def _expected_result_text() -> str:
    return (
        "On desktop, the editor opens as a right-side drawer. On compact layouts, it "
        "opens as a full-width sheet. In all cases, the editor is preloaded with the "
        "selected issue's current metadata (Summary, Description, Priority)."
    )


def _build_observation_summaries(payload: dict[str, object]) -> list[str]:
    summaries: list[str] = []
    for label, key in (
        ("Board desktop", "desktop_board_observation"),
        ("Issue Detail desktop", "desktop_issue_detail_observation"),
        ("Compact Issue Detail", "compact_observation"),
    ):
        observation = payload.get(key)
        if not isinstance(observation, dict):
            continue
        summaries.append(
            f"{label} showed {_format_surface_observation('geometry', observation)}",
        )
    return summaries


def _step_failures(payload: dict[str, object]) -> list[dict[str, object]]:
    failures = payload.get("step_failures")
    if not isinstance(failures, list):
        return []
    normalized: list[dict[str, object]] = []
    for failure in failures:
        if not isinstance(failure, dict):
            continue
        normalized.append(failure)
    return normalized


def _step_failure_summaries(payload: dict[str, object]) -> list[str]:
    summaries: list[str] = []
    for failure in _step_failures(payload):
        step = int(failure.get("step", -1))
        action = str(failure.get("action", "Unknown action"))
        error = str(failure.get("error", "Unknown error"))
        summaries.append(f"step {step} ({action}) failed with `{error}`")
    return summaries


def _build_combined_failure_message(step_failures: list[dict[str, object]]) -> str:
    messages: list[str] = []
    for failure in step_failures:
        step = int(failure.get("step", -1))
        error = str(failure.get("error", "Unknown error"))
        if error.lower().startswith(f"step {step} failed"):
            messages.append(error)
        else:
            messages.append(f"Step {step} failed: {error}")
    return "\n\n".join(messages)


def _first_product_failure(payload: dict[str, object]) -> dict[str, object] | None:
    for failure in _step_failures(payload):
        step = int(failure.get("step", -1))
        if step < 3:
            continue
        error = str(failure.get("error", ""))
        lowered = error.lower()
        if any(
            marker in lowered
            for marker in (
                "requires gh_token",
                "requires github_token",
                "api rate limit",
                "rate limit exceeded",
                "403",
                "401",
                "no module named",
                "modulenotfounderror",
                "syntaxerror",
                "nameerror",
                "typeerror",
                "attributeerror",
                "keyerror",
                "indexerror",
                "unboundlocalerror",
                "filenotfounderror",
                "permissionerror",
            )
        ):
            continue
        return failure
    return None


def _write_required_outputs(payload: dict[str, object]) -> None:
    passed = payload.get("status") == "passed"
    error = str(payload.get("error")) if not passed and payload.get("error") else None

    write_test_automation_result(RESULT_PATH, passed=passed, error=error)
    JIRA_COMMENT_PATH.write_text(
        _build_jira_comment(payload, passed=passed),
        encoding="utf-8",
    )
    PR_BODY_PATH.write_text(
        _build_pr_body(payload, passed=passed),
        encoding="utf-8",
    )
    RESPONSE_PATH.write_text(
        _build_response_summary(payload, passed=passed),
        encoding="utf-8",
    )

    if passed or _first_product_failure(payload) is None:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    else:
        BUG_DESCRIPTION_PATH.write_text(
            _build_bug_description(payload),
            encoding="utf-8",
        )


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS396_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts396_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    _write_required_outputs(payload)


if __name__ == "__main__":
    main()
