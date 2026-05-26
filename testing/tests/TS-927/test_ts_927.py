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
    MobileTriggerFocusObservation,
    WorkspaceSwitcherTriggerObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402
from testing.tests.support.stored_workspace_profiles_runtime import (  # noqa: E402
    StoredWorkspaceProfilesRuntime,
)

TICKET_KEY = "TS-927"
TEST_CASE_TITLE = (
    "Mobile keyboard Tab navigation — condensed workspace switcher trigger is reachable"
)
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-927/test_ts_927.py"
REQUEST_STEPS = [
    "Navigate to the mobile header using the keyboard.",
    "Press the Tab key repeatedly to cycle through the interactive elements in the header.",
    "Observe the focus sequence as it approaches the condensed workspace switcher trigger.",
]
EXPECTED_RESULT = (
    "Keyboard focus successfully lands on the condensed workspace switcher trigger "
    "in its logical order. The trigger must display a clearly defined focus-visible "
    "ring as specified in the fix."
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts927_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts927_failure.png"

HOSTED_TARGET = "IstiN/trackstate-setup"
LOCAL_TARGET = "/tmp/trackstate-demo"
DEFAULT_BRANCH = "main"
MOBILE_VIEWPORT_WIDTH = 375
MOBILE_VIEWPORT_HEIGHT = 844
MOBILE_TAB_COUNT = 24


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "app_url": "",
        "repository": "",
        "repository_ref": "",
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "expected_result": EXPECTED_RESULT,
        "viewport": {
            "width": MOBILE_VIEWPORT_WIDTH,
            "height": MOBILE_VIEWPORT_HEIGHT,
        },
        "preloaded_workspace_state": _workspace_state(HOSTED_TARGET, DEFAULT_BRANCH),
        "steps": [],
        "human_verification": [],
    }

    try:
        config = load_live_setup_test_config()
        service = LiveSetupRepositoryService(config=config)
        token = service.token
        workspace_state = _workspace_state(service.repository, service.ref)
        result.update(
            {
                "app_url": config.app_url,
                "repository": service.repository,
                "repository_ref": service.ref,
                "preloaded_workspace_state": workspace_state,
            },
        )
        if not token:
            raise RuntimeError(
                "TS-927 requires GH_TOKEN or GITHUB_TOKEN to open the deployed app.",
            )

        errors: list[str] = []

        with create_live_tracker_app(
            config,
            runtime_factory=lambda: StoredWorkspaceProfilesRuntime(
                repository=config.repository,
                token=token,
                workspace_state=workspace_state,
            ),
        ) as tracker_page:
            page = LiveWorkspaceSwitcherPage(tracker_page)
            page.set_viewport(
                width=MOBILE_VIEWPORT_WIDTH,
                height=MOBILE_VIEWPORT_HEIGHT,
            )
            runtime_state = tracker_page.open()
            result["runtime_state"] = runtime_state.kind
            result["runtime_body_text"] = runtime_state.body_text
            if runtime_state.kind != "ready":
                failure = (
                    "Step 1 failed: the deployed app did not reach the interactive "
                    "tracker shell in the mobile viewport before keyboard navigation "
                    "started.\n"
                    f"Observed runtime state: {runtime_state.kind}\n"
                    f"Observed body text:\n{runtime_state.body_text}"
                )
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=failure,
                )
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "The repeated Tab navigation step was not reachable because the "
                        "mobile tracker shell never finished loading."
                    ),
                )
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=(
                        "The focus-order and focus-ring check was not reachable because "
                        "the mobile tracker shell never finished loading."
                    ),
                )
                _record_human_verification(
                    result,
                    check="Viewed the deployed app in the mobile viewport before starting the keyboard sequence.",
                    observed=_snippet(runtime_state.body_text),
                )
                _capture_screenshot(page, FAILURE_SCREENSHOT_PATH, result)
                raise AssertionError(failure)

            trigger = page.observe_trigger()
            result["mobile_trigger_observation"] = asdict(trigger)
            _record_human_verification(
                result,
                check=(
                    "Viewed the condensed mobile header before keyboard navigation to "
                    "confirm the workspace switcher trigger was visible to the user."
                ),
                observed=_trigger_summary(trigger),
            )

            page.clear_focus()
            mobile_focus = page.observe_mobile_trigger_focus(
                tab_count=MOBILE_TAB_COUNT,
                timeout_ms=30_000,
            )
            result["mobile_trigger_focus_observation"] = asdict(mobile_focus)

            focus_started = len(mobile_focus.focus_sequence) > 0 and any(
                (step.after_label or "").strip() or (step.after_role or "").strip()
                for step in mobile_focus.focus_sequence
            )
            start_summary = _focus_sequence_summary(mobile_focus.focus_sequence)
            if focus_started:
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        "Starting from an unfocused page state, keyboard Tab navigation "
                        "entered the mobile header sequence. "
                        f"Observed focus sequence: {start_summary}"
                    ),
                )
            else:
                error = (
                    "Step 1 failed: keyboard navigation did not enter any visible mobile "
                    "header control from the page's unfocused state.\n"
                    f"Observed focus sequence: {start_summary}"
                )
                _record_step(
                    result,
                    step=1,
                    status="failed",
                    action=REQUEST_STEPS[0],
                    observed=error,
                )
                errors.append(error)

            trigger_step = _trigger_step_index(mobile_focus)
            if trigger_step is not None:
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action=REQUEST_STEPS[1],
                    observed=(
                        "Repeated Tab navigation reached the condensed workspace switcher "
                        f"trigger at Tab step {trigger_step}. Observed focus sequence: "
                        f"{start_summary}"
                    ),
                )
            else:
                error = (
                    "Step 2 failed: repeated Tab navigation in the mobile header never "
                    "reached the condensed workspace switcher trigger.\n"
                    f"{_mobile_focus_summary(mobile_focus)}"
                )
                _record_step(
                    result,
                    step=2,
                    status="failed",
                    action=REQUEST_STEPS[1],
                    observed=error,
                )
                errors.append(error)

            try:
                focus_summary = _assert_mobile_focus_result(mobile_focus)
            except AssertionError as error:
                observed = str(error)
                _record_step(
                    result,
                    step=3,
                    status="failed",
                    action=REQUEST_STEPS[2],
                    observed=observed,
                )
                errors.append(observed)
                _capture_screenshot(page, FAILURE_SCREENSHOT_PATH, result)
            else:
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=REQUEST_STEPS[2],
                    observed=focus_summary,
                )
                _capture_screenshot(page, SUCCESS_SCREENSHOT_PATH, result)

            _record_human_verification(
                result,
                check=(
                    "Viewed the condensed mobile trigger after tabbing like a keyboard "
                    "user and checked the visible focus treatment the user would see."
                ),
                observed=_mobile_focus_summary(mobile_focus),
            )

        if errors:
            raise AssertionError("\n\n".join(errors))
    except Exception as error:
        result.setdefault("error", _format_error(error))
        result.setdefault("traceback", traceback.format_exc())
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print("TS-927 passed")


def _workspace_state(repository: str, repository_ref: str) -> dict[str, object]:
    hosted_id = f"hosted:{repository.lower()}@{repository_ref}"
    local_id = f"local:{LOCAL_TARGET}@{repository_ref}"
    return {
        "activeWorkspaceId": hosted_id,
        "migrationComplete": True,
        "profiles": [
            {
                "id": hosted_id,
                "displayName": "",
                "targetType": "hosted",
                "target": repository,
                "defaultBranch": repository_ref,
                "writeBranch": repository_ref,
                "lastOpenedAt": "2026-05-13T12:00:00.000Z",
            },
            {
                "id": local_id,
                "displayName": "",
                "targetType": "local",
                "target": LOCAL_TARGET,
                "defaultBranch": repository_ref,
                "writeBranch": repository_ref,
                "lastOpenedAt": "2026-05-12T12:00:00.000Z",
            },
        ],
    }


def _trigger_step_index(observation: MobileTriggerFocusObservation) -> int | None:
    for step in observation.focus_sequence:
        if _is_workspace_trigger_label(step.after_label):
            return step.step
    return None


def _assert_mobile_focus_result(
    observation: MobileTriggerFocusObservation,
) -> str:
    if not _is_workspace_trigger_label(observation.active_label_after_focus):
        raise AssertionError(
            "Step 3 failed: the observed focus sequence never landed on the condensed "
            "workspace switcher trigger in the mobile header.\n"
            f"{_mobile_focus_summary(observation)}"
        )
    indicator_changed = any(
        before != after
        for before, after in (
            (observation.before_outline, observation.after_outline),
            (observation.before_outline_color, observation.after_outline_color),
            (observation.before_outline_width, observation.after_outline_width),
            (observation.before_box_shadow, observation.after_box_shadow),
        )
    )
    has_outline = _has_nonzero_outline(
        observation.after_outline,
        observation.after_outline_width,
    )
    has_box_shadow = _has_box_shadow(observation.after_box_shadow)
    if not has_outline and not has_box_shadow:
        raise AssertionError(
            "Step 3 failed: focus reached the condensed workspace switcher trigger, "
            "but the user-visible focus treatment was not clearly visible.\n"
            f"{_mobile_focus_summary(observation)}"
        )
    trigger_step = _trigger_step_index(observation)
    return (
        "The focus sequence reached the condensed workspace switcher trigger in "
        f"logical Tab order at step {trigger_step}, and the focused trigger exposed "
        "a visible outline or shadow-based focus ring. "
        f"focus_indicator_changed={indicator_changed}; "
        f"{_mobile_focus_summary(observation)}"
    )


def _has_nonzero_outline(outline: str, outline_width: str) -> bool:
    outline_normalized = outline.strip().lower()
    if not outline_normalized or outline_normalized == "none":
        return False
    width_normalized = outline_width.strip().lower()
    if width_normalized in {"", "0", "0px", "0px none rgb(0, 0, 0)"}:
        return False
    return "0px" not in width_normalized


def _has_box_shadow(box_shadow: str) -> bool:
    normalized = box_shadow.strip().lower()
    return bool(normalized) and normalized != "none"


def _focus_sequence_summary(sequence: tuple[FocusNavigationStep, ...]) -> str:
    if not sequence:
        return "<empty>"
    return " -> ".join(
        f"{step.step}:{step.after_label or step.after_role or '<none>'}"
        for step in sequence
    )


def _trigger_summary(observation: WorkspaceSwitcherTriggerObservation) -> str:
    return (
        f"viewport={int(observation.viewport_width)}x{int(observation.viewport_height)}; "
        f"semantic_label={observation.semantic_label!r}; "
        f"visible_text={observation.visible_text!r}; "
        f"position=({observation.left:.1f}, {observation.top:.1f}); "
        f"size=({observation.width:.1f}x{observation.height:.1f})"
    )


def _mobile_focus_summary(observation: MobileTriggerFocusObservation) -> str:
    return (
        f"focus_sequence={_focus_sequence_summary(observation.focus_sequence)}; "
        f"trigger_text={observation.trigger_text!r}; "
        f"active_after_focus={observation.active_label_after_focus!r}; "
        f"active_role_after_focus={observation.active_role_after_focus!r}; "
        f"active_tag_after_focus={observation.active_tag_name_after_focus!r}; "
        f"before_outline={observation.before_outline!r}; "
        f"before_outline_width={observation.before_outline_width!r}; "
        f"after_outline={observation.after_outline!r}; "
        f"after_outline_width={observation.after_outline_width!r}; "
        f"after_outline_color={observation.after_outline_color!r}; "
        f"after_box_shadow={observation.after_box_shadow!r}"
    )


def _is_workspace_trigger_label(label: str | None) -> bool:
    return bool(label and label.startswith("Workspace switcher:"))


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
        }
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


def _capture_screenshot(
    page: LiveWorkspaceSwitcherPage,
    path: Path,
    result: dict[str, object],
) -> None:
    path.unlink(missing_ok=True)
    try:
        page.screenshot(str(path))
    except Exception as error:
        result["screenshot_capture_error"] = _format_error(error)
        return
    if path.exists():
        result["screenshot"] = str(path)


def _format_error(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def _snippet(value: object, *, limit: int = 280) -> str:
    text = str(value).replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[:limit - 3]}..."


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
            }
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
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "h4. What was automated",
        (
            "* Opened the deployed TrackState web app in Chromium with preloaded hosted "
            "and local saved workspaces, then forced a 375x844 mobile viewport."
        ),
        (
            "* Drove keyboard Tab navigation from an unfocused page state and recorded "
            "the live focus sequence until the condensed workspace switcher trigger was "
            "reached or skipped."
        ),
        (
            "* Verified the focused trigger still showed a user-visible focus ring after "
            "focus landed on it."
        ),
        "",
        "h4. Result",
        (
            "* Matched the expected result."
            if passed
            else f"* Did not match the expected result. {_failure_summary(result)}"
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{result['os']}}}}}, "
            f"viewport {{{{{MOBILE_VIEWPORT_WIDTH}x{MOBILE_VIEWPORT_HEIGHT}}}}}."
        ),
        "",
        "h4. Step results",
        *_step_lines(result, jira=True),
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Run command",
        "{code:bash}",
        RUN_COMMAND,
        "{code}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code}",
                str(result.get("error", "")),
                "{code}",
            ]
        )
    if result.get("screenshot"):
        lines.extend(["", f"*Screenshot:* {{{{{result['screenshot']}}}}}"])
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status}",
        f"**Test Case:** {TICKET_KEY} — {TEST_CASE_TITLE}",
        "",
        "## What was automated",
        "- Opened the deployed TrackState web app in Chromium with preloaded hosted and local saved workspaces, then forced a 375x844 mobile viewport.",
        "- Drove keyboard Tab navigation from an unfocused page state and captured the live mobile focus sequence until the condensed workspace switcher trigger was reached or skipped.",
        "- Verified that the focused condensed trigger exposed a visible focus ring instead of only moving hidden/internal focus.",
        "",
        "## Result",
        (
            "- The observed behavior matched the expected result."
            if passed
            else f"- The observed behavior did not match the expected result. {_failure_summary(result)}"
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
    if result.get("screenshot"):
        lines.extend(["", f"**Screenshot:** `{result['screenshot']}`"])
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    return _pr_body(result, passed=passed)


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return []
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        status = "PASSED" if step.get("status") == "passed" else "FAILED"
        action = str(step.get("action", ""))
        observed = str(step.get("observed", ""))
        if jira:
            lines.append(
                f"* Step {step.get('step')}: *{status}* — {action} Observed: {observed}"
            )
        else:
            lines.append(
                f"- Step {step.get('step')}: **{status}** — {action} Observed: {observed}"
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list):
        return []
    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        if jira:
            lines.append(
                f"* {check.get('check')} Observed: {check.get('observed')}"
            )
        else:
            lines.append(
                f"- {check.get('check')} Observed: {check.get('observed')}"
            )
    return lines


def _failure_summary(result: dict[str, object]) -> str:
    failed_steps = [
        step
        for step in result.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "failed"
    ]
    if not failed_steps:
        return str(result.get("error", "Unknown failure"))
    first = failed_steps[0]
    return f"First failed step: {first.get('step')} — {first.get('observed')}"


def _failed_step_observations(result: dict[str, object]) -> list[str]:
    failed_steps = [
        step
        for step in result.get("steps", [])
        if isinstance(step, dict) and step.get("status") == "failed"
    ]
    observations: list[str] = []
    for step in failed_steps:
        step_number = step.get("step")
        observed = str(step.get("observed", "")).strip()
        if not observed:
            continue
        first_line = observed.splitlines()[0].strip()
        observations.append(f"Step {step_number}: {first_line}")
    if observations:
        return observations
    fallback_error = str(result.get("error", "")).strip()
    if fallback_error:
        return [fallback_error.splitlines()[0].strip()]
    return ["The run failed before the test could record step-level observations."]


def _bug_description(result: dict[str, object]) -> str:
    steps = result.get("steps", [])
    annotated_steps: list[str] = []
    for index, request_step in enumerate(REQUEST_STEPS, start=1):
        matching = next(
            (
                step
                for step in steps
                if isinstance(step, dict) and step.get("step") == index
            ),
            None,
        )
        if isinstance(matching, dict):
            icon = "✅" if matching.get("status") == "passed" else "❌"
            annotated_steps.append(
                f"{index}. {icon} {request_step}\n   Observed: {matching.get('observed')}"
            )
        else:
            annotated_steps.append(f"{index}. ❌ {request_step}\n   Observed: Not reached.")
    actual_lines = _failed_step_observations(result)
    return "\n".join(
        [
            f"# {TICKET_KEY} — {TEST_CASE_TITLE}",
            "",
            "## Steps to reproduce",
            *annotated_steps,
            "",
            "## Exact error message",
            "```",
            str(result.get("error", "")),
            "",
            str(result.get("traceback", "")),
            "```",
            "",
            "## Actual vs Expected",
            f"- **Expected:** {EXPECTED_RESULT}",
            "- **Actual:**",
            *[f"  - {line}" for line in actual_lines],
            "",
            "## Environment",
            f"- URL: {result.get('app_url', '')}",
            f"- Repository: {result.get('repository', '')} @ {result.get('repository_ref', '')}",
            f"- Browser: {result.get('browser', '')}",
            f"- OS: {result.get('os', '')}",
            f"- Viewport: {MOBILE_VIEWPORT_WIDTH}x{MOBILE_VIEWPORT_HEIGHT}",
            "",
            "## Logs and artifacts",
            f"- Screenshot: {result.get('screenshot', '<none>')}",
            "- Mobile trigger observation:",
            f"  {result.get('mobile_trigger_observation', {})}",
            "- Mobile focus observation:",
            f"  {result.get('mobile_trigger_focus_observation', {})}",
        ]
    ) + "\n"


if __name__ == "__main__":
    main()
