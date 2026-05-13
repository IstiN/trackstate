from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_create_issue_gate_page import (  # noqa: E402
    CreateIssueGateObservation,
    LiveCreateIssueGatePage,
)
from testing.components.pages.live_issue_detail_collaboration_page import (  # noqa: E402
    LiveIssueDetailCollaborationPage,
)
from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveHostedRepositoryMetadata,
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config  # noqa: E402
from testing.tests.support.live_tracker_app_factory import (  # noqa: E402
    create_live_tracker_app,
)
from testing.tests.support.read_only_hosted_session_runtime import (  # noqa: E402
    ReadOnlyHostedSessionObservation,
    ReadOnlyHostedSessionRuntime,
)

TICKET_KEY = "TS-371"
EXPECTED_CTA = "Open settings"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts371_success.png"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts371_failure.png"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-371 requires GH_TOKEN or GITHUB_TOKEN to open the hosted live app.",
        )

    metadata = service.fetch_demo_metadata()
    user = service.fetch_authenticated_user()
    _assert_preconditions(metadata)

    observation = ReadOnlyHostedSessionObservation(repository=service.repository)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "project_key": metadata.project_key,
        "project_name": metadata.project_name,
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app(
            config,
            runtime_factory=lambda: ReadOnlyHostedSessionRuntime(
                repository=service.repository,
                token=token,
                observation=observation,
            ),
        ) as tracker_page:
            access_page = LiveIssueDetailCollaborationPage(tracker_page)
            create_page = LiveCreateIssueGatePage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the Create issue access-gate scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )

                access_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                access_page.dismiss_connection_banner()
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the deployed hosted app and reach a connected hosted session.",
                    observed=(
                        f"runtime_state=ready; connected_user={user.login}; "
                        f"repository={service.repository}"
                    ),
                )

                create_trigger_body = create_page.wait_for_create_trigger()
                if "Create issue" not in create_trigger_body:
                    raise AssertionError(
                        "Step 2 failed: the top-bar shell did not expose the visible "
                        "`Create issue` action required by the test case.\n"
                        f"Observed body text:\n{create_trigger_body}",
                    )
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action='Locate the visible "Create issue" action in the top-bar shell.',
                    observed='create_button_visible=True; topbar_action_label="Create issue"',
                )

                create_page.open_create_issue()
                gate = create_page.wait_for_access_gate(
                    primary_action_label=EXPECTED_CTA,
                )
                result["gate_observation"] = _gate_payload(gate)
                result["permission_patch_observation"] = {
                    "intercepted_urls": list(observation.intercepted_urls),
                    "observed_permissions": list(observation.observed_permissions),
                }
                _assert_permission_patch_exercised(observation)
                _assert_gate_surface(gate)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "Click the Create trigger and verify the create flow renders a "
                        "guided gate panel instead of staying blank or silently doing nothing."
                    ),
                    observed=(
                        f'gate_panel_text="{gate.gate_panel_text}"; '
                        f"summary_field_count={gate.summary_field_count}; "
                        f"open_settings_button_count={gate.open_settings_button_count}; "
                        f"gate_open_settings_button_count={gate.gate_open_settings_button_count}"
                    ),
                )

                _assert_gate_guidance(gate)
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Inspect the gate panel for the contextual explanation of why "
                        "creation is blocked."
                    ),
                    observed=(
                        f"context_line_count={len(_descriptive_gate_lines(gate))}; "
                        f'explanation_text="{_gate_explanation_text(gate)}"; '
                        f'visible_cta="{EXPECTED_CTA}"'
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible Create issue surface showed a blocked-creation "
                        "explanation and the recovery CTA in the same gate panel a user sees "
                        "after clicking Create."
                    ),
                    observed=(
                        f'gate_panel_text="{gate.gate_panel_text}"; '
                        f'visible_cta="{EXPECTED_CTA}"'
                    ),
                )

                create_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)

                settings_body = create_page.open_settings_from_gate(gate)
                result["settings_body_text"] = settings_body
                _assert_settings_redirect(settings_body)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action=(
                        "Verify the recovery CTA points to the authentication/settings "
                        "surface."
                    ),
                    observed=(
                        f'clicked_cta="{EXPECTED_CTA}"; '
                        'settings_heading_visible=True; repository_access_visible=True'
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified clicking the visible Open settings CTA routed the user "
                        "to Project Settings with the Repository access section."
                    ),
                    observed=(
                        f'project_settings_visible={"Project Settings" in settings_body}; '
                        f'repository_access_visible={"Repository access" in settings_body}'
                    ),
                )

                _write_pass_outputs(result)
                return
            except Exception:
                create_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _assert_preconditions(metadata: LiveHostedRepositoryMetadata) -> None:
    if metadata.project_key != "DEMO":
        raise AssertionError(
            "Precondition failed: TS-371 expected the seeded DEMO hosted project.\n"
            f"Observed project key: {metadata.project_key}",
        )


def _assert_permission_patch_exercised(
    observation: ReadOnlyHostedSessionObservation,
) -> None:
    if observation.was_exercised:
        return
    raise AssertionError(
        "Precondition failed: the read-only hosted-session runtime never intercepted the "
        "repository permission request, so the live session was not proven to be read-only.",
    )


def _assert_gate_surface(gate: CreateIssueGateObservation) -> None:
    if not gate.create_heading_visible:
        raise AssertionError(
            "Step 3 failed: clicking `Create issue` did not render the Create issue "
            "surface heading.\n"
            f"Observed body text:\n{gate.body_text}",
        )
    if gate.gate_open_settings_button_count < 1:
        raise AssertionError(
            "Step 3 failed: the create issue gate did not expose a visible "
            f'`{EXPECTED_CTA}` recovery action.\n'
            f"Observed gate text: {gate.gate_panel_text}\n"
            f"Observed body text:\n{gate.body_text}",
        )


def _assert_gate_guidance(gate: CreateIssueGateObservation) -> None:
    explanation_text = _gate_explanation_text(gate)
    if "Create issue" not in gate.gate_panel_text or EXPECTED_CTA not in gate.gate_panel_text:
        raise AssertionError(
            "Step 4 failed: the Create issue gate did not keep the explanation panel and "
            "recovery CTA together in the same visible surface.\n"
            f"Observed gate text:\n{gate.gate_panel_text}",
        )
    if len(_descriptive_gate_lines(gate)) < 2 and len(explanation_text.split()) < 5:
        raise AssertionError(
            "Step 4 failed: the Create issue gate did not show enough contextual guidance "
            "to explain why creation is blocked.\n"
            f"Observed gate text:\n{gate.gate_panel_text}",
        )


def _assert_settings_redirect(settings_body: str) -> None:
    for fragment in ("Project Settings", "Repository access"):
        if fragment not in settings_body:
            raise AssertionError(
                "Step 5 failed: clicking the Create issue gate CTA did not route the user "
                "to the expected settings/authentication surface.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed body text:\n{settings_body}",
            )


def _normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def _descriptive_gate_lines(gate: CreateIssueGateObservation) -> list[str]:
    seen: set[str] = set()
    lines: list[str] = []
    for raw_line in gate.gate_panel_text.splitlines():
        line = _normalize_whitespace(raw_line)
        if not line:
            continue
        if line in {"Create issue", EXPECTED_CTA}:
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
    return lines


def _gate_explanation_text(gate: CreateIssueGateObservation) -> str:
    return " ".join(_descriptive_gate_lines(gate))


def _gate_payload(observation: CreateIssueGateObservation) -> dict[str, object]:
    return {
        "body_text": observation.body_text,
        "gate_panel_text": observation.gate_panel_text,
        "callout_semantics_label": observation.callout_semantics_label,
        "create_heading_visible": observation.create_heading_visible,
        "summary_field_count": observation.summary_field_count,
        "create_button_count": observation.create_button_count,
        "save_button_count": observation.save_button_count,
        "open_settings_button_count": observation.open_settings_button_count,
        "gate_open_settings_button_count": observation.gate_open_settings_button_count,
        "gate_cta_center_x": observation.gate_cta_center_x,
        "gate_cta_center_y": observation.gate_cta_center_y,
    }


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
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        "* Opened the deployed hosted TrackState app against the live setup repository.",
        "* Connected a hosted GitHub session and patched the live repository permission response to read-only so the production Create issue gate could be exercised.",
        '* Located and clicked the visible top-bar "Create issue" action.',
        "* Verified the Create issue surface showed a blocked-creation explanation and a visible Open settings recovery CTA.",
        "* Clicked the CTA and verified the user landed on Project Settings / Repository access.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the Create issue flow opened a guided recovery gate instead of silently failing or hiding the entry point."
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
        "- Opened the deployed hosted TrackState app against the live setup repository.",
        "- Connected a hosted GitHub session and patched the live repository permission response to read-only so the production Create issue gate could be exercised.",
        '- Located and clicked the visible top-bar "Create issue" action.',
        "- Verified the Create issue surface showed a blocked-creation explanation and a visible `Open settings` recovery CTA.",
        "- Clicked the CTA and verified the user landed on `Project Settings` / `Repository access`.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the Create issue flow opened a guided recovery gate instead of silently failing or hiding the entry point."
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
        "Ran the deployed hosted Create issue access-gate scenario with a connected read-only session.",
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
    lines = [
        f"# {TICKET_KEY} - Create issue guided recovery regression",
        "",
        "## Steps to reproduce",
        '1. Locate the "Create" action in the top-bar shell.',
        f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
        '2. Click the Create trigger.',
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "3. Verify that instead of a blank form or a silent failure, a gate panel is displayed.",
        f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
        "4. Inspect the gate panel for a contextual explanation of why creation is blocked.",
        f"   - {'✅' if _step_status(result, 4) == 'passed' else '❌'} {_step_observation(result, 4)}",
        "5. Verify the presence of a recovery CTA that points to the authentication/settings surface.",
        f"   - {'✅' if _step_status(result, 5) == 'passed' else '❌'} {_step_observation(result, 5)}",
        "",
        "## Actual vs Expected",
        (
            "- Expected: clicking Create issue in a connected read-only hosted session "
            "opens the Create issue surface with a contextual blocked-creation "
            "explanation and an Open settings CTA that routes to Project Settings."
        ),
        (
            "- Actual: "
            + str(
                result.get("error")
                or "the Create issue flow did not expose the expected guided recovery gate."
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
        "",
        "## Evidence",
        f"- Screenshot: `{result.get('screenshot', FAILURE_SCREENSHOT_PATH)}`",
        f"- Runtime state: `{result.get('runtime_state', '')}`",
        f"- Gate observation: `{result.get('gate_observation', {})}`",
        f"- Settings body text: `{result.get('settings_body_text', '')}`",
        f"- Permission patch observation: `{result.get('permission_patch_observation', {})}`",
    ]
    return "\n".join(lines) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — {step['status'].upper() if jira else step['status']}: {step['observed']}"
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
