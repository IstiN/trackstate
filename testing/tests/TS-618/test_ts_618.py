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

from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
    RepositoryAccessControlsObservation,
    RepositoryAccessFocusObservation,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-618"
RUN_COMMAND = "python testing/tests/TS-618/test_ts_618.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts618_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts618_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-618 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    user = service.fetch_authenticated_user()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
        "focus_sequence": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            settings_page = LiveProjectSettingsPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the repository access reverse-tab scenario started.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                connected_text = settings_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                result["connected_text"] = connected_text
                settings_page.dismiss_connection_banner()

                settings_body = settings_page.open_settings()
                result["settings_body"] = settings_body
                controls = settings_page.observe_repository_access_controls()
                result["repository_access_controls"] = asdict(controls)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Navigate to Project Settings → Repository access.",
                    observed=(
                        f"project_settings_visible={controls.project_settings_visible}; "
                        f"repository_access_visible={controls.repository_access_visible}; "
                        f"visible_controls={_visible_controls_summary(controls)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the live Project Settings screen visibly showed the "
                        "Repository access section together with the Fine-grained token "
                        "field, the Remember on this browser checkbox, and the Connect "
                        "token button."
                    ),
                    observed=_snippet(controls.section_text or controls.body_text),
                )

                settings_page.focus_repository_access_connect_token()
                try:
                    initial_focus = settings_page.wait_for_repository_access_focus(
                        "Connect token",
                        timeout_ms=5_000,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=2,
                        status="failed",
                        action="Focus the Connect token button.",
                        observed=str(error),
                    )
                    raise AssertionError(
                        "Step 2 failed: focusing the visible Connect token button did not "
                        "leave keyboard focus on that button.\n"
                        f"{error}",
                    ) from None
                _append_focus_observation(result, step=2, observation=initial_focus)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Focus the Connect token button.",
                    observed=_focus_summary(initial_focus),
                )

                settings_page.press_shift_tab_from_repository_access_focus("Connect token")
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Press Shift + Tab.",
                    observed="Sent Shift+Tab from the Connect token button.",
                )
                try:
                    first_shift_tab_focus = settings_page.wait_for_repository_access_focus(
                        "Remember on this browser",
                        timeout_ms=5_000,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=4,
                        status="failed",
                        action="Observe the focus indicator location.",
                        observed=str(error),
                    )
                    raise AssertionError(
                        "Step 4 failed: after pressing Shift+Tab from the Connect token "
                        "button, focus did not move to the visible Remember on this "
                        "browser checkbox.\n"
                        f"{error}",
                    ) from None
                _append_focus_observation(result, step=4, observation=first_shift_tab_focus)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Observe the focus indicator location.",
                    observed=_focus_summary(first_shift_tab_focus),
                )

                settings_page.press_shift_tab_from_repository_access_focus(
                    "Remember on this browser"
                )
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Press Shift + Tab again.",
                    observed="Sent Shift+Tab from the Remember on this browser checkbox.",
                )
                try:
                    second_shift_tab_focus = settings_page.wait_for_repository_access_focus(
                        "Fine-grained token",
                        timeout_ms=5_000,
                    )
                except AssertionError as error:
                    _record_step(
                        result,
                        step=6,
                        status="failed",
                        action="Observe the focus indicator location.",
                        observed=str(error),
                    )
                    raise AssertionError(
                        "Step 6 failed: after pressing Shift+Tab again, focus did not move "
                        "to the visible Fine-grained token input field.\n"
                        f"{error}",
                    ) from None
                _append_focus_observation(
                    result,
                    step=6,
                    observation=second_shift_tab_focus,
                )
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action="Observe the focus indicator location.",
                    observed=_focus_summary(second_shift_tab_focus),
                )

                settings_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a keyboard user that focus stayed inside the visible "
                        "Repository access controls and moved backward in sequence from "
                        "Connect token to Remember on this browser and then to Fine-grained "
                        "token."
                    ),
                    observed=_focus_sequence_summary(result),
                )
            except Exception:
                settings_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
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
    print(f"{TICKET_KEY} passed")


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


def _append_focus_observation(
    result: dict[str, object],
    *,
    step: int,
    observation: RepositoryAccessFocusObservation,
) -> None:
    sequence = result.setdefault("focus_sequence", [])
    assert isinstance(sequence, list)
    sequence.append(
        {
            "step": step,
            "label": observation.label,
            "tag_name": observation.tag_name,
            "role": observation.role,
            "accessible_name": observation.accessible_name,
            "text": observation.text,
            "outer_html": observation.outer_html,
        }
    )


def _visible_controls_summary(observation: RepositoryAccessControlsObservation) -> str:
    visible = []
    if observation.fine_grained_token_visible:
        visible.append("Fine-grained token")
    if observation.remember_on_this_browser_visible:
        visible.append("Remember on this browser")
    if observation.connect_token_visible:
        visible.append("Connect token")
    return ", ".join(visible) if visible else "<none>"


def _focus_summary(observation: RepositoryAccessFocusObservation) -> str:
    return (
        f"focused_label={observation.label}; "
        f"tag={observation.tag_name}; "
        f"role={observation.role}; "
        f"accessible_name={observation.accessible_name!r}"
    )


def _focus_sequence_summary(result: dict[str, object]) -> str:
    parts: list[str] = []
    for item in result.get("focus_sequence", []):
        if not isinstance(item, dict):
            continue
        parts.append(f"Step {item.get('step')}: {item.get('label')}")
    return " -> ".join(parts) if parts else "<no focus sequence recorded>"


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
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            "* Opened the deployed hosted TrackState app in Chromium using the configured "
            "GitHub token and navigated to *Project Settings → Repository access*."
        ),
        (
            "* Verified the visible repository-access controls included {{Fine-grained "
            "token}}, {{Remember on this browser}}, and {{Connect token}}."
        ),
        (
            "* Focused the visible {{Connect token}} button and checked live keyboard "
            "reverse traversal with {{Shift + Tab}} reached the visible checkbox first "
            "and the visible token field second."
        ),
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the first {{Shift + Tab}} moved focus to "
            "{{Remember on this browser}} and the second {{Shift + Tab}} moved focus to "
            "{{Fine-grained token}} without skipping either control."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
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
            ]
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
            "- Opened the deployed hosted TrackState app in Chromium using the configured "
            "GitHub token and navigated to `Project Settings → Repository access`."
        ),
        (
            "- Verified the visible repository-access controls included `Fine-grained "
            "token`, `Remember on this browser`, and `Connect token`."
        ),
        (
            "- Focused the visible `Connect token` button and checked live keyboard "
            "reverse traversal with `Shift+Tab` reached the visible checkbox first and "
            "the visible token field second."
        ),
        "",
        "### Observed result",
        (
            "- Matched the expected result: the first `Shift+Tab` moved focus to "
            "`Remember on this browser` and the second `Shift+Tab` moved focus to "
            "`Fine-grained token` without skipping either control."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
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
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation result*",
        (
            "* Verified reverse keyboard traversal in the live {{Project Settings → "
            "Repository access}} section from {{Connect token}} to {{Remember on this "
            "browser}} to {{Fine-grained token}}."
        ),
        (
            "* Result: "
            + (
                "PASSED — focus moved backward through the expected visible controls."
                if passed
                else f"FAILED — {result.get('error', 'the live reverse focus order did not match the expected sequence.')}"
            )
        ),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "# TS-618 - Reverse tab navigation from Connect token does not reach Remember and token input in order",
            "",
            "## Steps to reproduce",
            "1. Navigate to Project Settings → Repository access.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Focus the `Connect token` button (either by clicking it or tabbing to it).",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Press the Shift + Tab keys simultaneously.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Observe the focus indicator location.",
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "5. Press the Shift + Tab keys simultaneously again.",
            f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
            "6. Observe the focus indicator location.",
            f"   - {'✅' if _step_status(result, 6) == 'passed' else '❌'} {_step_observation(result, 6)}",
            "",
            "## Actual vs Expected",
            (
                "- Expected: after the `Connect token` button has focus, the first "
                "`Shift+Tab` press should move focus to `Remember on this browser` and "
                "the second `Shift+Tab` press should move focus to `Fine-grained token`, "
                "while all three controls stay visibly present in the Repository access "
                "section."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the hosted Repository access reverse keyboard traversal did not follow the expected order."
                )
            ),
            "",
            "## Missing or broken production capability",
            (
                "- The hosted Repository access focus traversal does not move backward "
                "from the visible `Connect token` button through the visible "
                "`Remember on this browser` checkbox to the visible `Fine-grained token` "
                "field after real page-level `Shift+Tab` keypresses."
            ),
            "",
            "## Failing command and output",
            f"- Command: `{RUN_COMMAND}`",
            f"- Result JSON: `{RESULT_PATH}`",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment details",
            f"- URL: `{result.get('app_url')}`",
            f"- Repository: `{result.get('repository')}` @ `{result.get('repository_ref')}`",
            "- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            "### Runtime body text",
            "```text",
            str(result.get("runtime_body_text", "")),
            "```",
            "### Project Settings body text",
            "```text",
            str(result.get("settings_body", "")),
            "```",
            "### Repository access control snapshot",
            "```json",
            json.dumps(result.get("repository_access_controls", {}), indent=2),
            "```",
            "### Focus sequence",
            "```json",
            json.dumps(result.get("focus_sequence", []), indent=2),
            "```",
        ]
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        status = str(step.get("status", "failed"))
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{status.upper() if jira else status}: {step['observed']}"
        )
    if not lines:
        lines.append(
            "# No step details were recorded."
            if jira
            else "1. No step details were recorded."
        )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for check in result.get("human_verification", []):
        if not isinstance(check, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(f"{prefix} {check.get('check')}: {check.get('observed')}")
    if not lines:
        lines.append(
            "# No human-style verification data was recorded."
            if jira
            else "1. No human-style verification data was recorded."
        )
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and int(step.get("step", -1)) == step_number:
            return str(step.get("observed", "No observation recorded."))
    previous_step = step_number - 1
    if previous_step >= 1 and _step_status(result, previous_step) != "passed":
        return (
            f"Not reached because Step {previous_step} failed: "
            f"{_step_observation(result, previous_step)}"
        )
    return str(result.get("error", "No observation recorded."))


def _snippet(value: object, *, limit: int = 400) -> str:
    collapsed = " ".join(str(value).split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


if __name__ == "__main__":
    main()
