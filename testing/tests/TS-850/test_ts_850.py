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
    WorkspaceSwitcherObservation,
    WorkspaceSwitcherTriggerDismissObservation,
    WorkspaceSwitcherTriggerObservation,
    WorkspaceTriggerAriaExpandedObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-850"
TEST_CASE_TITLE = (
    "Workspace switcher trigger ARIA compliance - aria-expanded state toggles on "
    "mouse interaction"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-850/test_ts_850.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
SURFACE_TOGGLE_TIMEOUT_MS = 4_000

PRECONDITIONS = [
    "The deployed TrackState app is open on a desktop browser and Dashboard is visible.",
    "A hosted GitHub token is available so the live app can render an interactive session.",
]
REQUEST_STEPS = [
    "Open the application and locate the workspace switcher trigger.",
    "Inspect the trigger and verify 'aria-expanded=\"false\"' is present while the surface is collapsed.",
    "Click the workspace switcher trigger with the mouse to open the surface.",
    "Inspect the trigger element again.",
    "Click the workspace switcher trigger again (or click outside/close) to collapse the surface.",
    "Inspect the trigger element again.",
]
EXPECTED_RESULT = (
    "The 'aria-expanded' attribute switches to 'true' when the surface is visible "
    "and returns to 'false' when the surface is hidden."
)
REWORK_FIXES = [
    (
        "Narrowed Step 3 to stable public evidence that the workspace switcher became "
        "visible after the mouse click, without container-kind, exact-heading, or "
        "row-count constraints."
    ),
    (
        "Normalized second-click dismissal failures so any close-path error is "
        "reported as Step 6 in generated outputs."
    ),
]

OUTPUTS_DIR = REPO_ROOT / "outputs"
INPUTS_DIR = REPO_ROOT / "input" / TICKET_KEY
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
DISCUSSIONS_RAW_PATH = INPUTS_DIR / "pr_discussions_raw.json"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts850_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts850_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-850 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
        )
    user = service.fetch_authenticated_user()

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "expected_result": EXPECTED_RESULT,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "desktop_viewport": DESKTOP_VIEWPORT,
        "surface_toggle_timeout_ms": SURFACE_TOGGLE_TIMEOUT_MS,
        "preconditions": PRECONDITIONS,
        "linked_bug": {
            "key": "TS-847",
            "status": "Done",
        },
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            try:
                trigger: WorkspaceSwitcherTriggerObservation | None = None
                try:
                    runtime = tracker_page.open()
                    result["runtime_state"] = runtime.kind
                    result["runtime_body_text"] = runtime.body_text
                    if runtime.kind != "ready":
                        raise AssertionError(
                            "Step 1 failed: the deployed app did not reach an interactive "
                            "desktop state before the mouse ARIA toggle scenario began.\n"
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
                        "Viewed the desktop Dashboard and confirmed the visible workspace "
                        "switcher trigger was present before any mouse interaction."
                    ),
                    observed=(
                        f"trigger_text={trigger.visible_text!r}; "
                        f"top_buttons={list(trigger.top_button_labels)!r}"
                    ),
                )

                aria_before_open: WorkspaceTriggerAriaExpandedObservation | None = None
                try:
                    aria_before_open = page.observe_trigger_aria_expanded(
                        expected_value="false",
                        timeout_ms=SURFACE_TOGGLE_TIMEOUT_MS,
                    )
                    result["trigger_aria_before_open"] = _trigger_aria_payload(
                        aria_before_open,
                    )
                    _assert_trigger_aria_expanded(
                        observation=aria_before_open,
                        expected_value="false",
                        step_number=2,
                        context="before clicking the workspace switcher trigger",
                    )
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
                        f"label={aria_before_open.label!r}; "
                        f"aria-expanded={aria_before_open.aria_expanded!r}; "
                        f"tabindex={aria_before_open.tabindex!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Inspected the visible trigger before opening the switcher and "
                        "confirmed it presented as collapsed to accessibility tooling."
                    ),
                    observed=(
                        f"label={aria_before_open.label!r}; "
                        f"aria-expanded={aria_before_open.aria_expanded!r}"
                    ),
                )

                switcher: WorkspaceSwitcherObservation | None = None
                try:
                    page.open_surface_with_click(timeout_ms=SURFACE_TOGGLE_TIMEOUT_MS)
                    switcher = page.observe_open_switcher(
                        timeout_ms=SURFACE_TOGGLE_TIMEOUT_MS,
                    )
                    result["open_switcher_observation"] = _switcher_payload(switcher)
                    _assert_switcher_opened(switcher=switcher)
                except Exception as error:
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
                        "Clicked the visible workspace switcher trigger and the workspace "
                        "switcher surface opened."
                    ),
                )

                aria_after_open: WorkspaceTriggerAriaExpandedObservation | None = None
                try:
                    aria_after_open = page.observe_trigger_aria_expanded(
                        expected_value="true",
                        timeout_ms=SURFACE_TOGGLE_TIMEOUT_MS,
                    )
                    result["trigger_aria_after_open"] = _trigger_aria_payload(
                        aria_after_open,
                    )
                    _assert_trigger_aria_expanded(
                        observation=aria_after_open,
                        expected_value="true",
                        step_number=4,
                        context="while the workspace switcher surface is visible",
                    )
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
                        f"switcher_visible=True; "
                        f"switcher_text_excerpt={_snippet(switcher.switcher_text)!r}; "
                        f"aria-expanded={aria_after_open.aria_expanded!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked the trigger like a desktop user and visually confirmed "
                        "the workspace switcher opened while the trigger reported an "
                        "expanded state."
                    ),
                    observed=(
                        f"switcher_text_excerpt={_snippet(switcher.switcher_text)!r}; "
                        f"aria-expanded={aria_after_open.aria_expanded!r}"
                    ),
                )

                try:
                    page.toggle_switcher_via_trigger(timeout_ms=SURFACE_TOGGLE_TIMEOUT_MS)
                except Exception as error:
                    _record_step(
                        result,
                        step=5,
                        status="failed",
                        action=REQUEST_STEPS[4],
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        "Clicked the same visible workspace switcher trigger again while "
                        "the surface was open."
                    ),
                )

                dismissal: WorkspaceSwitcherTriggerDismissObservation | None = None
                aria_after_close: WorkspaceTriggerAriaExpandedObservation | None = None
                try:
                    dismissal = page.wait_for_dismissal_after_trigger_click(
                        timeout_ms=SURFACE_TOGGLE_TIMEOUT_MS,
                    )
                    result["dismissal_observation"] = asdict(dismissal)
                    _assert_dismissal_after_click(dismissal)
                    aria_after_close = page.observe_trigger_aria_expanded(
                        expected_value="false",
                        timeout_ms=SURFACE_TOGGLE_TIMEOUT_MS,
                    )
                    result["trigger_aria_after_close"] = _trigger_aria_payload(
                        aria_after_close,
                    )
                    _assert_trigger_aria_expanded(
                        observation=aria_after_close,
                        expected_value="false",
                        step_number=6,
                        context="after dismissing the workspace switcher surface",
                    )
                except Exception as error:
                    normalized_error = _normalize_step_6_failure(error)
                    _record_step(
                        result,
                        step=6,
                        status="failed",
                        action=REQUEST_STEPS[5],
                        observed=str(normalized_error),
                    )
                    if normalized_error is error:
                        raise
                    raise normalized_error from None
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=REQUEST_STEPS[5],
                    observed=(
                        f"dashboard_visible={dismissal.dashboard_visible}; "
                        f"trigger_visible={dismissal.trigger_visible}; "
                        f"aria-expanded={aria_after_close.aria_expanded!r}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Clicked the trigger a second time and confirmed the switcher "
                        "disappeared from view while the trigger returned to its "
                        "collapsed ARIA state."
                    ),
                    observed=(
                        f"dashboard_visible={dismissal.dashboard_visible}; "
                        f"trigger_visible={dismissal.trigger_visible}; "
                        f"aria-expanded={aria_after_close.aria_expanded!r}"
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


def _assert_switcher_opened(
    *,
    switcher: WorkspaceSwitcherObservation,
) -> None:
    if "Workspace switcher" in switcher.switcher_text:
        return
    raise AssertionError(
        "Step 3 failed: clicking the workspace switcher trigger did not expose stable "
        "public evidence that the switcher became visible.\n"
        f"Observed switcher text:\n{switcher.switcher_text}",
    )


def _assert_trigger_aria_expanded(
    *,
    observation: WorkspaceTriggerAriaExpandedObservation,
    expected_value: str,
    step_number: int,
    context: str,
) -> None:
    if observation.aria_expanded == expected_value:
        return
    raise AssertionError(
        f"Step {step_number} failed: the workspace switcher trigger did not expose "
        f"aria-expanded={expected_value!r} {context}.\n"
        f"Observed label: {observation.label!r}\n"
        f"Observed role: {observation.role!r}\n"
        f"Observed aria-expanded: {observation.aria_expanded!r}\n"
        f"Observed trigger HTML: {observation.outer_html}",
    )


def _assert_dismissal_after_click(
    observation: WorkspaceSwitcherTriggerDismissObservation,
) -> None:
    failures: list[str] = []
    if not observation.trigger_visible:
        failures.append("the workspace switcher trigger was not visible after dismissal")
    if not observation.dashboard_visible:
        failures.append("the Dashboard view was not visible after dismissal")
    if failures:
        raise AssertionError(
            "Step 6 failed: clicking the workspace switcher trigger a second time did "
            "not restore the expected post-dismissal desktop view.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed trigger label after dismissal: {observation.trigger_label!r}\n"
            + f"Observed body text:\n{observation.body_text}",
        )


def _normalize_step_6_failure(error: Exception) -> Exception:
    message = str(error)
    expected_prefix = (
        "Step 4 failed: clicking the workspace switcher trigger a second time "
        "did not dismiss the panel."
    )
    if not message.startswith(expected_prefix):
        return error
    return AssertionError(message.replace("Step 4 failed", "Step 6 failed", 1))


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
    error = str(result.get("error", "AssertionError: TS-850 failed"))
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
    _write_review_replies(result, passed=False)
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
        "* Opened the deployed TrackState app in Chromium with a stored hosted token.",
        "* Located the visible desktop workspace switcher trigger on Dashboard.",
        "* Verified the trigger exposed aria-expanded=false while collapsed.",
        "* Clicked the trigger to open the workspace switcher and verified aria-expanded=true.",
        "* Clicked the trigger again to dismiss the switcher and verified aria-expanded=false.",
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
    lines.extend(
        [
            "",
            "h4. Test file",
            "{code}",
            "testing/tests/TS-850/test_ts_850.py",
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ],
    )
    lines.extend(_artifact_lines(result, jira=True))
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Review fixes",
        "",
        *[f"- {item}" for item in REWORK_FIXES],
        "",
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
        "- Located the visible desktop workspace switcher trigger on Dashboard.",
        "- Verified `aria-expanded=\"false\"` before mouse activation.",
        "- Clicked the trigger to open the switcher and verified `aria-expanded=\"true\"` while visible.",
        "- Clicked the trigger again to dismiss the switcher and verified `aria-expanded=\"false\"`.",
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
        "## Rework Summary",
        "",
        *[f"- Fixed: {item}" for item in REWORK_FIXES],
        f"- Re-ran `{RUN_COMMAND}`.",
        f"- Test case: **{TICKET_KEY} - {TEST_CASE_TITLE}**",
        f"- Result: **{status}**",
        (
            "- Outcome: the visible workspace switcher trigger started at "
            "`aria-expanded=\"false\"`, changed to `\"true\"` when the mouse click "
            "opened the surface, and returned to `\"false\"` when the second click "
            "dismissed it."
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
    title, reproduction_steps, missing_capability = _bug_context(result)
    return "\n".join(
        [
            f"# {title}",
            "",
            "## Steps to reproduce",
            *reproduction_steps,
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            _annotated_step_line(result, 5, REQUEST_STEPS[4]),
            _annotated_step_line(result, 6, REQUEST_STEPS[5]),
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
            missing_capability,
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
                    "trigger_aria_before_open": result.get("trigger_aria_before_open"),
                    "open_switcher_observation": result.get("open_switcher_observation"),
                    "open_panel_observation": result.get("open_panel_observation"),
                    "surface_observation": result.get("surface_observation"),
                    "trigger_aria_after_open": result.get("trigger_aria_after_open"),
                    "dismissal_observation": result.get("dismissal_observation"),
                    "trigger_aria_after_close": result.get("trigger_aria_after_close"),
                },
                indent=2,
            ),
            "```",
        ],
    ) + "\n"


def _bug_context(result: dict[str, object]) -> tuple[str, list[str], str]:
    failed_step = _first_failed_step_number(result)
    if failed_step == 1:
        return (
            f"{TICKET_KEY} - Workspace switcher trigger is not visible in the desktop Dashboard shell",
            [
                "1. Open the deployed TrackState app on a desktop browser.",
                "2. Navigate to Dashboard.",
                "3. Observe whether the workspace switcher trigger is visible and readable.",
            ],
            (
                "The production desktop UI does not expose a readable workspace "
                "switcher trigger in the visible Dashboard shell, so the mouse ARIA "
                "toggle scenario cannot begin."
            ),
        )
    if failed_step == 2:
        return (
            f"{TICKET_KEY} - Workspace switcher trigger exposes the wrong collapsed aria-expanded state",
            [
                "1. Open the deployed TrackState app on a desktop browser.",
                "2. Navigate to Dashboard.",
                "3. Inspect the workspace switcher trigger before activating it.",
            ],
            (
                "Before the workspace switcher opens, the production trigger does not "
                "report aria-expanded=\"false\" for the collapsed state."
            ),
        )
    if failed_step == 3:
        return (
            f"{TICKET_KEY} - Clicking the workspace switcher trigger does not open the surface",
            [
                "1. Open the deployed TrackState app on a desktop browser.",
                "2. Navigate to Dashboard.",
                "3. Click the workspace switcher trigger.",
                "4. Observe whether the workspace switcher surface opens.",
            ],
            (
                "When the user clicks the workspace switcher trigger, the production UI "
                "does not open the expected visible workspace switcher surface."
            ),
        )
    if failed_step == 4:
        return (
            f"{TICKET_KEY} - Workspace switcher trigger does not report aria-expanded=true while open",
            [
                "1. Open the deployed TrackState app on a desktop browser.",
                "2. Click the workspace switcher trigger to open the switcher.",
                "3. Inspect the trigger element while the surface is visible.",
            ],
            (
                "After the workspace switcher opens, the production trigger does not "
                "report aria-expanded=\"true\" for the expanded state."
            ),
        )
    if failed_step == 5:
        return (
            f"{TICKET_KEY} - The open workspace switcher trigger cannot be clicked again to collapse",
            [
                "1. Open the deployed TrackState app on a desktop browser.",
                "2. Click the workspace switcher trigger to open the switcher.",
                "3. Attempt to click the same trigger again.",
            ],
            (
                "Once the workspace switcher is open, the production UI does not allow "
                "the same trigger to be used for the second collapse click."
            ),
        )
    if failed_step == 6:
        return (
            f"{TICKET_KEY} - Workspace switcher does not restore collapsed aria-expanded state after mouse dismissal",
            [
                "1. Open the deployed TrackState app on a desktop browser.",
                "2. Click the workspace switcher trigger to open the switcher.",
                "3. Click the trigger again to dismiss the switcher.",
                "4. Inspect the trigger element after dismissal.",
            ],
            (
                "After the second click, the production UI does not both dismiss the "
                "workspace switcher and restore aria-expanded=\"false\" for the "
                "collapsed trigger state."
            ),
        )
    return (
        f"{TICKET_KEY} - Workspace switcher aria-expanded mouse toggle is broken",
        [
            "1. Open the deployed TrackState app on a desktop browser.",
            "2. Attempt the TS-850 mouse aria-expanded toggle scenario.",
            "3. Observe the first failing boundary.",
        ],
        (
            "The production desktop workspace switcher does not satisfy the TS-850 "
            "ARIA expanded-state toggle requirement for mouse interaction."
        ),
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
    if root_comment_id == 3264608568:
        return (
            "Fixed: Step 3 now uses stable visible workspace-switcher text as the "
            "open-state signal after the mouse click, and no longer requires a "
            "specific container kind, exact heading text, or visible row count. "
            + rerun_summary
        )
    if root_comment_id == 3264608689:
        return (
            "Fixed: the Step 6 close-path now normalizes the dismissal helper failure "
            "message so generated outputs and bug evidence report the failure as Step 6. "
            + rerun_summary
        )
    return "Fixed: addressed the TS-850 review feedback. " + rerun_summary


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


def _first_failed_step_number(result: dict[str, object]) -> int | None:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return None
    for step in steps:
        if isinstance(step, dict) and step.get("status") != "passed":
            return int(step.get("step", -1))
    return None


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


def _trigger_aria_payload(
    observation: WorkspaceTriggerAriaExpandedObservation,
) -> dict[str, object]:
    return {
        "label": observation.label,
        "role": observation.role,
        "tag_name": observation.tag_name,
        "tabindex": observation.tabindex,
        "keyboard_focusable": observation.keyboard_focusable,
        "aria_expanded": observation.aria_expanded,
        "outer_html": observation.outer_html,
    }


def _switcher_payload(observation: WorkspaceSwitcherObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "switcher_text": observation.switcher_text,
        "row_count": observation.row_count,
        "rows": [asdict(row) for row in observation.rows],
    }


def _snippet(text: str, *, max_length: int = 160) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."


if __name__ == "__main__":
    main()
