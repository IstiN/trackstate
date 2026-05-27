from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_identity_local_conflict_validator import (  # noqa: E402
    TrackStateCliReleaseIdentityLocalConflictValidator,
)
from testing.core.config.trackstate_cli_release_identity_local_conflict_config import (  # noqa: E402
    TrackStateCliReleaseIdentityLocalConflictConfig,
)
from testing.core.models.trackstate_cli_release_identity_local_conflict_result import (  # noqa: E402
    TrackStateCliReleaseIdentityLocalConflictRemoteState,
    TrackStateCliReleaseIdentityLocalConflictRepositoryState,
    TrackStateCliReleaseIdentityLocalConflictValidationResult,
)
from testing.tests.support.trackstate_cli_release_identity_local_conflict_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_identity_local_conflict_probe,
)

TICKET_KEY = "TS-560"
TICKET_SUMMARY = "Release identity conflict — fail on mismatched issue title"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-560/test_ts_560.py"
RUN_COMMAND = "python testing/tests/TS-560/test_ts_560.py"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config_path = REPO_ROOT / "testing/tests/TS-560/config.yaml"
    config = TrackStateCliReleaseIdentityLocalConflictConfig.from_file(config_path)
    validator = TrackStateCliReleaseIdentityLocalConflictValidator(
        probe=create_trackstate_cli_release_identity_local_conflict_probe(REPO_ROOT),
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "repository": config.repository,
        "branch": config.branch,
        "project_key": config.project_key,
        "issue_key": config.issue_key,
        "issue_summary": config.issue_summary,
        "release_tag": config.expected_release_tag,
        "expected_release_title": config.expected_release_title,
        "conflicting_release_title": config.conflicting_release_title,
        "requested_command": " ".join(config.requested_command),
        "config_path": str(config_path),
        "os": platform.system(),
        "steps": [],
        "human_verification": [],
    }

    try:
        validation = validator.validate(config=config)
        result.update(_validation_payload(validation))
        _assert_preconditions(config, validation, result)
        _assert_runtime_expectations(config, validation, result)
        _assert_repository_state(validation, result)
        _assert_remote_state(config, validation, result)
        _assert_cleanup(validation)
        _write_pass_outputs(result)
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        if "validation" in locals():
            result.update(_validation_payload(validation))
        _write_failure_outputs(config, result)
        raise


def _assert_preconditions(
    config: TrackStateCliReleaseIdentityLocalConflictConfig,
    validation: TrackStateCliReleaseIdentityLocalConflictValidationResult,
    result: dict[str, object],
) -> None:
    repository_state = validation.initial_repository_state
    remote_state = validation.initial_remote_state

    if validation.observation.requested_command != config.requested_command:
        raise AssertionError(
            "Precondition failed: TS-560 did not execute the exact ticket command.\n"
            f"Expected command: {' '.join(config.requested_command)}\n"
            f"Observed command: {validation.observation.requested_command_text}",
        )
    if validation.observation.compiled_binary_path is None:
        raise AssertionError(
            "Precondition failed: TS-560 must execute a repository-local compiled binary "
            "from the disposable local repository.\n"
            f"Executed command: {validation.observation.executed_command_text}\n"
            f"Fallback reason: {validation.observation.fallback_reason}",
        )
    if not repository_state.issue_main_exists:
        raise AssertionError(
            "Precondition failed: the local fixture issue TS-123 was not present before "
            "running the upload command.\n"
            f"Observed state:\n{_describe_repository_state(repository_state)}",
        )
    if not repository_state.source_file_exists:
        raise AssertionError(
            "Precondition failed: the local upload file report.pdf was missing before "
            "running the upload command.\n"
            f"Observed state:\n{_describe_repository_state(repository_state)}",
        )
    if repository_state.manifest_exists or repository_state.attachment_directory_exists:
        raise AssertionError(
            "Precondition failed: the disposable local repository already contained "
            "attachment output before TS-560 ran.\n"
            f"Observed state:\n{_describe_repository_state(repository_state)}",
        )
    if repository_state.remote_origin_url != config.remote_origin_url:
        raise AssertionError(
            "Precondition failed: the local repository origin did not point at the live "
            "setup repository.\n"
            f"Expected origin: {config.remote_origin_url}\n"
            f"Observed state:\n{_describe_repository_state(repository_state)}",
        )
    if not remote_state.release_present:
        raise AssertionError(
            "Precondition failed: the conflicting GitHub Release was not present before "
            "running the local upload command.\n"
            f"Observed state:\n{_describe_remote_state(remote_state)}",
        )
    if remote_state.release_name != config.conflicting_release_title:
        raise AssertionError(
            "Precondition failed: the GitHub Release title was not the mismatched title "
            "required by TS-560.\n"
            f"Expected title: {config.conflicting_release_title}\n"
            f"Observed state:\n{_describe_remote_state(remote_state)}",
        )

    _record_step(
        result,
        step=0,
        status="passed",
        action="Prepare the disposable local repository and mismatched GitHub Release preconditions.",
        observed=(
            f"remote_origin_url={repository_state.remote_origin_url}; "
            f"release_tag={config.expected_release_tag}; "
            f"release_title={remote_state.release_name}; "
            f"manifest_exists={repository_state.manifest_exists}"
        ),
    )


def _assert_runtime_expectations(
    config: TrackStateCliReleaseIdentityLocalConflictConfig,
    validation: TrackStateCliReleaseIdentityLocalConflictValidationResult,
    result: dict[str, object],
) -> None:
    observation = validation.observation
    payload = observation.result.json_payload
    if observation.result.exit_code != config.expected_exit_code:
        raise AssertionError(
            "Step 1 failed: executing the local attachment upload command did not return "
            "the expected conflict exit code.\n"
            f"Expected exit code: {config.expected_exit_code}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 1 failed: the local attachment upload command did not return a "
            "machine-readable JSON error envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
    if payload.get("ok") is not False:
        raise AssertionError(
            "Expected result failed: the local attachment upload conflict did not "
            "return `ok: false`.\n"
            f"Observed payload: {payload}",
        )

    error = payload.get("error")
    if not isinstance(error, dict):
        raise AssertionError(
            "Step 1 failed: the local attachment upload conflict did not include an "
            "`error` object.\n"
            f"Observed payload: {payload}",
        )

    result["observed_error_code"] = error.get("code")
    result["observed_error_category"] = error.get("category")
    result["observed_error_exit_code"] = error.get("exitCode")
    result["observed_error_message"] = error.get("message")
    result["observed_error_details"] = error.get("details")

    if error.get("code") != config.expected_error_code:
        raise AssertionError(
            "Step 1 failed: the local attachment upload conflict did not return the "
            "expected machine-readable error code.\n"
            f"Expected code: {config.expected_error_code}\n"
            f"Observed code: {error.get('code')}\n"
            f"Observed payload: {payload}",
        )
    if error.get("category") != config.expected_error_category:
        raise AssertionError(
            "Step 1 failed: the local attachment upload conflict did not return the "
            "expected error category.\n"
            f"Expected category: {config.expected_error_category}\n"
            f"Observed category: {error.get('category')}\n"
            f"Observed payload: {payload}",
        )
    if error.get("exitCode") != config.expected_exit_code:
        raise AssertionError(
            "Step 1 failed: the local attachment upload conflict did not preserve the "
            "expected machine-readable exit code.\n"
            f"Expected error.exitCode: {config.expected_exit_code}\n"
            f"Observed error.exitCode: {error.get('exitCode')}\n"
            f"Observed payload: {payload}",
        )

    details = error.get("details")
    if not isinstance(details, dict):
        raise AssertionError(
            "Step 1 failed: the local attachment upload conflict did not include "
            "`error.details`.\n"
            f"Observed payload: {payload}",
        )
    reason = str(details.get("reason", ""))
    missing_reason_fragments = [
        fragment
        for fragment in config.required_reason_fragments
        if fragment not in reason
    ]
    if missing_reason_fragments:
        raise AssertionError(
            "Expected result failed: the local upload conflict reason did not explain "
            "that the existing release belongs to another issue identity.\n"
            f"Missing reason fragments: {missing_reason_fragments}\n"
            f"Observed reason: {reason}\n"
            f"Observed payload: {payload}",
        )

    for fragment in config.required_stdout_fragments:
        if fragment not in observation.result.stdout:
            raise AssertionError(
                "Human-style verification failed: the visible CLI JSON output did not "
                "show the expected deterministic conflict markers.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )

    _record_step(
        result,
        step=1,
        status="passed",
        action="Run the exact local upload command for issue `TS-123`.",
        observed=(
            f"exit_code={observation.result.exit_code}; "
            f"error_code={error.get('code')}; "
            f"reason={reason}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Verified the terminal output stayed in a failure state and explicitly told a "
            "user that the existing release container does not match TS-123."
        ),
        observed=observation.result.stdout.strip() or observation.result.stderr.strip() or "<empty>",
    )


def _assert_repository_state(
    validation: TrackStateCliReleaseIdentityLocalConflictValidationResult,
    result: dict[str, object],
) -> None:
    initial_state = validation.initial_repository_state
    final_state = validation.final_repository_state

    if final_state.manifest_exists != initial_state.manifest_exists:
        raise AssertionError(
            "Expected result failed: the local attachments.json existence changed even "
            "though the upload should have failed before mutating repository state.\n"
            f"Initial state:\n{_describe_repository_state(initial_state)}\n\n"
            f"Final state:\n{_describe_repository_state(final_state)}",
        )
    if final_state.manifest_text != initial_state.manifest_text:
        raise AssertionError(
            "Expected result failed: the local attachments.json content changed even "
            "though the upload should have failed without mutation.\n"
            f"Initial state:\n{_describe_repository_state(initial_state)}\n\n"
            f"Final state:\n{_describe_repository_state(final_state)}",
        )
    if final_state.attachment_directory_exists != initial_state.attachment_directory_exists:
        raise AssertionError(
            "Expected result failed: the local attachments directory was created even "
            "though the upload should have failed before writing output.\n"
            f"Initial state:\n{_describe_repository_state(initial_state)}\n\n"
            f"Final state:\n{_describe_repository_state(final_state)}",
        )
    if final_state.expected_attachment_exists != initial_state.expected_attachment_exists:
        raise AssertionError(
            "Expected result failed: a local attachment file was written even though the "
            "release identity conflict should block the upload.\n"
            f"Initial state:\n{_describe_repository_state(initial_state)}\n\n"
            f"Final state:\n{_describe_repository_state(final_state)}",
        )
    if final_state.stored_files != initial_state.stored_files:
        raise AssertionError(
            "Expected result failed: the local repository stored attachment files even "
            "though the upload should have been rejected.\n"
            f"Initial files: {_describe_repository_state(initial_state)}\n\n"
            f"Final files: {_describe_repository_state(final_state)}",
        )
    if final_state.git_status_lines != initial_state.git_status_lines:
        raise AssertionError(
            "Expected result failed: the local repository working tree changed after the "
            "failed upload command.\n"
            f"Initial state:\n{_describe_repository_state(initial_state)}\n\n"
            f"Final state:\n{_describe_repository_state(final_state)}",
        )

    _record_step(
        result,
        step=2,
        status="passed",
        action="Inspect the local repository after the failed upload attempt.",
        observed=(
            f"manifest_exists={final_state.manifest_exists}; "
            f"attachment_directory_exists={final_state.attachment_directory_exists}; "
            f"stored_files={list(_stored_file_paths(final_state))}; "
            f"git_status_lines={list(final_state.git_status_lines)}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Verified from the repository filesystem and git status that no attachment "
            "metadata or local file output appeared after the command failed."
        ),
        observed=_describe_repository_state(final_state),
    )


def _assert_remote_state(
    config: TrackStateCliReleaseIdentityLocalConflictConfig,
    validation: TrackStateCliReleaseIdentityLocalConflictValidationResult,
    result: dict[str, object],
) -> None:
    initial_state = validation.initial_remote_state
    final_state = validation.final_remote_state

    if final_state.release_id != initial_state.release_id:
        raise AssertionError(
            "Expected result failed: the conflicting release object was replaced after "
            "the failed local upload.\n"
            f"Initial state:\n{_describe_remote_state(initial_state)}\n\n"
            f"Final state:\n{_describe_remote_state(final_state)}",
        )
    if final_state.release_name != config.conflicting_release_title:
        raise AssertionError(
            "Expected result failed: the conflicting release title changed after the "
            "failed local upload.\n"
            f"Initial state:\n{_describe_remote_state(initial_state)}\n\n"
            f"Final state:\n{_describe_remote_state(final_state)}",
        )
    if final_state.release_asset_names != initial_state.release_asset_names:
        raise AssertionError(
            "Expected result failed: the conflicting release asset list changed even "
            "though the upload should not target the mismatched release.\n"
            f"Initial state:\n{_describe_remote_state(initial_state)}\n\n"
            f"Final state:\n{_describe_remote_state(final_state)}",
        )

    _record_step(
        result,
        step=3,
        status="passed",
        action="Inspect the live GitHub Release after the failed upload attempt.",
        observed=(
            f"release_id={final_state.release_id}; "
            f"release_title={final_state.release_name}; "
            f"release_assets={list(final_state.release_asset_names)}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Verified the live GitHub Release still showed the mismatched title and the "
            "same visible asset list, so the command did not reuse another issue's container."
        ),
        observed=_describe_remote_state(final_state),
    )


def _assert_cleanup(
    validation: TrackStateCliReleaseIdentityLocalConflictValidationResult,
) -> None:
    if validation.cleanup_error is not None:
        raise AssertionError(
            "Cleanup failed after the local release identity conflict scenario completed.\n"
            f"{validation.cleanup_error}",
        )


def _validation_payload(
    validation: TrackStateCliReleaseIdentityLocalConflictValidationResult,
) -> dict[str, object]:
    return {
        "requested_command": validation.observation.requested_command_text,
        "executed_command": validation.observation.executed_command_text,
        "compiled_binary_path": validation.observation.compiled_binary_path,
        "repository_path": validation.observation.repository_path,
        "stdout": validation.observation.result.stdout,
        "stderr": validation.observation.result.stderr,
        "exit_code": validation.observation.result.exit_code,
        "payload": validation.observation.result.json_payload,
        "local_attachment_path": validation.local_attachment_path,
        "setup_actions": list(validation.setup_actions),
        "cleanup_actions": list(validation.cleanup_actions),
        "initial_repository_state": _repository_state_to_dict(
            validation.initial_repository_state,
        ),
        "final_repository_state": _repository_state_to_dict(
            validation.final_repository_state,
        ),
        "initial_remote_state": _remote_state_to_dict(validation.initial_remote_state),
        "final_remote_state": _remote_state_to_dict(validation.final_remote_state),
    }


def _repository_state_to_dict(
    state: TrackStateCliReleaseIdentityLocalConflictRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "source_file_exists": state.source_file_exists,
        "attachment_directory_exists": state.attachment_directory_exists,
        "expected_attachment_exists": state.expected_attachment_exists,
        "stored_files": [
            {
                "relative_path": stored_file.relative_path,
                "size_bytes": stored_file.size_bytes,
            }
            for stored_file in state.stored_files
        ],
        "manifest_exists": state.manifest_exists,
        "manifest_text": state.manifest_text,
        "git_status_lines": list(state.git_status_lines),
        "remote_names": list(state.remote_names),
        "remote_origin_url": state.remote_origin_url,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _remote_state_to_dict(
    state: TrackStateCliReleaseIdentityLocalConflictRemoteState,
) -> dict[str, object]:
    return {
        "release_present": state.release_present,
        "release_id": state.release_id,
        "release_name": state.release_name,
        "release_asset_names": list(state.release_asset_names),
    }


def _describe_repository_state(
    state: TrackStateCliReleaseIdentityLocalConflictRepositoryState,
) -> str:
    return json.dumps(_repository_state_to_dict(state), indent=2, sort_keys=True)


def _describe_remote_state(
    state: TrackStateCliReleaseIdentityLocalConflictRemoteState,
) -> str:
    return json.dumps(_remote_state_to_dict(state), indent=2, sort_keys=True)


def _stored_file_paths(
    state: TrackStateCliReleaseIdentityLocalConflictRepositoryState,
) -> tuple[str, ...]:
    return tuple(stored_file.relative_path for stored_file in state.stored_files)


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
    entries = result.setdefault("human_verification", [])
    assert isinstance(entries, list)
    entries.append({"check": check, "observed": observed})


def _write_pass_outputs(result: dict[str, object]) -> None:
    jira = _jira_comment(result, status="PASSED")
    markdown = _markdown_summary(result, status="PASSED")
    _write_text(JIRA_COMMENT_PATH, jira)
    _write_text(PR_BODY_PATH, markdown)
    _write_text(RESPONSE_PATH, markdown)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _write_failure_outputs(
    config: TrackStateCliReleaseIdentityLocalConflictConfig,
    result: dict[str, object],
) -> None:
    error = str(result.get("error", "AssertionError"))
    jira = _jira_comment(result, status="FAILED")
    markdown = _markdown_summary(result, status="FAILED")
    bug = _bug_description(config, result)
    _write_text(JIRA_COMMENT_PATH, jira)
    _write_text(PR_BODY_PATH, markdown)
    _write_text(RESPONSE_PATH, markdown)
    _write_text(BUG_DESCRIPTION_PATH, bug)
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
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _jira_comment(result: dict[str, object], *, status: str) -> str:
    steps = result.get("steps", [])
    human_checks = result.get("human_verification", [])
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Repository:* {result.get('repository')}",
        f"*Branch:* {result.get('branch')}",
        f"*Release tag:* {result.get('release_tag')}",
        f"*Requested command:* {{code}}{result.get('requested_command')}{{code}}",
        "",
        "h4. What was tested",
        (
            f"* Executed the exact local CLI upload flow from a disposable Git repository "
            f"whose {{{{origin}}}} pointed at "
            f"{{{{https://github.com/{result.get('repository')}.git}}}}."
        ),
        (
            f"* Verified the command failed with the deterministic release-identity conflict "
            f"instead of uploading {{{{report.pdf}}}} into release "
            f"{{{{{result.get('release_tag')}}}}}."
        ),
        (
            "* Verified the local repository did not create {{attachments.json}} or any "
            "attachment output files after the failure."
        ),
        (
            "* Verified the live GitHub Release kept the mismatched title and asset list "
            "after the command failed."
        ),
        "",
        "h4. Automation",
    ]
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                lines.append(
                    f"# [{step.get('status')}] {step.get('action')} -- {step.get('observed')}",
                )
    lines.extend(["", "h4. Human-style verification"])
    if isinstance(human_checks, list):
        for check in human_checks:
            if isinstance(check, dict):
                lines.append(
                    f"* {check.get('check')} Observed: {{noformat}}{check.get('observed')}{{noformat}}",
                )
    lines.extend(["", "h4. Result"])
    if status == "PASSED":
        lines.append("* The observed behavior matched the expected result.")
    else:
        lines.append(
            f"* Step failed: {{noformat}}{result.get('error')}{{noformat}}",
        )
    lines.extend(
        [
            "",
            "h4. Test file",
            "{code}",
            TEST_FILE_PATH,
            "{code}",
            "",
            "h4. Run command",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ],
    )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, status: str) -> str:
    steps = result.get("steps", [])
    human_checks = result.get("human_verification", [])
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Executed the exact local CLI upload flow from a disposable Git repository "
            f"whose `origin` pointed at `https://github.com/{result.get('repository')}.git`."
        ),
        (
            f"- Verified the command failed with the deterministic release-identity conflict "
            f"instead of uploading `report.pdf` into release `{result.get('release_tag')}`."
        ),
        (
            "- Verified the local repository did not create `attachments.json` or any "
            "attachment output files after the failure."
        ),
        (
            "- Verified the live GitHub Release kept the mismatched title and asset list "
            "after the command failed."
        ),
        "",
        "## Automation details",
    ]
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                lines.append(
                    f"1. **{step.get('status')}** {step.get('action')} — {step.get('observed')}",
                )
    lines.extend(["", "## Human-style verification"])
    if isinstance(human_checks, list):
        for check in human_checks:
            if isinstance(check, dict):
                lines.append(
                    f"1. {check.get('check')} Observed: `{check.get('observed')}`",
                )
    lines.extend(["", "## Result"])
    if status == "PASSED":
        lines.append("- The observed behavior matched the expected result.")
    else:
        lines.append(f"- Failure: `{result.get('error')}`")
    lines.extend(["", "## How to run", "```bash", RUN_COMMAND, "```"])
    return "\n".join(lines) + "\n"


def _bug_description(
    config: TrackStateCliReleaseIdentityLocalConflictConfig,
    result: dict[str, object],
) -> str:
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    traceback_text = str(result.get("traceback", ""))
    initial_repository_state = result.get("initial_repository_state")
    final_repository_state = result.get("final_repository_state")
    initial_remote_state = result.get("initial_remote_state")
    final_remote_state = result.get("final_remote_state")
    return "\n".join(
        [
            f"# {TICKET_KEY} - Local release identity conflict upload does not fail correctly",
            "",
            "## Steps to reproduce",
            "1. ✅ Configure a local TrackState repository with `attachmentStorage.mode = github-releases`.",
            (
                f"2. ✅ Ensure a GitHub Release exists for tag `{config.expected_release_tag}` "
                f"but the title is `{config.conflicting_release_title}` instead of "
                f"`{config.expected_release_title}`."
            ),
            (
                "3. ❌ Execute the exact CLI command "
                f"`{config.ticket_command}` from that local repository."
            ),
            f"   - Actual behavior: {result.get('error')}",
            f"   - CLI stdout at failure:\n\n```json\n{stdout}\n```",
            f"   - CLI stderr at failure:\n\n```\n{stderr}\n```",
            "4. ❌ Inspect the command output and repository/release state.",
            (
                "   - Actual local repository state:\n\n```json\n"
                f"{json.dumps(final_repository_state, indent=2, sort_keys=True) if isinstance(final_repository_state, dict) else final_repository_state}\n```"
            ),
            (
                "   - Actual remote release state:\n\n```json\n"
                f"{json.dumps(final_remote_state, indent=2, sort_keys=True) if isinstance(final_remote_state, dict) else final_remote_state}\n```"
            ),
            "",
            "## Expected vs Actual",
            (
                f"- **Expected:** the command should fail deterministically because release "
                f"`{config.expected_release_tag}` belongs to another issue identity, and no "
                "local manifest, local attachment output, or release asset changes should occur."
            ),
            f"- **Actual:** {result.get('error')}",
            (
                "- **Initial local repository state:**\n\n```json\n"
                f"{json.dumps(initial_repository_state, indent=2, sort_keys=True) if isinstance(initial_repository_state, dict) else initial_repository_state}\n```"
            ),
            (
                "- **Initial remote release state:**\n\n```json\n"
                f"{json.dumps(initial_remote_state, indent=2, sort_keys=True) if isinstance(initial_remote_state, dict) else initial_remote_state}\n```"
            ),
            "",
            "## Exact error / stack trace",
            f"```text\n{traceback_text}\n```",
            "",
            "## Environment",
            f"- Repository: `{config.repository}`",
            f"- Branch: `{config.branch}`",
            f"- Issue: `{config.issue_key}`",
            f"- Release tag: `{config.expected_release_tag}`",
            f"- Browser: `N/A (CLI scenario)`",
            f"- OS: `{result.get('os')}`",
            f"- Local upload file: `{result.get('local_attachment_path')}`",
            "",
            "## Logs",
            f"### stdout\n```json\n{stdout}\n```",
            f"### stderr\n```\n{stderr}\n```",
        ],
    ) + "\n"


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
