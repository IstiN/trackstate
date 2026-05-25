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
    WorkspaceSwitcherBlurDismissObservation,
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherPanelObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-821"
TEST_CASE_TITLE = "Lose component focus — workspace switcher panel dismisses via blur"
INPUT_DIR = REPO_ROOT / "input" / TICKET_KEY
DISCUSSIONS_RAW_PATH = INPUT_DIR / "pr_discussions_raw.json"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-821/test_ts_821.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 900}
BLUR_WAIT_MS = 6_000

REQUEST_STEPS = [
    "Launch the application on a desktop browser.",
    "Click the workspace switcher trigger to open the panel.",
    (
        "Press the 'Tab' key to move focus to a different interactive element "
        "outside the switcher (e.g., a 'Search' field or 'Create' button)."
    ),
    "Observe the state of the workspace switcher panel.",
]
EXPECTED_RESULT = (
    "The workspace switcher panel closes automatically when focus is lost to an "
    "external element."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts821_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts821_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-821 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "blur_wait_ms": BLUR_WAIT_MS,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the blur-dismissal scenario began.\n"
                            f"Observed runtime state: {runtime.kind}\n"
                            f"Observed body text:\n{runtime.body_text}",
                        )

                    page.dismiss_connection_banner()
                    page.navigate_to_section("Dashboard")
                    page.set_viewport(**DESKTOP_VIEWPORT)
                    trigger = page.observe_trigger()
                    result["trigger_observation"] = _trigger_payload(trigger)
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
                        f"trigger_text={trigger.visible_text!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the desktop app shell before the scenario and confirmed "
                        "Dashboard plus the workspace switcher trigger were visibly rendered."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                try:
                    switcher = page.open_and_observe()
                    panel = page.observe_open_panel(
                        expected_container_kinds=("anchored-panel", "surface"),
                    )
                    _assert_desktop_panel_open(
                        trigger=trigger,
                        switcher=switcher,
                        panel=panel,
                    )
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    result["open_panel_observation"] = asdict(panel)
                except Exception as error:
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
                        f"container_kind={panel.container_kind}; "
                        f"anchored_to_trigger={panel.anchored_to_trigger}; "
                        f"row_count={switcher.row_count}; "
                        f"title_visible={'Workspace switcher' in switcher.switcher_text}; "
                        f"content_excerpt={_snippet(switcher.switcher_text)}"
                    ),
                )

                try:
                    blur_observation = page.observe_blur_dismissal_after_tab(
                        panel=panel,
                        dismissal_timeout_ms=BLUR_WAIT_MS,
                    )
                    result["blur_observation"] = _blur_payload(blur_observation)
                    _assert_external_focus_reached(blur_observation)
                except Exception as error:
                    _record_human_verification(
                        result,
                        check=(
                            "Opened the visible desktop workspace switcher and tried to "
                            "continue the keyboard flow like a user."
                        ),
                        observed=str(error),
                    )
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
                        "Pressing Tab moved focus away from the switcher from a "
                        f"switcher-owned pre-Tab state={blur_observation.before_focus_owned_by_switcher} "
                        "to "
                        f"{blur_observation.after_focus_label!r} "
                        f"(role={blur_observation.after_focus_role!r}, "
                        f"tag={blur_observation.after_focus_tag_name!r}, "
                        f"visible={blur_observation.after_focus_visible}, "
                        f"in_viewport={blur_observation.after_focus_in_viewport}, "
                        f"different_from_before="
                        f"{blur_observation.after_focus_different_from_before})."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Opened the visible desktop workspace switcher, confirmed the panel "
                        "content a user would see, pressed Tab once, and watched which real "
                        "control received focus next."
                    ),
                    observed=(
                        f"switcher_text={_snippet(switcher.switcher_text)}; "
                        f"before_focus={blur_observation.before_focus_label!r}; "
                        f"before_role={blur_observation.before_focus_role!r}; "
                        f"before_visible={blur_observation.before_focus_visible}; "
                        f"before_in_viewport={blur_observation.before_focus_in_viewport}; "
                        f"before_within_switcher={blur_observation.before_focus_within_switcher}; "
                        f"before_on_trigger={blur_observation.before_focus_on_trigger}; "
                        f"before_owned_by_switcher={blur_observation.before_focus_owned_by_switcher}; "
                        f"focus_target={blur_observation.after_focus_label!r}; "
                        f"role={blur_observation.after_focus_role!r}; "
                        f"tag={blur_observation.after_focus_tag_name!r}; "
                        f"visible={blur_observation.after_focus_visible}; "
                        f"in_viewport={blur_observation.after_focus_in_viewport}; "
                        f"different_from_before="
                        f"{blur_observation.after_focus_different_from_before}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Observed the UI after focus left the switcher to see whether the "
                        "panel actually disappeared for a user."
                    ),
                    observed=(
                        f"panel_visible_after_wait={blur_observation.panel_visible_after_wait}; "
                        f"panel_text={_snippet(blur_observation.panel_text_after_wait)}"
                    ),
                )

                try:
                    _assert_blur_dismissal(blur_observation)
                except Exception as error:
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
                        "The workspace switcher surface dismissed after focus moved "
                        "outside the component."
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


def _assert_desktop_panel_open(
    *,
    trigger: WorkspaceSwitcherTriggerObservation,
    switcher: WorkspaceSwitcherObservation,
    panel: WorkspaceSwitcherPanelObservation,
) -> None:
    switcher_text = switcher.switcher_text.strip()
    if not switcher_text:
        raise AssertionError(
            "Step 2 failed: opening the workspace switcher did not expose readable "
            "visible panel content.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if (
        "Workspace switcher" not in switcher_text
        and trigger.display_name not in switcher_text
        and "Add workspace" not in switcher_text
    ):
        raise AssertionError(
            "Step 2 failed: clicking the workspace switcher trigger did not expose the "
            "expected desktop workspace-switcher content.\n"
            f"Observed switcher text:\n{switcher.switcher_text}",
        )
    if panel.container_kind not in {"anchored-panel", "surface"}:
        raise AssertionError(
            "Step 2 failed: clicking the workspace switcher trigger did not open the "
            "expected desktop panel-style surface.\n"
            f"Observed container kind: {panel.container_kind}\n"
            f"Observed bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}",
        )
    if panel.width <= 0 or panel.height <= 0:
        raise AssertionError(
            "Step 2 failed: clicking the workspace switcher trigger did not expose a "
            "readable desktop panel surface.\n"
            f"Observed panel bounds: left={panel.left:.1f}, top={panel.top:.1f}, "
            f"width={panel.width:.1f}, height={panel.height:.1f}\n"
            f"Observed trigger bounds: left={trigger.left:.1f}, top={trigger.top:.1f}, "
            f"width={trigger.width:.1f}, height={trigger.height:.1f}",
        )


def _assert_external_focus_reached(
    observation: WorkspaceSwitcherBlurDismissObservation,
) -> None:
    if not observation.before_focus_owned_by_switcher:
        raise AssertionError(
            "Step 3 failed: before pressing Tab, focus was not owned by the workspace "
            "switcher component or its trigger, so the blur-dismissal scenario was not "
            "validly exercised.\n"
            f"Observed focus before Tab: label={observation.before_focus_label!r}, "
            f"role={observation.before_focus_role!r}, tag={observation.before_focus_tag_name!r}\n"
            f"Focused element visible before Tab: {observation.before_focus_visible}\n"
            f"Focused element in viewport before Tab: {observation.before_focus_in_viewport}\n"
            f"Focused element within switcher before Tab: "
            f"{observation.before_focus_within_switcher}\n"
            f"Focused element on trigger before Tab: {observation.before_focus_on_trigger}",
        )
    if observation.external_focus_reached:
        return
    raise AssertionError(
        "Step 3 failed: pressing Tab after opening the workspace switcher did not "
        "move focus to a visible, different interactive element outside the "
        "switcher.\n"
        f"Observed focus before Tab: label={observation.before_focus_label!r}, "
        f"role={observation.before_focus_role!r}, tag={observation.before_focus_tag_name!r}\n"
        f"Observed focus after Tab: label={observation.after_focus_label!r}, "
        f"role={observation.after_focus_role!r}, tag={observation.after_focus_tag_name!r}\n"
        f"Focused element visible: {observation.after_focus_visible}\n"
        f"Focused element in viewport: {observation.after_focus_in_viewport}\n"
        f"Focused element changed after Tab: {observation.after_focus_different_from_before}\n"
        f"Active element remained within switcher: {observation.after_focus_within_switcher}",
    )


def _assert_blur_dismissal(
    observation: WorkspaceSwitcherBlurDismissObservation,
) -> None:
    if observation.panel_visible_after_wait:
        raise AssertionError(
            "Step 4 failed: focus moved to an external interactive element, but the "
            "workspace switcher panel remained visible instead of dismissing on blur.\n"
            f"Observed focus target: label={observation.after_focus_label!r}, "
            f"role={observation.after_focus_role!r}, tag={observation.after_focus_tag_name!r}\n"
            f"Observed wait: {observation.waited_ms / 1000:.1f} seconds\n"
            f"Observed panel text after blur wait:\n{observation.panel_text_after_wait}",
        )
    if not observation.trigger_visible_after_wait:
        raise AssertionError(
            "Step 4 failed: after the workspace switcher lost focus, the app shell did "
            "not keep the workspace switcher trigger visible.\n"
            f"Observed focus target: label={observation.after_focus_label!r}, "
            f"role={observation.after_focus_role!r}, tag={observation.after_focus_tag_name!r}",
        )
    if not observation.dashboard_visible_after_wait:
        raise AssertionError(
            "Step 4 failed: after the workspace switcher lost focus, the main "
            "Dashboard shell was not visibly present.\n"
            f"Observed focus target: label={observation.after_focus_label!r}, "
            f"role={observation.after_focus_role!r}, tag={observation.after_focus_tag_name!r}",
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
    _write_review_replies(result, passed=True)


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-821 failed"))
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
    _write_review_replies(result, passed=False)


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
        "* Opened the desktop workspace switcher from Dashboard.",
        "* Pressed Tab once after opening the switcher and verified focus moved to another visible interactive control outside the component.",
        (
            f"* Waited {BLUR_WAIT_MS / 1000:.1f} seconds for blur dismissal before "
            "asserting the visible panel state."
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
        "- Opened the desktop workspace switcher from Dashboard.",
        "- Pressed Tab once after opening the switcher and verified focus moved to another visible interactive control outside the component.",
        f"- Waited {BLUR_WAIT_MS / 1000:.1f} seconds for blur dismissal before asserting the visible panel state.",
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
            else "- Outcome: the desktop workspace switcher closed after focus moved to an external control."
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
    if not _product_blur_bug_proven(result):
        if _pre_tab_focus_ownership_bug_proven(result):
            return _pre_tab_focus_ownership_bug_description(result)
        if _step3_product_bug_proven(result):
            return _step3_product_bug_description(result)
        return _test_failure_bug_description(result)
    return "\n".join(
        [
            f"# {TICKET_KEY} - Workspace switcher does not dismiss after losing focus via Tab",
            "",
            "## Steps to reproduce",
            "1. Launch the application on a desktop browser.",
            "2. Click the workspace switcher trigger to open the panel.",
            "3. Press the 'Tab' key to move focus to a different interactive element outside the switcher.",
            "4. Observe the state of the workspace switcher panel.",
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
            (
                "- Expected: after focus moves to a different interactive element "
                "outside the workspace switcher, the panel closes automatically."
            ),
            f"- Actual: {result.get('error', '<missing error>')}",
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
            f"- Blur wait: {BLUR_WAIT_MS / 1000:.1f} seconds",
            f"- Run command: {RUN_COMMAND}",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
        ],
    ) + "\n"


def _step3_product_bug_description(result: dict[str, object]) -> str:
    blur = result.get("blur_observation")
    return "\n".join(
        [
            f"# {TICKET_KEY} - Workspace switcher does not move keyboard focus to a visible external control on Tab",
            "",
            "## Steps to reproduce",
            "1. Launch the application on a desktop browser.",
            "2. Click the workspace switcher trigger to open the panel.",
            "3. Press the `Tab` key once to move focus out of the open workspace switcher.",
            "4. Observe the focused element and the switcher panel state.",
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
            (
                "- Expected: after the workspace switcher owns keyboard focus, pressing "
                "`Tab` should move focus to a different visible interactive control "
                "outside the switcher so the blur-dismiss behavior can be exercised."
            ),
            f"- Actual: {_failed_step_summary(result)}",
            "",
            "## Missing or broken production capability",
            (
                "The live workspace switcher flow does not hand keyboard focus to a "
                "clearly external, user-visible control after `Tab`. In this run, focus "
                "left the selected workspace row but landed on the `Repository` input "
                "while the probe still classified that target as being within the open "
                "switcher bounds, so the required external blur path was not reached."
            ),
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
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Blur wait: {BLUR_WAIT_MS / 1000:.1f} seconds",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps({"blur_observation": blur}, indent=2),
            "```",
        ],
    ) + "\n"


def _pre_tab_focus_ownership_bug_description(result: dict[str, object]) -> str:
    blur = result.get("blur_observation")
    return "\n".join(
        [
            f"# {TICKET_KEY} - Workspace switcher does not expose switcher-owned focus after opening",
            "",
            "## Steps to reproduce",
            "1. Launch the application on a desktop browser.",
            "2. Click the workspace switcher trigger to open the panel.",
            "3. Attempt to continue the keyboard flow from the open switcher by moving focus into the switcher/trigger and then pressing `Tab` once.",
            "4. Observe the focused element before the `Tab` blur step.",
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
            (
                "- Expected: after the workspace switcher opens, the visible trigger or "
                "panel should own focus so pressing `Tab` can move focus to a different "
                "interactive element outside the component and exercise blur dismissal."
            ),
            f"- Actual: {_failed_step_summary(result)}",
            "",
            "## Missing or broken production capability",
            (
                "The live workspace switcher does not expose a production-visible "
                "switcher-owned focus state after opening. Even after a direct focus "
                "attempt on the visible trigger, the active element remains the root "
                "`FLUTTER-VIEW` instead of the trigger or an element inside the open "
                "workspace-switcher panel, so the required blur path cannot be exercised "
                "from the UI."
            ),
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
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Blur wait: {BLUR_WAIT_MS / 1000:.1f} seconds",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
            "```json",
            json.dumps({"blur_observation": blur}, indent=2),
            "```",
        ],
    ) + "\n"


def _test_failure_bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY} - TS-821 automation failed before proving the blur-dismiss product defect",
            "",
            "## Summary",
            (
                "The TS-821 automation run failed, but it did not prove the product bug "
                "from this ticket because the run stopped before demonstrating both that "
                "focus moved outside the workspace switcher and that the panel stayed "
                "visible afterward."
            ),
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
            (
                "- Actual: the automation failed before the blur-dismiss product check was "
                "fully exercised."
            ),
            "",
            "## Missing or broken production capability",
            (
                "Not proven yet in this run. The failure evidence currently points to a "
                "test/setup regression or another earlier-step issue rather than the "
                "specific blur-dismiss product behavior from TS-821."
            ),
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
            "## Environment details",
            f"- URL: {result.get('app_url')}",
            f"- Repository: {result.get('repository')} @ {result.get('repository_ref')}",
            f"- Browser: {result.get('browser')}",
            f"- OS: {result.get('os')}",
            f"- Viewport: {DESKTOP_VIEWPORT['width']}x{DESKTOP_VIEWPORT['height']}",
            f"- Blur wait: {BLUR_WAIT_MS / 1000:.1f} seconds",
            "",
            "## Screenshots or logs",
            f"- Screenshot: {result.get('screenshot', '<no screenshot recorded>')}",
        ],
    ) + "\n"


def _product_blur_bug_proven(result: dict[str, object]) -> bool:
    blur = result.get("blur_observation")
    if not isinstance(blur, dict):
        return False
    return bool(blur.get("external_focus_reached")) and bool(
        blur.get("panel_visible_after_wait"),
    )


def _pre_tab_focus_ownership_bug_proven(result: dict[str, object]) -> bool:
    blur = result.get("blur_observation")
    if not isinstance(blur, dict):
        return False
    before_focus = blur.get("before_focus")
    return isinstance(before_focus, dict) and not bool(
        before_focus.get("owned_by_switcher"),
    )


def _step3_product_bug_proven(result: dict[str, object]) -> bool:
    blur = result.get("blur_observation")
    if not isinstance(blur, dict):
        return False
    before_focus = blur.get("before_focus")
    return (
        isinstance(before_focus, dict)
        and bool(before_focus.get("owned_by_switcher"))
        and not bool(blur.get("external_focus_reached"))
    )


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
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(
                root_comment_id=thread.get("rootCommentId"),
                passed=passed,
                result=result,
            ),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}) + "\n",
        encoding="utf-8",
    )


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


def _review_reply_text(
    *,
    root_comment_id: object,
    passed: bool,
    result: dict[str, object],
) -> str:
    rerun_summary = (
        "Re-ran "
        f"`{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else "Re-ran "
        f"`{RUN_COMMAND}`: failed at {_failed_step_summary(result)}"
    )
    if root_comment_id == 3260410739:
        return (
            "Fixed: the blur helper now accepts switcher-owned focus after the direct "
            "focus call and no longer keyboard-walks from Search trying to make the "
            "trigger itself tabbable before Step 3. "
            + rerun_summary
        )
    if root_comment_id == 3260410842:
        return (
            "Fixed: `outputs/bug_description.md` now only describes the blur-dismiss "
            "product bug after the run proves focus left the switcher and the panel "
            "stayed visible; earlier failures now produce a neutral automation-failure "
            "summary instead of a misleading product bug. "
            + rerun_summary
        )
    if root_comment_id == 3260501228:
        return (
            "Fixed: removed the `FLUTTER-VIEW` fallback from the blur helper, so a "
            "failed ownership probe is no longer rewritten into success. TS-821 now "
            "continues only when switcher-owned focus is positively proven via "
            "switcher-specific signals before `Tab`. "
            + rerun_summary
        )
    return "Fixed and re-ran the requested TS-821 review changes. " + rerun_summary


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


def _switcher_payload(switcher: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "row_count": switcher.row_count,
        "switcher_text": switcher.switcher_text,
        "rows": [
            {
                "display_name": row.display_name,
                "target_type_label": row.target_type_label,
                "state_label": row.state_label,
                "detail_text": row.detail_text,
                "visible_text": row.visible_text,
                "selected": row.selected,
                "action_labels": list(row.action_labels),
                "button_labels": list(row.button_labels),
            }
            for row in switcher.rows
        ],
    }


def _blur_payload(
    observation: WorkspaceSwitcherBlurDismissObservation,
) -> dict[str, object]:
    return {
        "before_focus": {
            "label": observation.before_focus_label,
            "role": observation.before_focus_role,
            "tag_name": observation.before_focus_tag_name,
            "outer_html": observation.before_focus_outer_html,
            "visible": observation.before_focus_visible,
            "in_viewport": observation.before_focus_in_viewport,
            "within_switcher": observation.before_focus_within_switcher,
            "on_trigger": observation.before_focus_on_trigger,
            "owned_by_switcher": observation.before_focus_owned_by_switcher,
        },
        "after_focus": {
            "label": observation.after_focus_label,
            "role": observation.after_focus_role,
            "tag_name": observation.after_focus_tag_name,
            "outer_html": observation.after_focus_outer_html,
        },
        "after_focus_visible": observation.after_focus_visible,
        "after_focus_in_viewport": observation.after_focus_in_viewport,
        "after_focus_different_from_before": (
            observation.after_focus_different_from_before
        ),
        "after_focus_within_switcher": observation.after_focus_within_switcher,
        "external_focus_reached": observation.external_focus_reached,
        "panel_visible_after_wait": observation.panel_visible_after_wait,
        "panel_text_after_wait": observation.panel_text_after_wait,
        "dashboard_visible_after_wait": observation.dashboard_visible_after_wait,
        "trigger_visible_after_wait": observation.trigger_visible_after_wait,
        "waited_ms": observation.waited_ms,
    }


def _snippet(value: object, *, limit: int = 240) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


if __name__ == "__main__":
    main()
