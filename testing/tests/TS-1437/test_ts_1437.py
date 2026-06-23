from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-1437"
TEST_CASE_TITLE = (
    "Connect GitHub button interactivity — button is clickable in hosted project settings"
)
RUN_COMMAND = "python testing/tests/TS-1437/test_ts_1437.py"
DESKTOP_VIEWPORT = {"width": 1440, "height": 960}
TOKEN_INPUT_LABEL = "Fine-grained token"

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1437_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts1437_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    SUCCESS_SCREENSHOT_PATH.unlink(missing_ok=True)
    FAILURE_SCREENSHOT_PATH.unlink(missing_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-1437 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
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
        "user_login": user.login,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
            viewport_width=DESKTOP_VIEWPORT["width"],
            viewport_height=DESKTOP_VIEWPORT["height"],
        ) as tracker_page:
            settings_page = LiveProjectSettingsPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted "
                        "tracker shell before the interactivity check began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the application in a hosted browser session.",
                    observed=f"runtime_state=ready; repository={service.repository}",
                )

                settings_page.dismiss_connection_banner()
                settings_body = settings_page.open_settings()
                result["settings_body"] = settings_body
                if "Project Settings" not in settings_body:
                    raise AssertionError(
                        "Step 2 failed: the hosted session did not navigate to the "
                        "Project Settings surface.\n"
                        f"Observed body text:\n{settings_body}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Navigate to Project Settings.",
                    observed="opened_view=Project Settings",
                )

                settings_page.open_connect_dialog()
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Click the Connect GitHub button in Project Settings.",
                    observed="Playwright successfully clicked the Project Settings Connect GitHub button via the page object.",
                )

                dialog_observation = settings_page.observe_connect_dialog()
                result["dialog_observation"] = dialog_observation
                _assert_connect_dialog_open(dialog_observation)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Verify the Connect GitHub dialog opened.",
                    observed=(
                        f'dialog_title_visible={dialog_observation["dialog_title_visible"]}; '
                        f'token_input_visible={dialog_observation["token_input_visible"]}; '
                        f'token_input_count={dialog_observation["token_input_count"]}; '
                        f'connect_token_visible={dialog_observation["connect_token_visible"]}; '
                        f'remember_visible={dialog_observation["remember_visible"]}; '
                        f'cancel_visible={dialog_observation["cancel_visible"]}'
                    ),
                )

                settings_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a real user would that clicking the hosted Project "
                        "Settings Connect GitHub button opens the connection dialog."
                    ),
                    observed=(
                        f'dialog_title_visible={dialog_observation["dialog_title_visible"]}; '
                        f'token_input_visible={dialog_observation["token_input_visible"]}'
                    ),
                )

                settings_page.dismiss_connect_dialog()
            except Exception:
                settings_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise

    _write_pass_outputs(result)
    print(f"{TICKET_KEY} passed")


def _assert_connect_dialog_open(observation: dict[str, object]) -> None:
    errors: list[str] = []
    if not observation["dialog_title_visible"]:
        errors.append(
            "The connection dialog title ('Connect GitHub' or 'Manage GitHub access') "
            "was not visible in the hosted body text."
        )
    if not observation["token_input_visible"]:
        errors.append(
            f"The '{TOKEN_INPUT_LABEL}' input was not visible after clicking Connect GitHub."
        )
    if observation["token_input_count"] != 1:
        errors.append(
            f"Expected exactly one '{TOKEN_INPUT_LABEL}' input, found {observation['token_input_count']}."
        )
    if errors:
        raise AssertionError(
            "Step 4 failed: clicking Connect GitHub did not open the expected connection dialog.\n"
            + "\n".join(errors)
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
    dialog = result.get("dialog_observation", {})
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        "* Opened the deployed hosted TrackState app in a browser-authenticated GitHub session.",
        "* Navigated to Project Settings.",
        f"* Clicked the {{Connect GitHub}} button using the same {{flt-semantics[role=\"button\"]}} selector that previously timed out in TS-495.",
        "* Verified the Connect GitHub dialog rendered with the Fine-grained token field.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the Connect GitHub button was clickable within the timeout and the connection dialog opened."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}"
        ),
        f"* Screenshot: {{{{{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}}}}}",
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
    if isinstance(dialog, dict):
        lines.extend(
            [
                "",
                "*Dialog observation*",
                f"* dialog_title_visible={dialog.get('dialog_title_visible')}",
                f"* token_input_visible={dialog.get('token_input_visible')}",
                f"* token_input_count={dialog.get('token_input_count')}",
            ],
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    dialog = result.get("dialog_observation", {})
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        "- Opened the deployed hosted TrackState app in a browser-authenticated GitHub session.",
        "- Navigated to Project Settings.",
        "- Clicked the `Connect GitHub` button using the same `flt-semantics[role=\"button\"]` selector that previously timed out in TS-495.",
        "- Verified the Connect GitHub dialog rendered with the Fine-grained token field.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the Connect GitHub button was clickable within the timeout and the connection dialog opened."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: URL `{result['app_url']}`, repository `{result['repository']}` "
            f"@ `{result['repository_ref']}`, browser `Chromium (Playwright)`, OS `{platform.system()}`."
        ),
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
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
    if isinstance(dialog, dict):
        lines.extend(
            [
                "",
                "### Dialog observation",
                f"- dialog_title_visible={dialog.get('dialog_title_visible')}",
                f"- token_input_visible={dialog.get('token_input_visible')}",
                f"- token_input_count={dialog.get('token_input_count')}",
            ],
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "passed" if passed else "failed"
    dialog = result.get("dialog_observation", {})
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        (
            "Verified the hosted Project Settings Connect GitHub button is clickable "
            "and opens the connection dialog."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
    ]
    if isinstance(dialog, dict):
        lines.extend(
            [
                f"- dialog_title_visible={dialog.get('dialog_title_visible')}",
                f"- token_input_visible={dialog.get('token_input_visible')}",
                f"- token_input_count={dialog.get('token_input_count')}",
            ],
        )
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
    dialog = result.get("dialog_observation", {})
    return "\n".join(
        [
            f"# {TICKET_KEY} - Connect GitHub button in hosted Project Settings is not clickable",
            "",
            "## Steps to reproduce",
            "1. Open the application in a hosted browser session.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Navigate to Project Settings.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Click the Connect GitHub button.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Verify the Connect GitHub dialog opened.",
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            "- Expected: the Project Settings Connect GitHub button is clickable within the timeout and opens the connection dialog.",
            "- Actual: the hosted button was not clickable or the dialog did not open.",
            "",
            "## Environment",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
            "- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            f"- Dialog observation: `{dialog}`",
        ],
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        status = str(step.get("status", "failed")).upper() if jira else step.get("status", "failed")
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — {status}: {step['observed']}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
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


if __name__ == "__main__":
    main()
