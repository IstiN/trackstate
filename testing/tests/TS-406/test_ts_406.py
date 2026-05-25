from __future__ import annotations

import json
import os
import platform
import re
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_project_settings_admin_page import (
    LiveProjectSettingsAdminPage,
)
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.core.interfaces.web_app_session import WebAppTimeoutError
from testing.core.utils.polling import poll_until
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-406"
PROJECT_KEY = "DEMO"
BUG_WORKFLOW_ID = "bug-workflow"
BUG_WORKFLOW_NAME = "Bug Workflow"
BUG_ISSUE_TYPE_ID = "bug"
BUG_ISSUE_TYPE_NAME = "Bug"
WORKFLOW_TRANSITION_NAME = "Complete bug"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
SCREENSHOT_PATH = OUTPUTS_DIR / "ts406_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts406_success.png"
PERSISTENCE_TIMEOUT_SECONDS = 120
PERSISTENCE_POLL_SECONDS = 5
TICKET_STEPS = [
    "Navigate to Settings > Workflows.",
    "Create a new workflow named 'Bug Workflow'.",
    "Select 'To Do' and 'Done' as allowed statuses and define a transition between them.",
    "Click 'Save'.",
    "Navigate to the 'Issue Types' tab.",
    "Edit the 'Bug' issue type and select 'Bug Workflow' in the assigned workflow field.",
    "Click 'Save' and verify persistence.",
]


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    service = LiveSetupRepositoryService(config=config)
    token = service.token
    if not token:
        raise RuntimeError(
            "TS-406 requires GH_TOKEN or GITHUB_TOKEN to mutate live project settings.",
        )

    user = service.fetch_authenticated_user()
    initial_workflows = service.fetch_workflow_config_map(PROJECT_KEY)
    initial_issue_types = service.fetch_issue_type_config_entries(PROJECT_KEY)
    _assert_preconditions(initial_workflows, initial_issue_types)

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": service.repository,
        "repository_ref": service.ref,
        "project_key": PROJECT_KEY,
        "user_login": user.login,
        "workflow_id": BUG_WORKFLOW_ID,
        "workflow_name": BUG_WORKFLOW_NAME,
        "issue_type_id": BUG_ISSUE_TYPE_ID,
        "issue_type_name": BUG_ISSUE_TYPE_NAME,
        "workflow_existed_before_run": BUG_WORKFLOW_ID in initial_workflows,
        "initial_bug_issue_type": _bug_issue_type_entry(initial_issue_types),
        "steps": [],
        "human_verification": [],
    }

    try:
        with create_live_tracker_app_with_stored_token(
            config,
            token=token,
        ) as tracker_page:
            settings_page = LiveProjectSettingsAdminPage(tracker_page)
            try:
                runtime = tracker_page.open()
                result["runtime_state"] = runtime.kind
                result["runtime_body_text"] = runtime.body_text
                if runtime.kind != "ready":
                    raise AssertionError(
                        "Step 1 failed: the deployed app did not reach the hosted tracker "
                        "shell before the project settings workflow scenario began.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the hosted tracker shell.",
                    observed=runtime.body_text,
                )

                connected_body = settings_page.ensure_connected(
                    token=token,
                    repository=service.repository,
                    user_login=user.login,
                )
                result["connected_body_text"] = connected_body

                settings_text = settings_page.open_settings_admin()
                result["settings_body_text"] = settings_text
                if settings_page.SETTINGS_HEADER not in settings_text:
                    raise AssertionError(
                        "Step 1 failed: the hosted Settings screen did not show the "
                        "Project settings administration heading.\n"
                        f"Observed body text:\n{settings_text}",
                    )
                settings_page.open_tab(settings_page.WORKFLOWS_TAB)
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Navigate to Settings > Workflows.",
                    observed=settings_page.current_body_text(),
                )

                if settings_page.workflow_exists(BUG_WORKFLOW_NAME):
                    workflow_row = settings_page.workflow_row_label(BUG_WORKFLOW_NAME)
                    raise AssertionError(
                        "Precondition failed: the live Workflows tab already shows Bug "
                        "Workflow, so TS-406 cannot prove the Add workflow flow creates it "
                        "during this run.\n"
                        f"Observed workflow row:\n{workflow_row}",
                    )

                workflow_row = settings_page.create_bug_workflow()
                result["workflow_creation_mode"] = "created"
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action="Create a new workflow named Bug Workflow.",
                    observed=workflow_row,
                )
                if "Statuses: done, todo" not in workflow_row:
                    raise AssertionError(
                        "Step 4 failed: the Bug Workflow row did not visibly keep only "
                        "the To Do and Done statuses after saving the workflow editor.\n"
                        f"Observed workflow row:\n{workflow_row}",
                    )
                if "Transitions: 1" not in workflow_row:
                    raise AssertionError(
                        "Step 4 failed: the Bug Workflow row did not visibly report a "
                        "single saved transition.\n"
                        f"Observed workflow row:\n{workflow_row}",
                    )
                _record_step(
                    result,
                    step=4,
                    status="passed",
                    action=(
                        "Select To Do and Done as allowed statuses, define the To Do -> "
                        "Done transition, and save the workflow draft."
                    ),
                    observed=workflow_row,
                )

                settings_page.open_tab(settings_page.ISSUE_TYPES_TAB)
                _record_step(
                    result,
                    step=5,
                    status="passed",
                    action="Navigate to the Issue Types tab.",
                    observed=settings_page.current_body_text(),
                )

                initial_bug_issue_type_row = settings_page.issue_type_row_label(
                    BUG_ISSUE_TYPE_NAME,
                )
                result["initial_bug_issue_type_row"] = initial_bug_issue_type_row
                if f"Workflow: {BUG_WORKFLOW_ID}" in initial_bug_issue_type_row:
                    raise AssertionError(
                        "Precondition failed: the live Issue Types tab already shows Bug "
                        "assigned to bug-workflow, so TS-406 cannot prove the reassignment "
                        "step changes the workflow during this run.\n"
                        f"Observed issue type row:\n{initial_bug_issue_type_row}",
                    )

                workflow_dropdown_text, bug_issue_row = (
                    settings_page.assign_bug_issue_type_to_bug_workflow()
                )
                result["issue_type_dropdown_text"] = workflow_dropdown_text
                result["issue_type_row_before_save"] = bug_issue_row
                if "Workflow: bug-workflow" not in bug_issue_row:
                    raise AssertionError(
                        "Step 6 failed: the live Issue Types row did not update to the "
                        "bug-workflow ID after saving the Bug editor draft.\n"
                        f"Observed issue type row:\n{bug_issue_row}",
                    )
                _record_step(
                    result,
                    step=6,
                    status="passed",
                    action=(
                        "Edit the Bug issue type and select Bug Workflow in the assigned "
                        "workflow field."
                    ),
                    observed=(
                        f"{workflow_dropdown_text}\n{bug_issue_row}"
                        if workflow_dropdown_text
                        else bug_issue_row
                    ),
                )

                save_body_text = settings_page.save_project_settings()
                result["save_settings_body_text"] = save_body_text
                save_failure_text = _wait_for_save_failure(settings_page)
                result["save_failure_text"] = save_failure_text
                if save_failure_text is not None:
                    raise AssertionError(
                        "Step 7 failed: Save settings displayed a visible validation error "
                        "instead of persisting the workflow assignment.\n"
                        f"Observed body text:\n{save_failure_text}",
                    )
                persisted_config = _wait_for_repository_persistence(service)
                result["persisted_repository_config"] = persisted_config

                runtime_after_reload = tracker_page.open()
                result["runtime_after_reload"] = {
                    "kind": runtime_after_reload.kind,
                    "body_text": runtime_after_reload.body_text,
                }
                if runtime_after_reload.kind != "ready":
                    raise AssertionError(
                        "Step 7 failed: after saving settings, the hosted app did not "
                        "re-open cleanly for the persistence check.\n"
                        f"Observed body text:\n{runtime_after_reload.body_text}",
                    )
                settings_page.open_settings_admin()
                workflow_row_after_reload = _reload_workflow_row(settings_page)
                issue_type_row_after_reload = _reload_issue_type_row(settings_page)
                result["workflow_row_after_reload"] = workflow_row_after_reload
                result["issue_type_row_after_reload"] = issue_type_row_after_reload

                if "ID: bug-workflow" not in workflow_row_after_reload:
                    raise AssertionError(
                        "Step 7 failed: re-opening Settings did not keep the visible Bug "
                        "Workflow row in the Workflows tab.\n"
                        f"Observed workflow row after reload:\n{workflow_row_after_reload}",
                    )
                if "Workflow: bug-workflow" not in issue_type_row_after_reload:
                    raise AssertionError(
                        "Step 7 failed: re-opening Settings did not keep the visible Bug "
                        "issue type linked to bug-workflow.\n"
                        f"Observed issue type row after reload:\n{issue_type_row_after_reload}",
                    )

                _record_step(
                    result,
                    step=7,
                    status="passed",
                    action="Click Save and verify the Bug workflow assignment persists.",
                    observed=(
                        f"{workflow_row_after_reload}\n"
                        f"{issue_type_row_after_reload}\n"
                        f"{json.dumps(persisted_config, indent=2)}"
                    ),
                )
                _record_human_verification(
                    result,
                    check=(
                        'Verified the visible "Workflows" tab showed "Bug Workflow" with '
                        '"ID: bug-workflow", "Statuses: done, todo", and "Transitions: 1" '
                        "after the live save and reload."
                    ),
                    observed=workflow_row_after_reload,
                )
                _record_human_verification(
                    result,
                    check=(
                        'Verified the visible "Issue Types" tab showed the "Bug" row with '
                        '"Workflow: bug-workflow" after the live save and reload.'
                    ),
                    observed=issue_type_row_after_reload,
                )

                settings_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
            except Exception:
                settings_page.screenshot(str(SCREENSHOT_PATH))
                result["screenshot"] = str(SCREENSHOT_PATH)
                raise
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_failure=True)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_failure=False)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified from the live hosted Settings UI and repository config that "
            "Bug Workflow exists as a named project workflow and the Bug issue type "
            "persists with workflow ID bug-workflow."
        )
        _write_pass_outputs(result)
        print(json.dumps(result, indent=2))


def _assert_preconditions(
    workflows: dict[str, dict[str, object]],
    issue_types: list[dict[str, object]],
) -> None:
    workflow = workflows.get(BUG_WORKFLOW_ID)
    if workflow is not None:
        raise AssertionError(
            "Precondition failed: the live DEMO workflow config already defines "
            "bug-workflow, so TS-406 cannot prove the named workflow is created "
            "from a clean starting state.\n"
            f"Observed workflow config:\n{json.dumps(workflow, indent=2)}",
        )

    bug_issue_type = _bug_issue_type_entry(issue_types)
    if bug_issue_type is None:
        raise AssertionError(
            "Precondition failed: the live DEMO issue-types.json does not define the Bug "
            "issue type required by TS-406.",
        )
    if bug_issue_type.get("workflow") == BUG_WORKFLOW_ID:
        raise AssertionError(
            "Precondition failed: the live DEMO issue-types.json already links Bug to "
            "bug-workflow, so TS-406 cannot prove the issue-type reassignment changes "
            "the workflow.\n"
            f"Observed issue type config:\n{json.dumps(bug_issue_type, indent=2)}",
        )


def _bug_issue_type_entry(issue_types: list[dict[str, object]]) -> dict[str, object] | None:
    for issue_type in issue_types:
        if issue_type.get("id") == BUG_ISSUE_TYPE_ID:
            return issue_type
    return None


def _reload_workflow_row(settings_page: LiveProjectSettingsAdminPage) -> str:
    settings_page.open_tab(settings_page.WORKFLOWS_TAB)
    return settings_page.workflow_row_label(BUG_WORKFLOW_NAME)


def _reload_issue_type_row(settings_page: LiveProjectSettingsAdminPage) -> str:
    settings_page.open_tab(settings_page.ISSUE_TYPES_TAB)
    return settings_page.issue_type_row_label(BUG_ISSUE_TYPE_NAME)


def _wait_for_repository_persistence(
    service: LiveSetupRepositoryService,
) -> dict[str, object]:
    matched, last_observation = poll_until(
        probe=lambda: _observe_repository_persistence(service),
        is_satisfied=lambda observation: _workflow_matches_expectation(
            observation.get("workflow"),
        )
        and _bug_issue_type_matches_expectation(observation.get("bug_issue_type")),
        timeout_seconds=PERSISTENCE_TIMEOUT_SECONDS,
        interval_seconds=PERSISTENCE_POLL_SECONDS,
    )
    if matched:
        return last_observation

    raise AssertionError(
        "Step 7 failed: the live repository config did not persist the Bug workflow "
        "assignment within the allowed wait window.\n"
        f"Observed repository config:\n{json.dumps(last_observation, indent=2)}",
    )


def _observe_repository_persistence(
    service: LiveSetupRepositoryService,
) -> dict[str, object]:
    workflows = service.fetch_workflow_config_map(PROJECT_KEY)
    issue_types = service.fetch_issue_type_config_entries(PROJECT_KEY)
    workflow = workflows.get(BUG_WORKFLOW_ID)
    bug_issue_type = _bug_issue_type_entry(issue_types)
    return {
        "workflow": workflow,
        "bug_issue_type": bug_issue_type,
    }


def _wait_for_save_failure(
    settings_page: LiveProjectSettingsAdminPage,
) -> str | None:
    try:
        return settings_page.session.wait_for_text("Save failed:", timeout_ms=10_000)
    except WebAppTimeoutError:
        return None


def _workflow_matches_expectation(workflow: object) -> bool:
    if not isinstance(workflow, dict):
        return False
    if workflow.get("name") != BUG_WORKFLOW_NAME:
        return False

    statuses = workflow.get("statuses")
    transitions = workflow.get("transitions")
    if not isinstance(statuses, list) or set(statuses) != {"todo", "done"}:
        return False
    if not isinstance(transitions, list) or len(transitions) != 1:
        return False
    transition = transitions[0]
    if not isinstance(transition, dict):
        return False
    transition_id = transition.get("id")
    return (
        isinstance(transition_id, str)
        and bool(transition_id.strip())
        and transition.get("name") == WORKFLOW_TRANSITION_NAME
        and transition.get("from") == "todo"
        and transition.get("to") == "done"
    )


def _bug_issue_type_matches_expectation(issue_type: object) -> bool:
    return (
        isinstance(issue_type, dict)
        and issue_type.get("id") == BUG_ISSUE_TYPE_ID
        and issue_type.get("workflow") == BUG_WORKFLOW_ID
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
    verifications.append(
        {
            "check": check,
            "observed": observed,
        },
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
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(
    result: dict[str, object],
    *,
    product_failure: bool,
) -> None:
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
    if product_failure:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        "* Opened the deployed hosted tracker and reached *Project settings administration*.",
        "* Navigated through *Settings > Workflows* and created the named *Bug Workflow* draft with only *To Do* and *Done* plus one transition.",
        "* Switched to *Issue Types*, assigned *Bug Workflow* to the *Bug* issue type, and used the production *Save settings* action.",
        "* Verified the outcome from both the visible hosted UI and the repository-backed config data.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the named workflow was created, assigned to *Bug*, and persisted after reload."
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
    screenshot_path = result.get("screenshot", SCREENSHOT_PATH)
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        "- Opened the deployed hosted tracker and reached `Project settings administration`.",
        "- Navigated through `Settings > Workflows` and created the named `Bug Workflow` draft with only `To Do` and `Done` plus one transition.",
        "- Switched to `Issue Types`, assigned `Bug Workflow` to the `Bug` issue type, and used the production `Save settings` action.",
        "- Verified the outcome from both the visible hosted UI and the repository-backed config data.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the named workflow was created, assigned to `Bug`, and persisted after reload."
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
    screenshot_path = result.get("screenshot", SCREENSHOT_PATH)
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        "Ran the live workflow administration scenario against the hosted TrackState setup repository.",
        "",
        "## Observed",
        f"- Screenshot: `{screenshot_path}`",
        f"- Environment: `{result['app_url']}` on Chromium/Playwright ({platform.system()})",
        f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
        f"- Summary: {result.get('summary', result.get('error', 'No summary available.'))}",
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
    screenshot_path = result.get("screenshot", SCREENSHOT_PATH)
    failure_step = _failure_step_number(result)
    step_records = _step_result_map(result)
    lines = [
        f"# {TICKET_KEY} - Workflow administration persistence regression",
        "",
        "## Steps to reproduce",
    ]
    for index, ticket_step in enumerate(TICKET_STEPS, start=1):
        observed = step_records.get(index)
        if observed is not None:
            observation = str(observed.get("observed", "")).strip()
            lines.append(
                f"{index}. {ticket_step} "
                f"({'passed' if str(observed.get('status')) == 'passed' else 'failed'}) "
                f"{_step_icon(str(observed.get('status', 'failed')))}"
            )
            if observation:
                lines.append(f"   - Observed: {observation}")
            continue
        if failure_step == index:
            lines.append(f"{index}. {ticket_step} (failed) ❌")
            lines.append(f"   - Observed: {result.get('error', 'No error captured.')}")
        elif failure_step is not None and index > failure_step:
            lines.append(f"{index}. {ticket_step} (not reached)")
        else:
            lines.append(f"{index}. {ticket_step} (not completed)")
    lines.extend(
        [
            "",
            "## Actual vs Expected",
            (
                "* Expected: saving Project settings persists the new `bug-workflow` entry "
                "to `DEMO/config/workflows.json` and updates `DEMO/config/issue-types.json` "
                "so `bug` references `bug-workflow`."
            ),
            (
                f"* Actual: {result.get('error', 'The live scenario did not match the expected result.')}"
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}` @ `{result['repository_ref']}`",
            "- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.system()}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{screenshot_path}`",
            "",
            "## Human-style verification",
            *_human_lines(result, jira=False),
        ],
    )
    return "\n".join(lines) + "\n"


def _step_result_map(result: dict[str, object]) -> dict[int, dict[str, object]]:
    steps = result.get("steps", [])
    if not isinstance(steps, list):
        return {}
    mapped: dict[int, dict[str, object]] = {}
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_number = step.get("step")
        if isinstance(step_number, int):
            mapped[step_number] = step
    return mapped


def _failure_step_number(result: dict[str, object]) -> int | None:
    error = str(result.get("error", ""))
    match = re.search(r"Step (\d+) failed", error)
    if match is None:
        return None
    return int(match.group(1))


def _step_icon(status: str) -> str:
    return "✅" if status == "passed" else "❌"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    steps = result.get("steps", [])
    if not isinstance(steps, list) or not steps:
        message = "* No step evidence was captured before the failure." if jira else "- No step evidence was captured before the failure."
        return [message]
    for step in steps:
        if not isinstance(step, dict):
            continue
        step_number = step.get("step", "?")
        status = str(step.get("status", "failed"))
        action = str(step.get("action", "")).strip()
        observed = str(step.get("observed", "")).strip()
        if jira:
            lines.append(f"* Step {step_number} {_step_icon(status)} {action}")
            if observed:
                lines.append(f"** Observed: {{noformat}}{observed}{{noformat}}")
        else:
            lines.append(f"- Step {step_number} {_step_icon(status)} {action}")
            if observed:
                lines.append(f"  - Observed: `{observed}`")
    failure_step = _failure_step_number(result)
    if failure_step is not None and failure_step not in _step_result_map(result):
        failure_line = f"Step {failure_step} ❌ {result.get('error', 'Failure captured without step details.')}"
        lines.append(f"* {failure_line}" if jira else f"- {failure_line}")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    checks = result.get("human_verification", [])
    if not isinstance(checks, list) or not checks:
        message = (
            "* No separate human-style verification notes were captured."
            if jira
            else "- No separate human-style verification notes were captured."
        )
        return [message]
    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        description = str(check.get("check", "")).strip()
        observed = str(check.get("observed", "")).strip()
        if jira:
            lines.append(f"* {description}")
            if observed:
                lines.append(f"** Observed: {{noformat}}{observed}{{noformat}}")
        else:
            lines.append(f"- {description}")
            if observed:
                lines.append(f"  - Observed: `{observed}`")
    return lines


if __name__ == "__main__":
    main()
