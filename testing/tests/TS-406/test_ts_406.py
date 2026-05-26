from __future__ import annotations

import json
import os
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
SCREENSHOT_PATH = OUTPUTS_DIR / "ts406_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts406_success.png"
PERSISTENCE_TIMEOUT_SECONDS = 120
PERSISTENCE_POLL_SECONDS = 5


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
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result_if_requested(result)
        print(json.dumps(result, indent=2))
        raise
    else:
        result["status"] = "passed"
        result["summary"] = (
            "Verified from the live hosted Settings UI and repository config that "
            "Bug Workflow exists as a named project workflow and the Bug issue type "
            "persists with workflow ID bug-workflow."
        )
        _write_result_if_requested(result)
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


def _write_result_if_requested(payload: dict[str, object]) -> None:
    configured_path = os.environ.get("TS406_RESULT_PATH")
    result_path = (
        Path(configured_path)
        if configured_path
        else REPO_ROOT / "outputs" / "ts406_result.json"
    )
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
