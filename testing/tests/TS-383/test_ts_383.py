from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_hosted_lfs_restriction_validator import (  # noqa: E402
    TrackStateCliHostedLfsRestrictionValidator,
)
from testing.core.config.trackstate_cli_hosted_lfs_restriction_config import (  # noqa: E402
    TrackStateCliHostedLfsRestrictionConfig,
)
from testing.core.models.trackstate_cli_hosted_lfs_restriction_result import (  # noqa: E402
    TrackStateCliHostedLfsRestrictionRemoteState,
    TrackStateCliHostedLfsRestrictionValidationResult,
)
from testing.tests.support.trackstate_cli_hosted_lfs_restriction_probe_factory import (  # noqa: E402
    create_trackstate_cli_hosted_lfs_restriction_probe,
)

TICKET_KEY = "TS-383"
TEST_CASE_SUMMARY = "CLI Hosted LFS Restriction - Explicit failure for LFS-tracked uploads"
TEST_FILE_PATH = "testing/tests/TS-383/test_ts_383.py"
RUN_COMMAND = "python3 testing/tests/TS-383/test_ts_383.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    config = TrackStateCliHostedLfsRestrictionConfig.from_env()
    validator = TrackStateCliHostedLfsRestrictionValidator(
        probe=create_trackstate_cli_hosted_lfs_restriction_probe(REPO_ROOT)
    )
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "repository": config.repository,
        "branch": config.branch,
        "issue_key": config.issue_key,
        "issue_summary": config.issue_summary,
        "requested_command": " ".join(config.requested_command),
        "steps": [],
        "human_verification": [],
    }

    try:
        validation = validator.validate(config=config)
        result.update(_validation_payload(validation))
        _assert_preconditions(config, validation)
        _assert_runtime_expectations(config, validation, result)
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
    config: TrackStateCliHostedLfsRestrictionConfig,
    validation: TrackStateCliHostedLfsRestrictionValidationResult,
) -> None:
    initial_state = validation.initial_state
    if not initial_state.zip_lfs_rule_present:
        raise AssertionError(
            "Precondition failed: the hosted repository `.gitattributes` file did not "
            f"contain the required `{config.required_gitattributes_fragment}` rule.\n"
            f"Observed rule line: {initial_state.zip_lfs_rule_line}"
        )
    missing_fixture_paths = [
        path for path in config.fixture_repo_paths if path not in initial_state.present_fixture_paths
    ]
    if missing_fixture_paths:
        raise AssertionError(
            "Precondition failed: TS-383 could not seed all required hosted fixture files "
            "before running the upload command.\n"
            f"Missing fixture paths: {missing_fixture_paths}\n"
            f"Observed fixture paths: {initial_state.present_fixture_paths}"
        )
    if not initial_state.issue_main_exists:
        raise AssertionError(
            "Precondition failed: the hosted DEMO project did not expose the seeded "
            "TS-22 issue before the upload command ran.\n"
            f"Observed issue content:\n{initial_state.issue_main_content or '<missing>'}"
        )
    if initial_state.attachment_exists:
        raise AssertionError(
            "Precondition failed: the hosted issue already contained assets.zip before "
            "the ticket command ran.\n"
            f"Observed attachment sha: {initial_state.attachment_sha}"
        )
    if validation.observation.requested_command != config.requested_command:
        raise AssertionError(
            "Precondition failed: TS-383 did not preserve the intended hosted ticket "
            "command.\n"
            f"Expected command: {' '.join(config.requested_command)}\n"
            f"Observed command: {validation.observation.requested_command_text}"
        )


def _assert_runtime_expectations(
    config: TrackStateCliHostedLfsRestrictionConfig,
    validation: TrackStateCliHostedLfsRestrictionValidationResult,
    result: dict[str, object],
) -> None:
    observation = validation.observation
    payload = observation.result.json_payload
    _record_step(
        result,
        step=1,
        status="passed",
        action=(
            "Execute `trackstate attachment upload --issue TS-22 --file assets.zip "
            "--target hosted --provider github` against the hosted GitHub repository."
        ),
        observed=(
            "The command executed against the live hosted repository and returned "
            f"process exit code {observation.result.exit_code}."
        ),
    )

    step_two_failures: list[str] = []
    error: dict[str, object] = {}
    if not isinstance(payload, dict):
        step_two_failures.append(
            "The command did not return a machine-readable JSON error envelope."
        )
    else:
        if payload.get("ok") is not False:
            step_two_failures.append(
                f"Expected `ok: false`, but observed `{payload.get('ok')}`."
            )
        raw_error = payload.get("error")
        if not isinstance(raw_error, dict):
            step_two_failures.append(
                "The response did not include an `error` object."
            )
        else:
            error = raw_error

    result["observed_error_code"] = error.get("code")
    result["observed_error_category"] = error.get("category")
    result["observed_error_exit_code"] = error.get("exitCode")
    result["observed_error_message"] = error.get("message")
    result["observed_error_details"] = error.get("details")

    if observation.result.exit_code != config.expected_exit_code:
        step_two_failures.append(
            "Expected process exit code "
            f"{config.expected_exit_code}, but observed {observation.result.exit_code}."
        )
    if error.get("exitCode") != config.expected_exit_code:
        step_two_failures.append(
            "Expected `error.exitCode` "
            f"{config.expected_exit_code}, but observed {error.get('exitCode')}."
        )
    if error.get("code") not in config.accepted_error_codes:
        step_two_failures.append(
            "Expected unsupported error code "
            f"{config.accepted_error_codes}, but observed `{error.get('code')}`."
        )
    if error.get("category") != config.expected_error_category:
        step_two_failures.append(
            "Expected error category "
            f"`{config.expected_error_category}`, but observed `{error.get('category')}`."
        )

    message = str(error.get("message", ""))
    lowered_message = message.lower()
    missing_fragments = [
        fragment
        for fragment in config.required_error_message_fragments
        if fragment not in lowered_message
    ]
    if missing_fragments:
        step_two_failures.append(
            "Expected the visible CLI message to explain that hosted Git LFS upload is "
            "unsupported/not implemented, but it was missing fragments "
            f"{missing_fragments}. Observed message: `{message}`."
        )

    missing_stdout_fragments = [
        fragment
        for fragment in config.required_stdout_fragments
        if fragment not in observation.result.stdout
    ]
    if missing_stdout_fragments:
        step_two_failures.append(
            "Expected the visible CLI JSON output to include markers "
            f"{missing_stdout_fragments}, but they were absent from stdout."
        )

    if validation.final_state.attachment_exists:
        step_two_failures.append(
            "The hosted repository gained `assets.zip` even though the upload should "
            "have been rejected. Observed attachment sha: "
            f"{validation.final_state.attachment_sha}."
        )

    _record_step(
        result,
        step=2,
        status="failed" if step_two_failures else "passed",
        action="Inspect the exit code, error object, visible CLI output, and remote attachment state.",
        observed=json.dumps(
            {
                "payload": payload,
                "step_two_failures": step_two_failures,
                "remote_attachment_exists": validation.final_state.attachment_exists,
                "remote_attachment_sha": validation.final_state.attachment_sha,
            },
            indent=2,
            sort_keys=True,
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Checked the user-visible CLI JSON output to confirm it stayed in an error "
            "state and clearly explained the hosted Git LFS restriction."
        ),
        observed=observation.output,
        matched=not any(
            failure
            for failure in step_two_failures
            if "message" in failure.lower()
            or "error category" in failure.lower()
            or "error code" in failure.lower()
            or "stdout" in failure.lower()
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Checked the hosted repository after the command to confirm "
            "`DEMO/TS-22/attachments/assets.zip` was still absent."
        ),
        observed=(
            f"attachment_exists={validation.final_state.attachment_exists}, "
            f"attachment_sha={validation.final_state.attachment_sha}"
        ),
        matched=not validation.final_state.attachment_exists,
    )
    if step_two_failures:
        raise AssertionError(
            "Step 2 failed: the hosted LFS upload response did not match the explicit "
            "unsupported contract required by TS-383.\n"
            + "\n".join(f"- {failure}" for failure in step_two_failures)
            + f"\nObserved payload: {payload}"
            + f"\nstdout:\n{observation.result.stdout}"
            + f"\nstderr:\n{observation.result.stderr}"
        )


def _assert_cleanup(
    validation: TrackStateCliHostedLfsRestrictionValidationResult,
) -> None:
    if validation.cleanup_error is not None:
        raise AssertionError(
            "Cleanup failed after the hosted LFS upload scenario completed.\n"
            f"{validation.cleanup_error}"
        )


def _validation_payload(
    validation: TrackStateCliHostedLfsRestrictionValidationResult,
) -> dict[str, object]:
    return {
        "executed_command": validation.observation.executed_command_text,
        "compiled_binary_path": validation.observation.compiled_binary_path,
        "working_directory": validation.observation.repository_path,
        "local_attachment_path": validation.local_attachment_path,
        "stdout": validation.observation.result.stdout,
        "stderr": validation.observation.result.stderr,
        "exit_code": validation.observation.result.exit_code,
        "initial_state": _state_payload(validation.initial_state),
        "final_state": _state_payload(validation.final_state),
        "setup_actions": list(validation.setup_actions),
        "cleanup_actions": list(validation.cleanup_actions),
        "cleanup_error": validation.cleanup_error,
    }


def _state_payload(
    state: TrackStateCliHostedLfsRestrictionRemoteState,
) -> dict[str, object]:
    return {
        "zip_lfs_rule_present": state.zip_lfs_rule_present,
        "zip_lfs_rule_line": state.zip_lfs_rule_line,
        "present_fixture_paths": list(state.present_fixture_paths),
        "issue_main_exists": state.issue_main_exists,
        "issue_main_content": state.issue_main_content,
        "attachment_exists": state.attachment_exists,
        "attachment_sha": state.attachment_sha,
    }


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    result.setdefault("steps", []).append(
        {
            "step": step,
            "status": status,
            "action": action,
            "observed": observed,
        }
    )


def _record_human_verification(
    result: dict[str, object],
    *,
    check: str,
    observed: str,
    matched: bool,
) -> None:
    result.setdefault("human_verification", []).append(
        {
            "check": check,
            "observed": observed,
            "matched": matched,
        }
    )


def _write_pass_outputs(result: dict[str, object]) -> None:
    status_line = "✅ PASSED"
    jira_lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status_line}",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Verified the live hosted CLI upload against {{{result['repository']}}} on branch {{{result['branch']}}} with a real `assets.zip` file and the repository's existing `*.zip` Git LFS rule.",
        "* Verified the process exit code, machine-readable error object, visible JSON output, and that the hosted issue remained without the uploaded attachment.",
        "",
        "h4. Result",
        "* Automation matched the expected unsupported contract: `ok: false`, unsupported error code/category, exit code `5`, and a user-facing message explaining hosted Git LFS upload is not implemented.",
        "* Human-style verification matched the expected result: the visible CLI output stayed in the expected unsupported state and the hosted repository did not gain `DEMO/TS-22/attachments/assets.zip`.",
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
    ]
    markdown_lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {status_line}",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_SUMMARY}",
        "",
        "## What was automated",
        f"- Exercised the live hosted CLI upload against `{result['repository']}` on `{result['branch']}` using a real `assets.zip` file and the repository's existing `*.zip` Git LFS rule.",
        "- Verified the process exit code, machine-readable error object, visible JSON output, and that the hosted issue remained without the uploaded attachment.",
        "",
        "## Result",
        "- Automation matched the expected unsupported contract: `ok: false`, unsupported error code/category, exit code `5`, and a user-facing message explaining hosted Git LFS upload is not implemented.",
        "- Human-style verification matched the expected result: the visible CLI output stayed in the expected unsupported state and the hosted repository did not gain `DEMO/TS-22/attachments/assets.zip`.",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
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
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()


def _write_failure_outputs(
    config: TrackStateCliHostedLfsRestrictionConfig,
    result: dict[str, object],
) -> None:
    error_text = str(result.get("error", "AssertionError: unknown failure"))
    short_error = error_text.splitlines()[0] if error_text else "AssertionError"
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    initial_state = result.get("initial_state", {})
    final_state = result.get("final_state", {})
    steps = list(result.get("steps", []))
    human_checks = list(result.get("human_verification", []))
    step_one = next((step for step in steps if step.get("step") == 1), None)
    step_two = next((step for step in steps if step.get("step") == 2), None)
    observed_payload = {
        "code": result.get("observed_error_code"),
        "category": result.get("observed_error_category"),
        "exitCode": result.get("observed_error_exit_code"),
        "message": result.get("observed_error_message"),
        "details": result.get("observed_error_details"),
    }
    actual_vs_expected = (
        "Expected the hosted CLI to fail explicitly with an unsupported-operation style "
        "error (`ok: false`, unsupported machine-readable code/category, and a user-facing "
        "message stating hosted Git LFS upload is not implemented). "
        f"Instead it returned exit code `{result.get('exit_code')}` and error payload "
        f"`{json.dumps(observed_payload, sort_keys=True)}`."
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} - {TEST_CASE_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Verified the live hosted CLI upload against {{{result.get('repository', config.repository)}}} on branch {{{result.get('branch', config.branch)}}} using a real `assets.zip` file and the repository's existing `*.zip` Git LFS rule.",
        "* Verified the process exit code, machine-readable error object, visible JSON output, and whether the hosted issue gained an attachment.",
        "",
        "h4. Result",
        f"* Step 1 {'passed' if step_one and step_one.get('status') == 'passed' else 'failed'}: the command executed against the live hosted repository and returned process exit code {{{result.get('exit_code')}}}.",
        "* Step 2 failed: the returned contract did not match the explicit unsupported result required by the ticket.",
        f"* Actual vs Expected: {actual_vs_expected}",
        "",
        "h4. Human-style verification",
        *[
            (
                f"* {'Matched' if check.get('matched') else 'Did not match'}: "
                f"{check.get('check')} Observed: {check.get('observed')}"
            )
            for check in human_checks
        ],
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
        "",
        "h4. Logs / Evidence",
        "{code:json}",
        stdout.rstrip(),
        "{code}",
        "{code}",
        stderr.rstrip(),
        "{code}",
    ]
    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} - {TEST_CASE_SUMMARY}",
        "",
        "## What was automated",
        f"- Exercised the live hosted CLI upload against `{result.get('repository', config.repository)}` on `{result.get('branch', config.branch)}` using a real `assets.zip` file and the repository's existing `*.zip` Git LFS rule.",
        "- Verified the process exit code, machine-readable error object, visible JSON output, and whether the hosted issue gained an attachment.",
        "",
        "## Result",
        f"- Step 1 {'passed' if step_one and step_one.get('status') == 'passed' else 'failed'}: the command executed against the live hosted repository and returned process exit code `{result.get('exit_code')}`.",
        "- Step 2 failed because the returned contract was not the explicit unsupported result required by the ticket.",
        f"- **Expected:** explicit unsupported failure for hosted Git LFS upload with `ok: false`, unsupported code/category, exit code `5`, and a message saying hosted Git LFS upload is not implemented.",
        f"- **Actual:** {actual_vs_expected}",
        "",
        "## Human-style verification",
        *[
            f"- **{'Matched' if check.get('matched') else 'Did not match'}:** {check.get('check')} Observed: {check.get('observed')}"
            for check in human_checks
        ],
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
        "",
        "## Observed stdout",
        "```json",
        stdout.rstrip(),
        "```",
        "",
        "## Observed stderr",
        "```text",
        stderr.rstrip(),
        "```",
    ]
    bug_lines = [
        f"h3. Bug: {TEST_CASE_SUMMARY}",
        "",
        "h4. Environment",
        f"* Repository: {{{result.get('repository', config.repository)}}}",
        f"* Branch: {{{result.get('branch', config.branch)}}}",
        f"* URL / target: {{hosted GitHub repository {result.get('repository', config.repository)}}}",
        f"* OS: {{{platform.platform()}}}",
        f"* Python: {{{sys.version.split()[0]}}}",
        f"* Working directory: {{{result.get('working_directory')}}}",
        f"* Local upload file: {{{result.get('local_attachment_path')}}}",
        "",
        "h4. Steps to Reproduce",
        f"# Execute command: {{ {result.get('requested_command')} }}",
        "# Inspect the exit code and error object.",
        "",
        "h4. Step Results",
        f"* Step 1 ✅ Preconditions passed: `.gitattributes` contained `{{{config.required_gitattributes_fragment}}}`, the hosted `DEMO` project exposed the seeded `TS-22` issue, and no pre-existing `assets.zip` attachment was present.",
        f"* Step 1 ✅ Command execution completed and returned exit code `{{{result.get('exit_code')}}}`.",
        "* Step 2 ❌ The returned contract did not match the explicit unsupported result required by the ticket.",
        f"* Step 2 ❌ Observed error payload: {{ {json.dumps(observed_payload, sort_keys=True)} }}",
        f"* Step 2 ❌ The user-visible message was `{{{result.get('observed_error_message')}}}` instead of a message explaining that hosted Git LFS upload is not implemented.",
        "",
        "h4. Expected Result",
        "* The command should fail with `ok: false`, an unsupported machine-readable error code/category, process exit code `5`, `error.exitCode` `5`, and a message explaining that hosted Git LFS upload is not implemented.",
        "",
        "h4. Actual Result",
        f"* The command returned process exit code `{{{result.get('exit_code')}}}` and error payload {{ {json.dumps(observed_payload, sort_keys=True)} }}.",
        "* The hosted repository correctly remained without `DEMO/TS-22/attachments/assets.zip`, so the defect is the surfaced error contract rather than an unexpected upload success.",
        "",
        "h4. Logs / Error Output",
        "{code:text}",
        str(result.get("traceback", "")).rstrip(),
        "{code}",
        "{code:json}",
        stdout.rstrip(),
        "{code}",
        "{code}",
        stderr.rstrip(),
        "{code}",
        "",
        "h4. Notes",
        f"* Initial state: {{{json.dumps(initial_state, sort_keys=True)}}}",
        f"* Final state: {{{json.dumps(final_state, sort_keys=True)}}}",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_text,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
