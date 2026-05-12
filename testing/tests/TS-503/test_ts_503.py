from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_identity_conflict_validator import (  # noqa: E402
    TrackStateCliReleaseIdentityConflictValidator,
)
from testing.core.config.trackstate_cli_release_identity_conflict_config import (  # noqa: E402
    TrackStateCliReleaseIdentityConflictConfig,
)
from testing.core.models.trackstate_cli_release_identity_conflict_result import (  # noqa: E402
    TrackStateCliReleaseIdentityConflictRemoteState,
    TrackStateCliReleaseIdentityConflictValidationResult,
)
from testing.tests.support.trackstate_cli_release_identity_conflict_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_identity_conflict_probe,
)

TICKET_KEY = "TS-503"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config_path = REPO_ROOT / "testing/tests/TS-503/config.yaml"
    config = TrackStateCliReleaseIdentityConflictConfig.from_file(config_path)
    validator = TrackStateCliReleaseIdentityConflictValidator(
        probe=create_trackstate_cli_release_identity_conflict_probe(REPO_ROOT),
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
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
        _assert_no_state_mutation(config, validation, result)
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
    config: TrackStateCliReleaseIdentityConflictConfig,
    validation: TrackStateCliReleaseIdentityConflictValidationResult,
    result: dict[str, object],
) -> None:
    initial_state = validation.initial_state
    if validation.observation.requested_command != config.requested_command:
        raise AssertionError(
            "Precondition failed: TS-503 did not execute the exact ticket command.\n"
            f"Expected command: {' '.join(config.requested_command)}\n"
            f"Observed command: {validation.observation.requested_command_text}",
        )
    if validation.observation.compiled_binary_path is None:
        raise AssertionError(
            "Precondition failed: TS-503 must execute a repository-local compiled binary "
            "so the hosted command is pinned to this checkout.\n"
            f"Executed command: {validation.observation.executed_command_text}\n"
            f"Fallback reason: {validation.observation.fallback_reason}",
        )
    if not initial_state.issue_main_exists:
        raise AssertionError(
            "Precondition failed: the hosted fixture issue `TS-300` was not present "
            "before running the upload command.\n"
            f"Observed state:\n{_describe_state(initial_state)}",
        )
    if not initial_state.release_present:
        raise AssertionError(
            "Precondition failed: the hosted conflict release did not exist before "
            "running the upload command.\n"
            f"Observed state:\n{_describe_state(initial_state)}",
        )
    if initial_state.release_name != config.conflicting_release_title:
        raise AssertionError(
            "Precondition failed: the hosted release title was not the mismatched "
            "Manual Release title required by TS-503.\n"
            f"Expected title: {config.conflicting_release_title}\n"
            f"Observed state:\n{_describe_state(initial_state)}",
        )
    if '"mode": "github-releases"' not in (initial_state.project_json_text or ""):
        raise AssertionError(
            "Precondition failed: the hosted project was not switched to "
            "`github-releases` mode before the upload command.\n"
            f"Observed project.json:\n{initial_state.project_json_text}",
        )

    _record_step(
        result,
        step=0,
        status="passed",
        action="Prepare the hosted DEMO project and conflicting release preconditions.",
        observed=(
            f"release_tag={config.expected_release_tag}; "
            f"release_title={initial_state.release_name}; "
            f"manifest_exists={initial_state.manifest_exists}"
        ),
    )


def _assert_runtime_expectations(
    config: TrackStateCliReleaseIdentityConflictConfig,
    validation: TrackStateCliReleaseIdentityConflictValidationResult,
    result: dict[str, object],
) -> None:
    observation = validation.observation
    payload = observation.result.json_payload
    if observation.result.exit_code != config.expected_exit_code:
        raise AssertionError(
            "Step 1 failed: executing the hosted attachment upload command did not "
            "return the expected failure exit code.\n"
            f"Expected exit code: {config.expected_exit_code}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 1 failed: the hosted attachment upload command did not return a "
            "machine-readable JSON error envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
    if payload.get("ok") is not False:
        raise AssertionError(
            "Expected result failed: the hosted attachment upload conflict did not "
            "return `ok: false`.\n"
            f"Observed payload: {payload}",
        )

    error = payload.get("error")
    if not isinstance(error, dict):
        raise AssertionError(
            "Step 1 failed: the hosted attachment upload conflict did not include an "
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
            "Step 1 failed: the hosted attachment upload conflict did not return the "
            "expected machine-readable error code.\n"
            f"Expected code: {config.expected_error_code}\n"
            f"Observed code: {error.get('code')}\n"
            f"Observed payload: {payload}",
        )
    if error.get("category") != config.expected_error_category:
        raise AssertionError(
            "Step 1 failed: the hosted attachment upload conflict did not return the "
            "expected error category.\n"
            f"Expected category: {config.expected_error_category}\n"
            f"Observed category: {error.get('category')}\n"
            f"Observed payload: {payload}",
        )
    if error.get("exitCode") != config.expected_exit_code:
        raise AssertionError(
            "Step 1 failed: the hosted attachment upload conflict did not preserve the "
            "expected machine-readable exit code.\n"
            f"Expected error.exitCode: {config.expected_exit_code}\n"
            f"Observed error.exitCode: {error.get('exitCode')}\n"
            f"Observed payload: {payload}",
        )

    details = error.get("details")
    if not isinstance(details, dict):
        raise AssertionError(
            "Step 1 failed: the hosted attachment upload conflict did not include "
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
            "Expected result failed: the hosted upload conflict reason did not explain "
            "that the existing release mismatched the issue container.\n"
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
        action="Attempt to upload an attachment to issue `TS-300`.",
        observed=(
            f"exit_code={observation.result.exit_code}; "
            f"error_code={error.get('code')}; "
            f"reason={reason}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Verified the visible CLI output stayed in a failure state and explicitly "
            "reported that the existing release did not match the TS-300 issue container."
        ),
        observed=observation.result.stdout,
    )


def _assert_no_state_mutation(
    config: TrackStateCliReleaseIdentityConflictConfig,
    validation: TrackStateCliReleaseIdentityConflictValidationResult,
    result: dict[str, object],
) -> None:
    initial_state = validation.initial_state
    final_state = validation.final_state

    if final_state.release_id != initial_state.release_id:
        raise AssertionError(
            "Expected result failed: the conflicting release object was replaced after "
            "the failed upload.\n"
            f"Initial release_id: {initial_state.release_id}\n"
            f"Final release_id: {final_state.release_id}\n"
            f"Initial state:\n{_describe_state(initial_state)}\n\n"
            f"Final state:\n{_describe_state(final_state)}",
        )
    if final_state.release_name != config.conflicting_release_title:
        raise AssertionError(
            "Expected result failed: the conflicting release title changed after the "
            "failed upload.\n"
            f"Initial state:\n{_describe_state(initial_state)}\n\n"
            f"Final state:\n{_describe_state(final_state)}",
        )
    if final_state.release_asset_names != initial_state.release_asset_names:
        raise AssertionError(
            "Expected result failed: the conflicting release asset list changed even "
            "though the upload should have failed before mutating state.\n"
            f"Initial asset names: {initial_state.release_asset_names}\n"
            f"Final asset names: {final_state.release_asset_names}",
        )
    if final_state.manifest_exists != initial_state.manifest_exists:
        raise AssertionError(
            "Expected result failed: the hosted attachment manifest existence changed "
            "even though AC5 requires no mutation.\n"
            f"Initial state:\n{_describe_state(initial_state)}\n\n"
            f"Final state:\n{_describe_state(final_state)}",
        )
    if final_state.manifest_text != initial_state.manifest_text:
        raise AssertionError(
            "Expected result failed: `attachments.json` changed even though the upload "
            "should have failed without mutation.\n"
            f"Initial manifest:\n{initial_state.manifest_text}\n\n"
            f"Final manifest:\n{final_state.manifest_text}",
        )
    if final_state.project_json_text != initial_state.project_json_text:
        raise AssertionError(
            "Expected result failed: the hosted project settings changed during the "
            "failed upload.\n"
            f"Initial project.json:\n{initial_state.project_json_text}\n\n"
            f"Final project.json:\n{final_state.project_json_text}",
        )
    if final_state.issue_main_content != initial_state.issue_main_content:
        raise AssertionError(
            "Expected result failed: the hosted issue markdown changed during the "
            "failed upload.\n"
            f"Initial issue markdown:\n{initial_state.issue_main_content}\n\n"
            f"Final issue markdown:\n{final_state.issue_main_content}",
        )

    _record_step(
        result,
        step=2,
        status="passed",
        action="Verify that no hosted release or manifest state was mutated.",
        observed=(
            f"release_id={final_state.release_id}; "
            f"release_assets={list(final_state.release_asset_names)}; "
            f"manifest_exists={final_state.manifest_exists}; "
            f"manifest_sha={final_state.manifest_sha}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Verified the conflicting `Manual Release` container stayed in place as the "
            "same hosted release object, with the same visible asset list, and the issue "
            "manifest remained unchanged after the failed command."
        ),
        observed=_describe_state(final_state),
    )


def _assert_cleanup(
    validation: TrackStateCliReleaseIdentityConflictValidationResult,
) -> None:
    if validation.cleanup_error is not None:
        raise AssertionError(
            "Cleanup failed after the hosted release identity conflict scenario "
            "completed.\n"
            f"{validation.cleanup_error}",
        )


def _validation_payload(
    validation: TrackStateCliReleaseIdentityConflictValidationResult,
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
        "initial_state": _state_to_dict(validation.initial_state),
        "final_state": _state_to_dict(validation.final_state),
    }


def _state_to_dict(
    state: TrackStateCliReleaseIdentityConflictRemoteState,
) -> dict[str, object]:
    return {
        "project_json_text": state.project_json_text,
        "issue_main_exists": state.issue_main_exists,
        "issue_main_content": state.issue_main_content,
        "manifest_exists": state.manifest_exists,
        "manifest_text": state.manifest_text,
        "manifest_sha": state.manifest_sha,
        "release_present": state.release_present,
        "release_id": state.release_id,
        "release_name": state.release_name,
        "release_asset_names": list(state.release_asset_names),
    }


def _describe_state(state: TrackStateCliReleaseIdentityConflictRemoteState) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


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
    checks.append(
        {
            "check": check,
            "observed": observed,
        },
    )


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
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()


def _write_failure_outputs(
    config: TrackStateCliReleaseIdentityConflictConfig,
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
        f"h1. {TICKET_KEY} {status}",
        "",
        f"*Repository:* {result.get('repository')}",
        f"*Branch:* {result.get('branch')}",
        f"*Issue:* {result.get('issue_key')}",
        f"*Release tag:* {result.get('release_tag')}",
        f"*Requested command:* {{code}}{result.get('requested_command')}{{code}}",
        "",
        "h2. Automation",
    ]
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                lines.append(
                    f"# [{step.get('status')}] {step.get('action')} -- {step.get('observed')}",
                )
    lines.extend(["", "h2. Human-style verification"])
    if isinstance(human_checks, list):
        for check in human_checks:
            if isinstance(check, dict):
                lines.append(
                    f"* {check.get('check')} Observed: {{noformat}}{check.get('observed')}{{noformat}}",
                )
    if status == "FAILED":
        lines.extend(
            [
                "",
                "h2. Failure",
                f"*Error:* {{noformat}}{result.get('error')}{{noformat}}",
            ],
        )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, status: str) -> str:
    steps = result.get("steps", [])
    human_checks = result.get("human_verification", [])
    lines = [
        f"# {TICKET_KEY} {status}",
        "",
        f"- **Repository:** `{result.get('repository')}`",
        f"- **Branch:** `{result.get('branch')}`",
        f"- **Issue:** `{result.get('issue_key')}`",
        f"- **Release tag:** `{result.get('release_tag')}`",
        f"- **Requested command:** `{result.get('requested_command')}`",
        "",
        "## Automation",
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
    if status == "FAILED":
        lines.extend(["", "## Failure", f"`{result.get('error')}`"])
    return "\n".join(lines) + "\n"


def _bug_description(
    config: TrackStateCliReleaseIdentityConflictConfig,
    result: dict[str, object],
) -> str:
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    traceback_text = str(result.get("traceback", ""))
    initial_state = result.get("initial_state")
    final_state = result.get("final_state")
    return "\n".join(
        [
            f"# {TICKET_KEY} - Release identity conflict upload did not fail cleanly",
            "",
            "## Steps to reproduce",
            "1. ✅ Configure the hosted DEMO project for `github-releases` attachment storage with tag prefix `prefix-`.",
            "2. ✅ Ensure issue `TS-300` exists and the hosted repository resolves tag `prefix-TS-300` to a release titled `Manual Release` instead of `Attachments for TS-300`.",
            "3. ❌ Run the hosted CLI upload command "
            f"`trackstate attachment upload --issue TS-300 --file release-conflict.txt --target hosted --provider github --repository {config.repository} --branch {config.branch}`.",
            f"   - Actual behavior: {result.get('error')}",
            f"   - CLI stdout at failure:\n\n```json\n{stdout}\n```",
            f"   - CLI stderr at failure:\n\n```\n{stderr}\n```",
            "",
            "## Expected vs Actual",
            f"- **Expected:** the command should fail deterministically because release `{config.expected_release_tag}` belongs to a mismatched issue container title, and no hosted manifest or release assets should change.",
            f"- **Actual:** {result.get('error')}",
            f"- **Initial remote state:**\n\n```json\n{json.dumps(initial_state, indent=2, sort_keys=True) if isinstance(initial_state, dict) else initial_state}\n```",
            f"- **Final remote state:**\n\n```json\n{json.dumps(final_state, indent=2, sort_keys=True) if isinstance(final_state, dict) else final_state}\n```",
            "",
            "## Exact error / stack trace",
            f"```text\n{traceback_text}\n```",
            "",
            "## Environment",
            f"- Repository: `{config.repository}`",
            f"- Branch: `{config.branch}`",
            f"- Issue: `{config.issue_key}`",
            f"- Release tag: `{config.expected_release_tag}`",
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
