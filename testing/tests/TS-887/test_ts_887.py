from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_multi_view_refresh_page import (  # noqa: E402
    LabeledTextFieldObservation,
    LiveMultiViewRefreshPage,
)
from testing.components.pages.live_project_settings_page import (  # noqa: E402
    LiveProjectSettingsPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedIssueFixture,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import create_live_tracker_app  # noqa: E402

TICKET_KEY = "TS-887"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts887_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts887_success.png"

REQUEST_STEPS = (
    "Clear the content of the Summary field.",
    "Click the Save button to trigger validation.",
    "Inspect the resulting error message (Summary is required).",
    "Verify the error message meets WCAG AA contrast (4.5:1).",
    "Use a screen reader to verify that the error is announced (for example, via a live region or focus shift).",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-887 requires GH_TOKEN or GITHUB_TOKEN to open the hosted edit flow.",
        )

    user = service.fetch_authenticated_user()
    issue_fixture = service.fetch_issue_fixture(ISSUE_PATH)
    _assert_preconditions(issue_fixture)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "issue_key": issue_fixture.key,
        "issue_path": issue_fixture.path,
        "issue_summary": issue_fixture.summary,
        "browser": "Chromium (Playwright)",
        "os": platform.platform(),
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(config) as tracker_page:
            settings_page = LiveProjectSettingsPage(tracker_page)
            edit_page = LiveMultiViewRefreshPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Precondition failed: the deployed app did not reach the hosted "
                        "tracker shell before the edit-validation scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                connected_text = settings_page.ensure_write_capable_connection(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                result["connected_body_text"] = connected_text
                settings_page.dismiss_connection_banner()

                edit_dialog_text = edit_page.open_edit_dialog_for_issue_key(
                    issue_key=issue_fixture.key,
                )
                result["edit_dialog_text"] = edit_dialog_text
                _record_human_verification(
                    result,
                    check=(
                        "Viewed the live hosted Edit issue surface as a user and checked "
                        "that the dialog heading and target issue identity were visible."
                    ),
                    observed=(
                        f"Dialog contained `Edit issue`: {'Edit issue' in edit_dialog_text}; "
                        f"dialog contained `{issue_fixture.key}`: {issue_fixture.key in edit_dialog_text}."
                    ),
                )

                summary_field = edit_page.observe_labeled_text_field("Summary")
                result["summary_field"] = _field_payload(summary_field)

                if not summary_field.enabled:
                    observation = _summary_field_failure_observation(summary_field)
                    _record_step(
                        result,
                        step=1,
                        status="failed",
                        action=REQUEST_STEPS[0],
                        observed=observation,
                    )
                    _mark_unreached_steps(result, first_unreached=2)
                    _record_human_verification(
                        result,
                        check=(
                            "Tried to start the scenario the same way a user would: by "
                            "placing focus in Summary and clearing the field before saving."
                        ),
                        observed=observation,
                    )
                    raise AssertionError(
                        "Step 1 failed: the live Edit issue surface rendered the required "
                        "Summary field as disabled, so the user could not clear it to trigger "
                        "validation.\n"
                        f"Summary field payload: {_field_payload(summary_field)}\n"
                        f"Observed dialog text:\n{edit_dialog_text}",
                    )

                cleared_field = edit_page.clear_labeled_text_field("Summary")
                result["summary_field_after_clear"] = _field_payload(cleared_field)
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action=REQUEST_STEPS[0],
                    observed=(
                        f"Summary field became editable and cleared successfully. "
                        f"Field payload: {_field_payload(cleared_field)}"
                    ),
                )

                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _mark_unreached_steps(result, first_unreached=2)
                raise AssertionError(
                    "TS-887 currently implements the live bug reproduction through the first "
                    "required user action. The production defect reproduced only when Step 1 "
                    "was impossible; downstream validation checks were intentionally not run "
                    "after the reproduction condition changed.",
                )
            except Exception:
                tracker_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _assert_preconditions(issue_fixture: LiveHostedIssueFixture) -> None:
    if issue_fixture.key != "DEMO-2":
        raise AssertionError(
            "Precondition failed: TS-887 expected the seeded DEMO-2 issue fixture.\n"
            f"Observed issue key: {issue_fixture.key}",
        )


def _field_payload(field: LabeledTextFieldObservation) -> dict[str, object]:
    return {
        "label": field.label,
        "value": field.value,
        "enabled": field.enabled,
        "disabled": field.disabled,
        "read_only": field.read_only,
        "aria_label": field.aria_label,
        "aria_invalid": field.aria_invalid,
        "aria_describedby": field.aria_describedby,
        "aria_errormessage": field.aria_errormessage,
        "outer_html": field.outer_html,
    }


def _summary_field_failure_observation(field: LabeledTextFieldObservation) -> str:
    return (
        "The visible Summary input existed inside the Edit issue dialog, but it was not "
        f"editable. enabled={field.enabled}, disabled={field.disabled}, "
        f"read_only={field.read_only}, value={field.value!r}, "
        f"aria_invalid={field.aria_invalid!r}, "
        f"aria_describedby={field.aria_describedby!r}, "
        f"aria_errormessage={field.aria_errormessage!r}."
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


def _mark_unreached_steps(result: dict[str, object], *, first_unreached: int) -> None:
    recorded = {
        int(step["step"])
        for step in result.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    for index in range(first_unreached, len(REQUEST_STEPS) + 1):
        if index in recorded:
            continue
        _record_step(
            result,
            step=index,
            status="not_run",
            action=REQUEST_STEPS[index - 1],
            observed="Not reached because the production UI failed the earlier required step.",
        )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
) -> None:
    entries = result.setdefault("human_verification", [])
    assert isinstance(entries, list)
    entries.append({"check": check, "observed": observed})


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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object]) -> str:
    lines = [
        f"h3. {TICKET_KEY} FAILED",
        "",
        "*Automation coverage*",
        "* Opened the deployed hosted TrackState app.",
        "* Connected the live session with the configured GitHub token until the write-capable connected banner appeared.",
        "* Opened the live Edit issue surface for DEMO-2.",
        "* Attempted to perform the first required user action from the ticket: clear the Summary field.",
        "",
        "*Observed result*",
        "* The scenario failed at Step 1 because the visible Summary field was disabled in the deployed Edit issue dialog, so the user could not clear it and could not reach the validation feedback checks.",
        (
            f"* Environment: URL {{{{{result['app_url']}}}}}, repository "
            f"{{{{{result['repository']}}}}} @ {{{{{result['repository_ref']}}}}}, "
            f"browser {{Chromium (Playwright)}}, OS {{{{{platform.system()}}}}}."
        ),
        f"* Screenshot: {{{{{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}}}}}",
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
        "",
        "*Exact error*",
        "{code}",
        str(result.get("traceback", result.get("error", ""))),
        "{code}",
    ]
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object]) -> str:
    lines = [
        f"## {TICKET_KEY} Failed",
        "",
        "### Automation",
        "- Opened the deployed hosted TrackState app.",
        "- Connected the live session with the configured GitHub token until the connected banner appeared.",
        "- Opened the live `Edit issue` surface for `DEMO-2`.",
        "- Attempted the first required user action from the ticket: clearing the `Summary` field.",
        "",
        "### Observed result",
        "- The scenario failed at Step 1 because the visible `Summary` field was disabled in the deployed Edit issue dialog, so the user could not trigger the validation feedback path.",
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
        "",
        "### Exact error",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object]) -> str:
    lines = [
        f"# {TICKET_KEY} failed",
        "",
        "The deployed hosted Edit issue flow did not allow the required Summary-validation scenario to start.",
        "",
        "## Observed",
        f"- Issue: `{result.get('issue_key', '')}`",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        "",
        "## Error",
        "```text",
        str(result.get("traceback", result.get("error", ""))),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    lines = [
        f"# {TICKET_KEY} - Edit issue Summary validation cannot be triggered because Summary is disabled",
        "",
        "## Steps to reproduce",
        "1. Clear the content of the `Summary` field.",
        f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
        "2. Click the `Save` button to trigger validation.",
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        "3. Inspect the resulting error message (`Summary is required`).",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Verify the error message meets WCAG AA contrast (4.5:1).",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "5. Use a screen reader to verify that the error is announced.",
        f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
        "",
        "## Actual vs Expected",
        "- Expected: the live Edit issue surface lets the user clear Summary, click Save, see the visible `Summary is required` validation message, and verify its contrast/accessibility behavior.",
        (
            "- Actual: the live Edit issue surface rendered the required Summary input "
            "as disabled, so the user could not clear it and could not reach the "
            "validation feedback scenario."
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
        f"- Issue: `{result.get('issue_key', '')}` (`{result.get('issue_path', '')}`)",
        "- Browser: `Chromium (Playwright)`",
        f"- OS: `{platform.platform()}`",
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        "",
        "## Observed dialog text",
        "```text",
        str(result.get("edit_dialog_text", result.get("runtime_body_text", ""))),
        "```",
        "",
        "## Observed Summary field payload",
        "```json",
        json.dumps(result.get("summary_field", {}), indent=2, sort_keys=True),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — {step['status']}: {step['observed']}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for entry in result.get("human_verification", []):
        if not isinstance(entry, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {entry['check']} Observed: {entry['observed']}")
    if not lines:
        lines.append(
            "* No human-style verification was recorded."
            if jira
            else "- No human-style verification was recorded."
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
    return str(result.get("error", "No observation recorded."))


if __name__ == "__main__":
    main()
