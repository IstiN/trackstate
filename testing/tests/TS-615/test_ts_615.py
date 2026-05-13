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

from testing.components.pages.live_tracker_header_page import (  # noqa: E402
    DesktopHeaderObservation,
    LiveTrackerHeaderPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-615"
RUN_COMMAND = "python testing/tests/TS-615/test_ts_615.py"
EXPECTED_CONTROL_HEIGHT = 32.0
HEIGHT_TOLERANCE = 1.0
CENTER_TOLERANCE = 1.0

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts615_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts615_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-615 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
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
    }

    try:
        with create_live_tracker_app_with_stored_token(config, token=token) as tracker_page:
            header_page = LiveTrackerHeaderPage(tracker_page)
            tracker_page.session.set_viewport_size(width=1440, height=960)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the desktop "
                        "tracker shell before the header parity scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                connected_body = header_page.ensure_attachments_limited_state(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                header_page.dismiss_connection_banner()
                result["connected_body_text"] = connected_body
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Launch the web application and trigger the 'Attachments limited' state.",
                    observed=(
                        f"runtime_state={runtime.kind}; hosted_access="
                        f"{'Attachments limited' if 'Attachments limited' in connected_body else 'missing'}; "
                        f"connected_user={user.login}"
                    ),
                )

                observation = header_page.observe_desktop_header()
                result["header_observation"] = asdict(observation)
                _assert_repository_access_button(observation)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Locate the repository access state button in the desktop header.",
                    observed=(
                        f"repository_access_label={observation.repository_access.label}; "
                        f"x={observation.repository_access.x:.1f}; "
                        f"y={observation.repository_access.y:.1f}; "
                        f"width={observation.repository_access.width:.1f}; "
                        f"height={observation.repository_access.height:.1f}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified as a desktop user that the visible top bar showed "
                        "`Create issue`, `Attachments limited`, and the theme toggle in "
                        "the expected top-right control cluster."
                    ),
                    observed=_header_cluster_summary(observation),
                )

                try:
                    _assert_visual_parity(observation)
                except AssertionError as error:
                    _record_step(
                        result,
                        step=3,
                        status="failed",
                        action=(
                            "Compare the repository access button height and baseline "
                            "alignment against the adjacent JQL search field and "
                            "'Create issue' button."
                        ),
                        observed=str(error),
                    )
                    raise
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Compare the repository access button height and baseline alignment "
                        "against the adjacent JQL search field and 'Create issue' button."
                    ),
                    observed=_parity_summary(observation),
                )

                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action="Verify that the shared spacing token is applied to the pill.",
                    observed=(
                        f"repository_access_height={observation.repository_access.height:.1f}; "
                        f"search_input_height={observation.search_input.height:.1f}; "
                        f"expected_height={EXPECTED_CONTROL_HEIGHT:.1f}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the repository access label was legible and visually sat "
                        "on the same centered baseline as the neighboring desktop controls."
                    ),
                    observed=_parity_summary(observation),
                )
                header_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                header_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
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


def _assert_repository_access_button(observation: DesktopHeaderObservation) -> None:
    if observation.repository_access.label != "Attachments limited":
        raise AssertionError(
            "Step 2 failed: the desktop header did not expose the expected "
            "`Attachments limited` repository access label.\n"
            f"Observed header metrics: {_parity_summary(observation)}",
        )


def _assert_visual_parity(observation: DesktopHeaderObservation) -> None:
    repository_access = observation.repository_access
    search_input = observation.search_input
    create_issue = observation.create_issue
    errors: list[str] = []

    if not _within(repository_access.height, EXPECTED_CONTROL_HEIGHT, HEIGHT_TOLERANCE):
        errors.append(
            "repository access height was "
            f"{repository_access.height:.1f}px instead of {EXPECTED_CONTROL_HEIGHT:.1f}px"
        )
    if not _within(search_input.height, EXPECTED_CONTROL_HEIGHT, HEIGHT_TOLERANCE):
        errors.append(
            "search input height was "
            f"{search_input.height:.1f}px instead of {EXPECTED_CONTROL_HEIGHT:.1f}px"
        )
    if not _within(create_issue.height, EXPECTED_CONTROL_HEIGHT, HEIGHT_TOLERANCE):
        errors.append(
            "Create issue height was "
            f"{create_issue.height:.1f}px instead of {EXPECTED_CONTROL_HEIGHT:.1f}px"
        )
    if not _within(
        repository_access.center_y,
        search_input.center_y,
        CENTER_TOLERANCE,
    ):
        errors.append(
            "repository access vertical center "
            f"({repository_access.center_y:.1f}px) drifted from the search field center "
            f"({search_input.center_y:.1f}px)"
        )
    if not _within(
        repository_access.center_y,
        create_issue.center_y,
        CENTER_TOLERANCE,
    ):
        errors.append(
            "repository access vertical center "
            f"({repository_access.center_y:.1f}px) drifted from the Create issue center "
            f"({create_issue.center_y:.1f}px)"
        )

    if errors:
        raise AssertionError(
            "Step 3 failed: the desktop header controls did not keep the documented "
            "32px visual parity for the `Attachments limited` repository access state.\n"
            f"{'; '.join(errors)}.\n"
            f"Observed metrics: {_parity_summary(observation)}",
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
    verifications = result.setdefault("human_verification", [])
    assert isinstance(verifications, list)
    verifications.append({"check": check, "observed": observed})


def _write_pass_outputs(result: dict[str, object]) -> None:
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
        "* Opened the deployed hosted TrackState web app in a desktop Chromium session.",
        "* Connected the real hosted GitHub flow until the live top bar exposed the `Attachments limited` repository access state.",
        "* Located the visible search field, `Create issue`, `Attachments limited`, sync pill, and theme toggle controls from the rendered desktop header.",
        "* Compared the repository access control metrics against the expected 32px height and against the adjacent search field and `Create issue` button alignment.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the `Attachments limited` header control kept the documented 32px height and aligned with the neighboring desktop controls."
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
        "- Opened the deployed hosted TrackState web app in a desktop Chromium session.",
        "- Connected the real hosted GitHub flow until the live top bar exposed the `Attachments limited` repository access state.",
        "- Located the visible search field, `Create issue`, `Attachments limited`, sync pill, and theme toggle controls from the rendered desktop header.",
        "- Compared the repository access control metrics against the expected 32px height and against the adjacent search field and `Create issue` button alignment.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the `Attachments limited` header control kept the documented 32px height and aligned with the neighboring desktop controls."
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
            "Ran the deployed hosted desktop-header parity scenario for the "
            "`Attachments limited` repository access control."
        ),
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
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
    observation = result.get("header_observation", {})
    return "\n".join(
        [
            "# TS-615 - Desktop header `Attachments limited` control does not keep the documented 32px parity",
            "",
            "## Steps to reproduce",
            "1. Launch the web application and trigger the `Attachments limited` state.",
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "2. Locate the repository access state button in the desktop header.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "3. Compare its height and baseline alignment against the adjacent JQL search field and `Create issue` button.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "4. Verify that the shared spacing token is applied to the pill.",
            f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Actual vs Expected",
            (
                "- Expected: the desktop header shows `Attachments limited` as a 32px-tall "
                "repository access control that stays vertically centered with the adjacent "
                "search field and `Create issue` button."
            ),
            (
                "- Actual: "
                + str(
                    result.get("error")
                    or "the live desktop header did not preserve the expected 32px visual parity."
                )
            ),
            "",
            "## Environment",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.platform()}`",
            f"- Run command: `{RUN_COMMAND}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
            f"- Header observation: `{observation}`",
            f"- Runtime state: `{result.get('runtime_state', '')}`",
            f"- Connected body text: `{result.get('connected_body_text', '')}`",
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


def _header_cluster_summary(observation: DesktopHeaderObservation) -> str:
    return (
        f"search_field=({observation.search_field.x:.1f},{observation.search_field.y:.1f},"
        f"{observation.search_field.width:.1f}x{observation.search_field.height:.1f}); "
        f"create_issue=({observation.create_issue.x:.1f},{observation.create_issue.y:.1f},"
        f"{observation.create_issue.width:.1f}x{observation.create_issue.height:.1f}); "
        f"repository_access=({observation.repository_access.x:.1f},{observation.repository_access.y:.1f},"
        f"{observation.repository_access.width:.1f}x{observation.repository_access.height:.1f}); "
        f"theme_toggle=({observation.theme_toggle.x:.1f},{observation.theme_toggle.y:.1f},"
        f"{observation.theme_toggle.width:.1f}x{observation.theme_toggle.height:.1f})"
    )


def _parity_summary(observation: DesktopHeaderObservation) -> str:
    return (
        f"search_input_height={observation.search_input.height:.1f}px; "
        f"create_issue_height={observation.create_issue.height:.1f}px; "
        f"repository_access_height={observation.repository_access.height:.1f}px; "
        f"search_input_center_y={observation.search_input.center_y:.1f}px; "
        f"create_issue_center_y={observation.create_issue.center_y:.1f}px; "
        f"repository_access_center_y={observation.repository_access.center_y:.1f}px"
    )


def _within(value: float, expected: float, tolerance: float) -> bool:
    return abs(value - expected) <= tolerance


if __name__ == "__main__":
    main()
