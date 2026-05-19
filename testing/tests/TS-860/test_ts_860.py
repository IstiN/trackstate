from __future__ import annotations

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
    WorkspaceSwitcherTriggerObservation,
    WorkspaceTriggerAriaControlsObservation,
    WorkspaceTriggerAriaControlsTargetObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-860"
TEST_CASE_TITLE = (
    "Initial application load - workspace switcher trigger has valid aria-controls attribute"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-860/test_ts_860.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
TRIGGER_ATTRIBUTE_TIMEOUT_MS = 4_000
LINKED_BUGS = ["TS-854"]

PRECONDITIONS = [
    "The deployed TrackState app is open in a desktop browser with Dashboard visible.",
    "A hosted GitHub token is available so the live app can render an interactive session.",
]
REQUEST_STEPS = [
    "Open the application and locate the workspace switcher trigger element.",
    "Inspect the DOM attributes of the trigger element without clicking it.",
    "Retrieve the value of the 'aria-controls' attribute.",
    "Search the DOM for an element with an 'id' that matches the 'aria-controls' value.",
    "Verify that the element exists in the DOM.",
]
EXPECTED_RESULT = (
    "The 'aria-controls' attribute is present on the trigger by default, and its value "
    "references an existing element ID in the DOM, ensuring the accessibility "
    "relationship is established prior to interaction."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts860_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts860_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-860 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
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
        "linked_bugs": LINKED_BUGS,
        "preconditions": PRECONDITIONS,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    page: LiveWorkspaceSwitcherPage | None = None
    failures: list[str] = []
    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            trigger: WorkspaceSwitcherTriggerObservation | None = None
            trigger_aria: WorkspaceTriggerAriaControlsObservation | None = None
            target: WorkspaceTriggerAriaControlsTargetObservation | None = None

            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach an interactive "
                        "desktop state before the initial aria-controls inspection began.\n"
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
                    "Viewed the desktop header and confirmed the visible workspace switcher "
                    "trigger was rendered before any interaction."
                ),
                observed=(
                    f"trigger_text={trigger.visible_text!r}; "
                    f"display_name={trigger.display_name!r}; "
                    f"state_label={trigger.state_label!r}"
                ),
            )

            try:
                trigger_aria = page.observe_trigger_aria_controls(
                    timeout_ms=TRIGGER_ATTRIBUTE_TIMEOUT_MS,
                )
                result["trigger_aria_controls_observation"] = _trigger_aria_payload(
                    trigger_aria,
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
                    f"label={trigger_aria.label!r}; "
                    f"aria-controls={trigger_aria.aria_controls!r}; "
                    f"role={trigger_aria.role!r}; "
                    f"tabindex={trigger_aria.tabindex!r}"
                ),
            )

            try:
                _assert_trigger_aria_controls_present(trigger_aria)
            except AssertionError as error:
                failures.append(str(error))
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=str(error),
                )
            else:
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        f"Trigger exposed aria-controls={trigger_aria.aria_controls!r} "
                        "on initial page load before the switcher was opened."
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Inspected the visible trigger before any click and confirmed the "
                        "accessibility attribute was already present."
                    ),
                    observed=f"aria-controls={trigger_aria.aria_controls!r}",
                )

            try:
                target = page.observe_trigger_aria_controls_target(
                    timeout_ms=TRIGGER_ATTRIBUTE_TIMEOUT_MS,
                )
                result["trigger_aria_controls_target_observation"] = _target_payload(target)
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
                    f"trigger_aria_controls={target.trigger_aria_controls!r}; "
                    f"controlled_element_found={target.controlled_element_found}; "
                    f"controlled_element_id={target.controlled_element_id!r}; "
                    f"controlled_element_role={target.controlled_element_role!r}; "
                    f"controlled_element_tag={target.controlled_element_tag_name!r}"
                ),
            )

            try:
                _assert_trigger_target_exists(target)
            except AssertionError as error:
                failures.append(str(error))
                _record_step(
                    result,
                    step=5,
                    status="failed",
                    action=REQUEST_STEPS[4],
                    observed=str(error),
                )
            else:
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=REQUEST_STEPS[4],
                    observed=(
                        f"Found DOM element id={target.controlled_element_id!r} for "
                        f"aria-controls={target.trigger_aria_controls!r}; "
                        f"visible={target.controlled_element_visible}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the pre-interaction accessibility relationship an auditor "
                        "would care about: the trigger already pointed at a real DOM node."
                    ),
                    observed=(
                        f"aria-controls={target.trigger_aria_controls!r}; "
                        f"controlled_element_id={target.controlled_element_id!r}; "
                        f"controlled_element_role={target.controlled_element_role!r}"
                    ),
                )

            if failures:
                _capture_failure_screenshot(page, result)
                raise AssertionError("\n\n".join(failures))

            page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
            result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        if page is not None:
            try:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        if page is not None:
            try:
                page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
            except Exception as screenshot_error:
                result["screenshot_error"] = (
                    f"{type(screenshot_error).__name__}: {screenshot_error}"
                )
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _assert_trigger_aria_controls_present(
    observation: WorkspaceTriggerAriaControlsObservation,
) -> None:
    if observation.aria_controls:
        return
    raise AssertionError(
        "Step 3 failed: the workspace switcher trigger did not expose an aria-controls "
        "attribute on initial page load.\n"
        f"Observed label: {observation.label!r}\n"
        f"Observed role: {observation.role!r}\n"
        f"Observed aria-controls: {observation.aria_controls!r}\n"
        f"Observed trigger HTML: {observation.outer_html}",
    )


def _assert_trigger_target_exists(
    observation: WorkspaceTriggerAriaControlsTargetObservation,
) -> None:
    failures: list[str] = []
    if not observation.trigger_aria_controls:
        failures.append(
            "the trigger aria-controls attribute was missing, so no matching DOM id could be checked",
        )
    if (
        observation.trigger_aria_controls
        and not observation.controlled_element_found
    ):
        failures.append(
            f"no DOM element with id {observation.trigger_aria_controls!r} existed before interaction",
        )
    if (
        observation.trigger_aria_controls
        and observation.controlled_element_id
        and observation.controlled_element_id != observation.trigger_aria_controls
    ):
        failures.append(
            "the DOM element returned by the initial aria-controls lookup did not preserve "
            f"the same id ({observation.controlled_element_id!r} != "
            f"{observation.trigger_aria_controls!r})",
        )
    if failures:
        raise AssertionError(
            "Step 5 failed: the workspace switcher trigger aria-controls value did not "
            "reference an existing DOM element before interaction.\n"
            + "\n".join(f"- {item}" for item in failures)
            + "\n"
            + f"Observed trigger aria-controls: {observation.trigger_aria_controls!r}\n"
            + f"Observed controlled element id: {observation.controlled_element_id!r}\n"
            + f"Observed controlled element role/tag: {observation.controlled_element_role!r} / "
            + f"{observation.controlled_element_tag_name!r}\n"
            + f"Observed controlled element text: {_snippet(observation.controlled_element_text)!r}\n"
            + f"Observed trigger HTML: {observation.trigger_outer_html}\n"
            + f"Observed controlled element HTML: {observation.controlled_element_outer_html}",
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


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = str(result.get("error", "AssertionError: TS-860 failed"))
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
        "* Located the visible workspace switcher trigger on Dashboard before any interaction.",
        "* Inspected the trigger DOM attributes without clicking the trigger.",
        "* Read the trigger's aria-controls value on initial page load.",
        "* Queried the live DOM for the element referenced by aria-controls and verified it already existed.",
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
        "- Located the visible workspace switcher trigger on Dashboard before any interaction.",
        "- Inspected the trigger DOM attributes without clicking the trigger.",
        "- Read the trigger `aria-controls` value on initial page load.",
        "- Queried the live DOM for the element referenced by `aria-controls` and verified it already existed.",
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
            "- Added TS-860 live desktop coverage for the workspace switcher trigger "
            "aria-controls relationship on initial page load."
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
            "- Outcome: the visible workspace switcher trigger exposed aria-controls and "
            "the referenced DOM element already existed before interaction."
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
            f"# {TICKET_KEY} - Workspace switcher trigger does not expose a valid initial aria-controls DOM reference",
            "",
            "## Steps to reproduce",
            "1. Open the deployed TrackState app on a desktop browser and navigate to Dashboard.",
            "2. Locate the visible workspace switcher trigger in the header without clicking it.",
            "3. Inspect the trigger element attributes and read the aria-controls value.",
            "4. Search the DOM for an element whose id equals the aria-controls value.",
            "5. Verify that the referenced element exists before any interaction.",
            "",
            "## Exact steps from the test case with observations",
            _annotated_step_line(result, 1, REQUEST_STEPS[0]),
            _annotated_step_line(result, 2, REQUEST_STEPS[1]),
            _annotated_step_line(result, 3, REQUEST_STEPS[2]),
            _annotated_step_line(result, 4, REQUEST_STEPS[3]),
            _annotated_step_line(result, 5, REQUEST_STEPS[4]),
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
                    "trigger_aria_controls_observation": result.get(
                        "trigger_aria_controls_observation",
                    ),
                    "trigger_aria_controls_target_observation": result.get(
                        "trigger_aria_controls_target_observation",
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


def _failed_step_summary(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("status") != "passed":
                return f"Step {step.get('step')}: {step.get('observed')}"
    return str(result.get("error", "No failed step recorded."))


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


def _trigger_aria_payload(
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


def _target_payload(
    observation: WorkspaceTriggerAriaControlsTargetObservation,
) -> dict[str, object]:
    return {
        "trigger_label": observation.trigger_label,
        "trigger_aria_controls": observation.trigger_aria_controls,
        "controlled_element_found": observation.controlled_element_found,
        "controlled_element_visible": observation.controlled_element_visible,
        "controlled_element_id": observation.controlled_element_id,
        "controlled_element_role": observation.controlled_element_role,
        "controlled_element_tag_name": observation.controlled_element_tag_name,
        "controlled_element_text": observation.controlled_element_text,
        "trigger_outer_html": observation.trigger_outer_html,
        "controlled_element_outer_html": observation.controlled_element_outer_html,
    }


def _snippet(text: str, *, max_length: int = 160) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_length:
        return normalized
    return normalized[: max_length - 3] + "..."


if __name__ == "__main__":
    main()
