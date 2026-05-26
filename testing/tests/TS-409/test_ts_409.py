from __future__ import annotations

import json
import os
from pathlib import Path
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
FAILURE_SCREENSHOT_PATH = OUTPUTS_DIR / "ts409_failure.png"
SUCCESS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts409_success.png"
STATUSES_SCREENSHOT_PATH = OUTPUTS_DIR / "ts409_statuses_commit.png"
WORKFLOWS_SCREENSHOT_PATH = OUTPUTS_DIR / "ts409_workflows_commit.png"
RESULT_PATH = OUTPUTS_DIR / "ts409_result.json"
STATUSES_PATH = "DEMO/config/statuses.json"
WORKFLOWS_PATH = "DEMO/config/workflows.json"
WORKFLOW_NAME = "Delivery Workflow"
WORKFLOW_ID = "delivery-workflow"


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
    except AssertionError as error:
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        _write_result(result)
        raise
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_result(result)
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
    _write_result(result)
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
    return len(transitions) - 1


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
    attempts: int = 5,
    interval_seconds: float = 3.0,
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


def _write_result(payload: dict[str, object]) -> None:
    RESULT_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
