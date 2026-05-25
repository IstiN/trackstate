from __future__ import annotations

import json
import os
from pathlib import Path
import platform
import sys
import traceback
import uuid

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.pages.live_project_settings_page import (
    LiveProjectSettingsPage,
    ProjectSettingsUiObservation,
)
from testing.components.services.hosted_project_settings_repository_service import (
    HostedCommitObservation,
    HostedProjectSettingsRepositoryService,
)
from testing.components.services.hosted_trackstate_session_cli_service import (
    HostedTrackStateSessionCliService,
)
from testing.components.services.live_setup_repository_service import (
    LiveSetupRepositoryService,
)
from testing.core.config.live_setup_test_config import load_live_setup_test_config
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.utils.polling import poll_until
from testing.tests.support.hosted_trackstate_session_cli_probe_factory import (
    create_hosted_trackstate_session_cli_probe,
)
from testing.tests.support.github_repository_file_page_factory import (
    create_github_repository_file_page,
)
from testing.tests.support.live_tracker_app_factory import (
    create_live_tracker_app_with_stored_token,
)

TICKET_KEY = "TS-409"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts409_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts409_success.png"
STATUSES_SCREENSHOT_PATH = OUTPUTS_DIR / "ts409_statuses_commit.png"
WORKFLOWS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts409_workflows_commit.png"
STATUSES_PATH = "DEMO/config/statuses.json"
WORKFLOWS_PATH = "DEMO/config/workflows.json"
WORKFLOW_NAME = "Delivery Workflow"
WORKFLOW_ID = "delivery-workflow"
REQUEST_STEPS = (
    "Navigate to Settings Admin Workspace.",
    "Make changes in 'Statuses' (Add new) and 'Workflows' (Update transition).",
    "Click 'Save'.",
    "Verify the resulting Git commit.",
    "Execute `trackstate session` via CLI.",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_live_setup_test_config()
    live_service = LiveSetupRepositoryService(config=config)
    token = live_service.token
    if not token:
        raise RuntimeError(
            "TS-409 requires GH_TOKEN or GITHUB_TOKEN to drive the hosted Settings flow.",
        )

    repository_service = HostedProjectSettingsRepositoryService(
        repository=config.repository,
        branch=config.ref,
        token=token,
    )
    cli_service = HostedTrackStateSessionCliService(
        create_hosted_trackstate_session_cli_probe(REPO_ROOT)
    )
    user = live_service.fetch_authenticated_user()
    baseline_statuses = repository_service.fetch_file(STATUSES_PATH, ref=config.ref)
    baseline_workflows = repository_service.fetch_file(WORKFLOWS_PATH, ref=config.ref)
    baseline_head_sha = repository_service.branch_head_sha()

    suffix = uuid.uuid4().hex[:8]
    status_id = f"ts-409-status-{suffix}"
    status_name = f"TS-409 Status {suffix}"
    transition_name = f"TS-409 Reopen {suffix}"
    transition_index = _resolve_delivery_transition_index(baseline_workflows.content)

    result: dict[str, object] = {
        "status": "failed",
        "ticket": TICKET_KEY,
        "app_url": config.app_url,
        "repository": config.repository,
        "repository_ref": config.ref,
        "baseline_head_sha": baseline_head_sha,
        "expected_status_id": status_id,
        "expected_status_name": status_name,
        "expected_transition_name": transition_name,
        "steps": [],
        "human_verification": [],
    }

    mutation_attempted = False
    cleanup_commit_sha: str | None = None
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
                        "shell before the Settings scenario started.\n"
                        f"Observed body text:\n{runtime.body_text}",
                    )
                _record_step(
                    result,
                    step=1,
                    status="passed",
                    action="Open the deployed app and reach the hosted tracker shell.",
                    observed=runtime.body_text,
                )

                connected_text = settings_page.ensure_connected(
                    token=token,
                    repository=config.repository,
                    user_login=user.login,
                )
                result["connected_text"] = connected_text
                settings_page.dismiss_connection_banner()
                _record_step(
                    result,
                    step=2,
                    status="passed",
                    action="Connect the hosted session with a fine-grained token.",
                    observed=connected_text,
                )

                ui_observation = _perform_settings_mutation(
                    settings_page=settings_page,
                    status_id=status_id,
                    status_name=status_name,
                    workflow_name=WORKFLOW_NAME,
                    transition_name=transition_name,
                    transition_index=transition_index,
                )
                tracker_page.screenshot(str(SUCCESS_SCREENSHOT_PATH))
                result["ui_observation"] = _ui_observation_to_dict(ui_observation)
                result["settings_screenshot"] = str(SUCCESS_SCREENSHOT_PATH)
                _record_step(
                    result,
                    step=3,
                    status="passed",
                    action=(
                        "In Settings, add a new status, update the Delivery Workflow "
                        "transition label, and save the settings."
                    ),
                    observed=ui_observation.post_save_text,
                )
                _record_human_verification(
                    result,
                    check=(
                        "Verified the visible hosted settings flow exposed the user-facing "
                        "`Project Settings`, `Add status`, `Workflows`, `Edit workflow`, "
                        "and `Save settings` surfaces before and after saving."
                    ),
                    observed=_human_ui_observation_text(ui_observation),
                )
            except Exception:
                settings_page.screenshot(str(FAILURE_SCREENSHOT_PATH))
                result["screenshot"] = str(FAILURE_SCREENSHOT_PATH)
                raise

        mutation_attempted = True
        new_head_sha = repository_service.wait_for_head_change(baseline_head_sha)
        commit_observation = repository_service.fetch_commit(new_head_sha)
        result["commit_observation"] = _commit_observation_to_dict(commit_observation)
        result["new_head_sha"] = new_head_sha
        _assert_commit_observation(
            baseline_head_sha=baseline_head_sha,
            commit_observation=commit_observation,
        )
        _record_step(
            result,
            step=4,
            status="passed",
            action="Verify the resulting Git commit for the hosted settings save.",
            observed=json.dumps(_commit_observation_to_dict(commit_observation), indent=2),
        )

        committed_statuses = repository_service.fetch_file(STATUSES_PATH, ref=new_head_sha)
        committed_workflows = repository_service.fetch_file(WORKFLOWS_PATH, ref=new_head_sha)
        result["committed_statuses_content"] = committed_statuses.content
        result["committed_workflows_content"] = committed_workflows.content
        _assert_committed_configuration(
            statuses_content=committed_statuses.content,
            workflows_content=committed_workflows.content,
            status_id=status_id,
            status_name=status_name,
            transition_name=transition_name,
        )

        file_page_observations = _verify_files_in_github_ui(
            repository=config.repository,
            commit_sha=new_head_sha,
            status_name=status_name,
            transition_name=transition_name,
        )
        result["github_ui_verification"] = file_page_observations
        _record_human_verification(
            result,
            check=(
                "Verified the committed GitHub file views visibly showed the new status "
                "and updated Delivery Workflow transition in the saved repository state."
            ),
            observed=_human_commit_observation_text(file_page_observations),
        )

        cli_result = _run_session_until_project_config(
            cli_service=cli_service,
            repository=config.repository,
            branch=config.ref,
            status_marker=status_name,
            workflow_marker=transition_name,
        )
        result["cli_observation"] = {
            "command": cli_result.command_text,
            "exit_code": cli_result.exit_code,
            "stdout": cli_result.stdout,
            "stderr": cli_result.stderr,
            "json_payload": cli_result.json_payload,
        }
        _record_step(
            result,
            step=5,
            status="passed",
            action="Run `trackstate session` for the same hosted repository.",
            observed=cli_result.stdout,
        )
        _record_human_verification(
            result,
            check=(
                "Verified the installed `trackstate session` CLI output for the same "
                "hosted repository exposed the saved status and workflow markers inside "
                "the returned `projectConfig` block."
            ),
            observed=_human_cli_observation_text(cli_result),
        )
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _record_failed_step_from_error(result)
        _write_failure_outputs(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise
    finally:
        if mutation_attempted:
            try:
                current_statuses = repository_service.fetch_file(STATUSES_PATH, ref=config.ref)
                current_workflows = repository_service.fetch_file(WORKFLOWS_PATH, ref=config.ref)
                if (
                    current_statuses.content != baseline_statuses.content
                    or current_workflows.content != baseline_workflows.content
                ):
                    cleanup_commit_sha = repository_service.restore_settings(
                        statuses_content=baseline_statuses.content,
                        workflows_content=baseline_workflows.content,
                        message=f"Restore {TICKET_KEY} hosted settings fixture",
                    )
            except Exception as cleanup_error:  # pragma: no cover - best-effort cleanup
                result["cleanup_error"] = (
                    f"{type(cleanup_error).__name__}: {cleanup_error}"
                )
            else:
                if cleanup_commit_sha is not None:
                    result["cleanup_commit_sha"] = cleanup_commit_sha

    result["status"] = "passed"
    result["summary"] = (
        "Verified that the hosted Settings flow wrote the status and workflow "
        "changes in one commit and that the hosted CLI session output exposed the "
        "updated projectConfig data immediately afterward."
    )
    _write_pass_outputs(result)
    print(json.dumps(result, indent=2))


def _perform_settings_mutation(
    *,
    settings_page: LiveProjectSettingsPage,
    status_id: str,
    status_name: str,
    workflow_name: str,
    transition_name: str,
    transition_index: int,
) -> ProjectSettingsUiObservation:
    settings_text = settings_page.open_settings()
    status_dialog_text, status_list_text = settings_page.add_status(
        status_id=status_id,
        status_name=status_name,
    )
    workflow_tab_text = settings_page.open_workflows_tab()
    workflow_dialog_text, workflow_tab_text = settings_page.update_workflow_transition_name(
        workflow_name=workflow_name,
        transition_index=transition_index,
        transition_name=transition_name,
    )
    post_save_text = settings_page.save_settings()
    return ProjectSettingsUiObservation(
        settings_text=settings_text,
        status_dialog_text=status_dialog_text,
        status_list_text=status_list_text,
        workflow_dialog_text=workflow_dialog_text,
        workflow_tab_text=workflow_tab_text,
        post_save_text=post_save_text,
    )


def _resolve_delivery_transition_index(workflows_content: str) -> int:
    payload = json.loads(workflows_content)
    if not isinstance(payload, dict) or WORKFLOW_ID not in payload:
        raise AssertionError(
            "Precondition failed: the hosted repository no longer exposes the "
            f"{WORKFLOW_ID!r} workflow.\nObserved workflows.json:\n{workflows_content}",
        )
    workflow = payload[WORKFLOW_ID]
    if not isinstance(workflow, dict):
        raise AssertionError(
            "Precondition failed: the Delivery Workflow entry is not a JSON object.\n"
            f"Observed workflows.json:\n{workflows_content}",
        )
    transitions = workflow.get("transitions")
    if not isinstance(transitions, list) or len(transitions) < 4:
        raise AssertionError(
            "Precondition failed: TS-409 expected the Delivery Workflow to expose at "
            "least four transitions so the existing 'Reopen' transition can be updated.\n"
            f"Observed workflows.json:\n{workflows_content}",
        )
    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            continue
        if str(transition.get("id", "")).strip() == "reopen":
            return index
    for index, transition in enumerate(transitions):
        if not isinstance(transition, dict):
            continue
        if str(transition.get("name", "")).strip().lower() == "reopen":
            return index
    raise AssertionError(
        "Precondition failed: TS-409 expected the Delivery Workflow to expose an "
        "existing `Reopen` transition to edit.\n"
        f"Observed workflows.json:\n{workflows_content}",
    )


def _assert_commit_observation(
    *,
    baseline_head_sha: str,
    commit_observation: HostedCommitObservation,
) -> None:
    if len(commit_observation.parent_shas) != 1:
        raise AssertionError(
            "Step 4 failed: the resulting head commit was not a single atomic commit "
            "for the hosted settings save.\n"
            f"Observed parent SHAs: {list(commit_observation.parent_shas)}\n"
            f"Observed commit: {json.dumps(_commit_observation_to_dict(commit_observation), indent=2)}",
        )
    if commit_observation.parent_shas[0] != baseline_head_sha:
        raise AssertionError(
            "Step 4 failed: the resulting head commit was not a direct atomic child "
            "of the pre-save repository head.\n"
            f"Expected parent: {baseline_head_sha}\n"
            f"Observed commit: {json.dumps(_commit_observation_to_dict(commit_observation), indent=2)}",
        )
    expected_files = {STATUSES_PATH, WORKFLOWS_PATH}
    changed_files = set(commit_observation.changed_files)
    missing_files = sorted(expected_files - changed_files)
    if missing_files:
        raise AssertionError(
            "Step 4 failed: the settings save commit did not include both modified "
            "catalog files.\n"
            f"Missing files: {missing_files}\n"
            f"Observed commit: {json.dumps(_commit_observation_to_dict(commit_observation), indent=2)}",
        )


def _assert_committed_configuration(
    *,
    statuses_content: str,
    workflows_content: str,
    status_id: str,
    status_name: str,
    transition_name: str,
) -> None:
    if status_id not in statuses_content or status_name not in statuses_content:
        raise AssertionError(
            "Step 4 failed: the committed statuses.json file did not contain the new "
            "status saved from the Settings UI.\n"
            f"Expected status id: {status_id}\n"
            f"Expected status name: {status_name}\n"
            f"Observed statuses.json:\n{statuses_content}",
        )
    if transition_name not in workflows_content:
        raise AssertionError(
            "Step 4 failed: the committed workflows.json file did not contain the "
            "updated transition label saved from the Settings UI.\n"
            f"Expected transition name: {transition_name}\n"
            f"Observed workflows.json:\n{workflows_content}",
        )


def _verify_files_in_github_ui(
    *,
    repository: str,
    commit_sha: str,
    status_name: str,
    transition_name: str,
) -> dict[str, object]:
    with create_github_repository_file_page() as file_page:
        statuses_observation = file_page.open_file(
            repository=repository,
            branch=commit_sha,
            file_path=STATUSES_PATH,
            expected_texts=(status_name, "statuses.json"),
            screenshot_path=str(STATUSES_SCREENSHOT_PATH),
            timeout_seconds=60,
        )
        workflows_observation = file_page.open_file(
            repository=repository,
            branch=commit_sha,
            file_path=WORKFLOWS_PATH,
            expected_texts=(transition_name, "workflows.json"),
            screenshot_path=str(WORKFLOWS_SCREENSHOT_PATH),
            timeout_seconds=60,
        )
    return {
        "statuses_file": {
            "url": statuses_observation.url,
            "matched_text": statuses_observation.matched_text,
            "screenshot_path": statuses_observation.screenshot_path,
            "body_text": statuses_observation.body_text,
        },
        "workflows_file": {
            "url": workflows_observation.url,
            "matched_text": workflows_observation.matched_text,
            "screenshot_path": workflows_observation.screenshot_path,
            "body_text": workflows_observation.body_text,
        },
    }


def _run_session_until_project_config(
    *,
    cli_service: HostedTrackStateSessionCliService,
    repository: str,
    branch: str,
    status_marker: str,
    workflow_marker: str,
    attempts: int = 12,
    interval_seconds: float = 5.0,
) -> CliCommandResult:
    matched, last_result = poll_until(
        probe=lambda: cli_service.run_session(
            repository=repository,
            branch=branch,
        ),
        is_satisfied=lambda result: _session_result_has_project_config_markers(
            result,
            status_marker=status_marker,
            workflow_marker=workflow_marker,
        ),
        timeout_seconds=attempts * interval_seconds,
        interval_seconds=interval_seconds,
    )
    if matched:
        return last_result
    if not last_result.succeeded:
        raise AssertionError(
            "Step 5 failed: `trackstate session` did not complete successfully "
            "against the hosted repository after the Settings save.\n"
            f"Command: {last_result.command_text}\n"
            f"Exit code: {last_result.exit_code}\n"
            f"stdout:\n{last_result.stdout}\n"
            f"stderr:\n{last_result.stderr}",
        )
    payload = last_result.json_payload
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 5 failed: `trackstate session` did not emit a JSON object.\n"
            f"stdout:\n{last_result.stdout}\n"
            f"stderr:\n{last_result.stderr}",
        )
    data = payload.get("data")
    if not isinstance(data, dict):
        raise AssertionError(
            "Step 5 failed: the session payload did not expose a `data` object.\n"
            f"Observed payload: {json.dumps(payload, indent=2)}",
        )
    payload = (
        last_result.json_payload
        if isinstance(last_result.json_payload, dict)
        else {"stdout": last_result.stdout}
    )
    raise AssertionError(
        "Step 5 failed: the hosted CLI session output did not expose an updated "
        "`projectConfig` block with the saved status catalog and workflow summary.\n"
        f"Expected status marker: {status_marker}\n"
        f"Expected workflow marker: {workflow_marker}\n"
        f"Observed payload: {json.dumps(payload, indent=2)}",
    )


def _session_result_has_project_config_markers(
    result: CliCommandResult,
    *,
    status_marker: str,
    workflow_marker: str,
) -> bool:
    if not result.succeeded:
        return False
    payload = result.json_payload
    if not isinstance(payload, dict):
        return False
    data = payload.get("data")
    if not isinstance(data, dict):
        return False
    project_config = data.get("projectConfig")
    if not isinstance(project_config, dict):
        return False
    project_config_text = json.dumps(project_config, sort_keys=True)
    return status_marker in project_config_text and workflow_marker in project_config_text


def _ui_observation_to_dict(observation: ProjectSettingsUiObservation) -> dict[str, object]:
    return {
        "settings_text": observation.settings_text,
        "status_dialog_text": observation.status_dialog_text,
        "status_list_text": observation.status_list_text,
        "workflow_dialog_text": observation.workflow_dialog_text,
        "workflow_tab_text": observation.workflow_tab_text,
        "post_save_text": observation.post_save_text,
    }


def _commit_observation_to_dict(observation: HostedCommitObservation) -> dict[str, object]:
    return {
        "sha": observation.sha,
        "message": observation.message,
        "parent_shas": list(observation.parent_shas),
        "changed_files": list(observation.changed_files),
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
    observations = result.setdefault("human_verification", [])
    assert isinstance(observations, list)
    observations.append({"check": check, "observed": observed})


def _record_failed_step_from_error(result: dict[str, object]) -> None:
    error = str(result.get("error", "")).strip()
    if not error.startswith("Step "):
        return
    try:
        prefix, _, observed = error.partition("\n")
        step_number = int(prefix.split()[1])
    except (IndexError, ValueError):
        return
    steps = result.setdefault("steps", [])
    assert isinstance(steps, list)
    if any(
        isinstance(step, dict) and int(step.get("step", -1)) == step_number
        for step in steps
    ):
        return
    action = (
        REQUEST_STEPS[step_number - 1]
        if 0 < step_number <= len(REQUEST_STEPS)
        else "Automation step failed."
    )
    steps.append(
        {
            "step": step_number,
            "status": "failed",
            "action": action,
            "observed": observed or error,
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
    if _is_product_failure(result):
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        "* Opened the deployed hosted TrackState app, connected to the live setup repository, and navigated to *Project Settings*.",
        "* Added a unique status, edited the existing *Delivery Workflow* transition, and saved through the visible hosted Settings UI.",
        "* Verified the save result through the live GitHub repository commit/file state.",
        "* Ran the installed {{trackstate session}} CLI against the same hosted repository and checked the returned {{projectConfig}} block.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result: the hosted save produced one atomic commit and the CLI immediately exposed the updated project configuration."
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
        "- Opened the deployed hosted TrackState app, connected to the live setup repository, and navigated to `Project Settings`.",
        "- Added a unique status, edited the existing `Delivery Workflow` transition, and saved through the visible hosted Settings UI.",
        "- Verified the save result through the live GitHub repository commit/file state.",
        "- Ran the installed `trackstate session` CLI against the same hosted repository and checked the returned `projectConfig` block.",
        "",
        "### Observed result",
        (
            "- Matched the expected result: the hosted save produced one atomic commit and the CLI immediately exposed the updated project configuration."
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
        f"# {TICKET_KEY} {status}",
        "",
        (
            "Verified the hosted Settings save created one atomic commit and the installed "
            "`trackstate session` CLI immediately returned the updated `projectConfig`."
            if passed
            else "The hosted Settings persistence / CLI parity scenario did not match the expected result."
        ),
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    screenshot_path = result.get("screenshot", FAILURE_SCREENSHOT_PATH)
    actual = _actual_result_text(result)
    cli_observation = result.get("cli_observation")
    cli_text = (
        json.dumps(cli_observation, indent=2)
        if isinstance(cli_observation, dict)
        else "CLI step was not reached."
    )
    return "\n".join(
        [
            f"# {TICKET_KEY} product defect",
            "",
            "## Steps to reproduce",
            *_ticket_step_lines(result),
            "",
            "## Expected result",
            (
                "Approved changes are written in one atomic Git commit via `applyFileChanges`. "
                "The CLI `session` output immediately reflects the updated status catalog and "
                "workflow summaries in the `projectConfig` block."
            ),
            "",
            "## Actual result",
            actual,
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment details",
            f"- URL: `{result['app_url']}`",
            f"- Repository: `{result['repository']}`",
            f"- Branch/ref: `{result['repository_ref']}`",
            f"- Browser: `Chromium (Playwright)`",
            f"- OS: `{platform.system()}`",
            "",
            "## Screenshots or logs",
            f"- Screenshot: `{screenshot_path}`",
            "- CLI observation:",
            "```json",
            cli_text,
            "```",
        ]
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps", [])
    if not isinstance(steps, list) or not steps:
        return ["* No automation steps were recorded." if jira else "- No automation steps were recorded."]
    prefix = "*" if jira else "-"
    rendered: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        rendered.append(
            f"{prefix} Step {step.get('step')}: {step.get('status', 'unknown').upper()} - "
            f"{step.get('action', '')}"
        )
        rendered.append(f"{prefix} Observed: {step.get('observed', '')}")
    return rendered


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    entries = result.get("human_verification", [])
    if not isinstance(entries, list) or not entries:
        return ["* No additional human-style observations were recorded." if jira else "- No additional human-style observations were recorded."]
    prefix = "*" if jira else "-"
    rendered: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        rendered.append(f"{prefix} {entry.get('check', '')}")
        rendered.append(f"{prefix} Observed: {entry.get('observed', '')}")
    return rendered


def _ticket_step_lines(result: dict[str, object]) -> list[str]:
    recorded_steps = result.get("steps", [])
    step_lookup = {
        int(step.get("step")): step
        for step in recorded_steps
        if isinstance(step, dict) and isinstance(step.get("step"), int)
    }
    lines: list[str] = []
    for index, action in enumerate(REQUEST_STEPS, start=1):
        step = step_lookup.get(index)
        if step is None:
            lines.append(f"{index}. {action} - not reached.")
            continue
        status = str(step.get("status", "unknown")).upper()
        icon = "✅" if status == "PASSED" else "❌"
        lines.append(f"{index}. {action} - {icon} {status}")
        lines.append(f"   - Observed: {step.get('observed', '')}")
    return lines


def _actual_result_text(result: dict[str, object]) -> str:
    error = str(result.get("error", ""))
    if error.startswith("Step 4 failed:"):
        return (
            "After the hosted Settings save, the repository branch head did not change "
            "within the polling window, so no new atomic commit was available for the "
            "requested settings update."
        )
    if error.startswith("Step 5 failed:"):
        return (
            "The hosted save reached Git, but the installed `trackstate session` CLI did "
            "not expose the updated status/workflow markers inside the returned "
            "`projectConfig` block within the polling window."
        )
    return error or "The scenario failed before the expected user-visible result was observed."


def _human_ui_observation_text(observation: ProjectSettingsUiObservation) -> str:
    return (
        f"settings_text={observation.settings_text!r}; "
        f"status_dialog_text={observation.status_dialog_text!r}; "
        f"workflow_dialog_text={observation.workflow_dialog_text!r}; "
        f"post_save_text={observation.post_save_text!r}"
    )


def _human_commit_observation_text(observation: dict[str, object]) -> str:
    statuses = observation.get("statuses_file", {}) if isinstance(observation, dict) else {}
    workflows = observation.get("workflows_file", {}) if isinstance(observation, dict) else {}
    return (
        f"statuses_url={statuses.get('url', '')!r}; "
        f"statuses_match={statuses.get('matched_text', '')!r}; "
        f"statuses_screenshot={statuses.get('screenshot_path', '')!r}; "
        f"workflows_url={workflows.get('url', '')!r}; "
        f"workflows_match={workflows.get('matched_text', '')!r}; "
        f"workflows_screenshot={workflows.get('screenshot_path', '')!r}"
    )


def _human_cli_observation_text(result: CliCommandResult) -> str:
    payload = (
        json.dumps(result.json_payload, sort_keys=True)
        if result.json_payload is not None
        else result.stdout
    )
    return (
        f"command={result.command_text!r}; exit_code={result.exit_code}; "
        f"project_config_payload={payload}"
    )


def _is_product_failure(result: dict[str, object]) -> bool:
    error = str(result.get("error", ""))
    if error.startswith("Precondition failed:"):
        return False
    if "requires GH_TOKEN" in error or "available on PATH" in error:
        return False
    return error.startswith("Step ")


if __name__ == "__main__":
    main()
