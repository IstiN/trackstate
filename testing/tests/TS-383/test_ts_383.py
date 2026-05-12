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
    if not isinstance(payload, dict):
        raise AssertionError(
            "Step 2 failed: the hosted LFS upload command did not return a machine-"
            "readable JSON error envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}"
        )
    if payload.get("ok") is not False:
        raise AssertionError(
            "Expected result failed: the hosted LFS upload command did not return "
            "`ok: false`.\n"
            f"Observed payload: {payload}"
        )

    error = payload.get("error")
    if not isinstance(error, dict):
        raise AssertionError(
            "Step 2 failed: the hosted LFS upload response did not include an `error` "
            f"object.\nObserved payload: {payload}"
        )

    result["observed_error_code"] = error.get("code")
    result["observed_error_category"] = error.get("category")
    result["observed_error_exit_code"] = error.get("exitCode")
    result["observed_error_message"] = error.get("message")
    result["observed_error_details"] = error.get("details")

    if observation.result.exit_code != config.expected_exit_code:
        raise AssertionError(
            "Step 1 failed: executing the hosted LFS upload command did not return the "
            "expected unsupported exit code.\n"
            f"Expected exit code: {config.expected_exit_code}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"Observed payload: {payload}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}"
        )
    if error.get("exitCode") != config.expected_exit_code:
        raise AssertionError(
            "Step 2 failed: the hosted LFS upload error object did not return the "
            "expected machine-readable exit code.\n"
            f"Expected error.exitCode: {config.expected_exit_code}\n"
            f"Observed error.exitCode: {error.get('exitCode')}\n"
            f"Observed payload: {payload}"
        )

    if error.get("code") not in config.accepted_error_codes:
        raise AssertionError(
            "Step 2 failed: the hosted LFS upload command did not return an explicit "
            "unsupported machine-readable code.\n"
            f"Accepted codes: {config.accepted_error_codes}\n"
            f"Observed code: {error.get('code')}\n"
            f"Observed payload: {payload}"
        )
    if error.get("category") != config.expected_error_category:
        raise AssertionError(
            "Step 2 failed: the hosted LFS upload command did not classify the failure "
            "as unsupported.\n"
            f"Expected category: {config.expected_error_category}\n"
            f"Observed category: {error.get('category')}\n"
            f"Observed payload: {payload}"
        )

    message = str(error.get("message", ""))
    lowered_message = message.lower()
    missing_fragments = [
        fragment
        for fragment in config.required_error_message_fragments
        if fragment not in lowered_message
    ]
    if missing_fragments:
        raise AssertionError(
            "Expected result failed: the visible CLI error message did not explicitly "
            "tell the user that hosted Git LFS upload is unsupported or not implemented.\n"
            f"Missing message fragments: {missing_fragments}\n"
            f"Observed message: {message}\n"
            f"Observed payload: {payload}"
        )

    for fragment in config.required_stdout_fragments:
        if fragment not in observation.result.stdout:
            raise AssertionError(
                "Human-style verification failed: the visible CLI output did not show "
                "the expected unsupported JSON envelope markers.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}"
            )

    if validation.final_state.attachment_exists:
        raise AssertionError(
            "Expected result failed: the hosted repository gained assets.zip even though "
            "the LFS-tracked upload should have been rejected.\n"
            f"Observed attachment sha: {validation.final_state.attachment_sha}"
        )

    _record_step(
        result,
        step=1,
        status="passed",
        action=(
            "Execute `trackstate attachment upload --issue TS-22 --file assets.zip "
            "--target hosted --provider github` against the hosted GitHub repository."
        ),
        observed=(
            f"Exit code {observation.result.exit_code}; stdout returned a JSON error "
            f"envelope with code `{error.get('code')}`."
        ),
    )
    _record_step(
        result,
        step=2,
        status="passed",
        action="Inspect the exit code and error object.",
        observed=json.dumps(payload, indent=2, sort_keys=True),
    )
    _record_human_verification(
        result,
        check=(
            "Verified the user-visible CLI output stayed in an error state, described "
            "the hosted Git LFS restriction, and did not report a successful upload."
        ),
        observed=observation.output,
    )
    _record_human_verification(
        result,
        check=(
            "Verified the hosted issue remained without an `assets.zip` attachment after "
            "the failed command."
        ),
        observed=(
            f"attachment_exists={validation.final_state.attachment_exists}, "
            f"attachment_sha={validation.final_state.attachment_sha}"
        ),
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
) -> None:
    result.setdefault("human_verification", []).append(
        {
            "check": check,
            "observed": observed,
        }
    )


def _write_pass_outputs(result: dict[str, object]) -> None:
    summary = (
        f"TS-383 passed against `{result['repository']}` on `{result['branch']}`: the "
        "hosted CLI rejected the LFS-tracked `assets.zip` upload with an explicit "
        "unsupported error and the remote issue stayed unchanged."
    )
    jira_lines = [
        "h3. TS-383 Passed",
        "",
        f"*Repository:* {{{result['repository']}}}",
        f"*Branch:* {{{result['branch']}}}",
        f"*Command:* {{{result['requested_command']}}}",
        f"*Observed error code:* {{{result.get('observed_error_code')}}}",
        f"*Observed error category:* {{{result.get('observed_error_category')}}}",
        f"*Observed error exit code:* {{{result.get('observed_error_exit_code')}}}",
        "",
        "*Automation checks*",
        "# Verified the hosted repository already tracked `*.zip` via Git LFS in `.gitattributes`.",
        "# Seeded a temporary hosted `TS-22` issue inside the live `DEMO` project index and executed the CLI upload command from a clean working directory containing `assets.zip`.",
        "# Confirmed the command returned `ok: false`, an unsupported error code/category, and no attachment was created remotely.",
        "",
        "*Real user verification*",
        "# Checked the visible CLI JSON output to confirm the failure stayed explicit and did not report a successful upload.",
        "# Checked the hosted repository state after the command and confirmed `DEMO/TS-22/attachments/assets.zip` was still absent.",
        "",
        f"*Observed stdout:* {{code:json}}{result['stdout']}{{code}}",
    ]
    markdown_lines = [
        f"## {summary}",
        "",
        f"- **Repository:** `{result['repository']}`",
        f"- **Branch:** `{result['branch']}`",
        f"- **Command:** `{result['requested_command']}`",
        f"- **Observed error code:** `{result.get('observed_error_code')}`",
        f"- **Observed error category:** `{result.get('observed_error_category')}`",
        f"- **Observed error exit code:** `{result.get('observed_error_exit_code')}`",
        "",
        "### Automation",
        "1. Verified the hosted repo `.gitattributes` already tracked `*.zip` through Git LFS.",
        "2. Seeded a temporary hosted `TS-22` issue inside the live `DEMO` project index and ran the CLI upload scenario with a real `assets.zip` file.",
        "3. Confirmed the command returned an explicit unsupported JSON error and that no remote attachment was created.",
        "",
        "### Real human-style verification",
        "1. Checked the user-visible CLI output to confirm it stayed in an error state and did not show a success payload.",
        "2. Checked the hosted issue state after the command and confirmed `assets.zip` never appeared in the issue attachments path.",
        "",
        "### Observed stdout",
        "```json",
        str(result["stdout"]).rstrip(),
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
        "h3. TS-383 Failed",
        "",
        f"*Repository:* {{{result.get('repository', config.repository)}}}",
        f"*Branch:* {{{result.get('branch', config.branch)}}}",
        f"*Command:* {{{result.get('requested_command')}}}",
        f"*Failure:* {{{short_error}}}",
        "",
        "*Which step failed*",
        "# Step 1 (execute hosted upload command) "
        + ("passed." if result.get("exit_code") is not None else "did not complete."),
        "# Step 2 (inspect exit code and error object) failed because the returned error contract did not match the explicit unsupported result required by the ticket.",
        "",
        "*Actual vs Expected*",
        f"* Expected: explicit unsupported failure for hosted Git LFS upload with machine-readable unsupported code/category and a message saying the upload is not implemented.",
        f"* Actual: {actual_vs_expected}",
        "",
        "*Human verification*",
        "# Checked the visible CLI output and confirmed the user would see the observed error payload below.",
        "# Checked the hosted repository state after the command; the attachment remained absent, so the defect is in error classification/message rather than an unexpected successful upload.",
        "",
        f"*Observed stdout:* {{code:json}}{stdout}{{code}}",
        f"*Observed stderr:* {{code}}{stderr}{{code}}",
    ]
    markdown_lines = [
        "## TS-383 failed",
        "",
        f"- **Repository:** `{result.get('repository', config.repository)}`",
        f"- **Branch:** `{result.get('branch', config.branch)}`",
        f"- **Command:** `{result.get('requested_command')}`",
        f"- **Failure:** `{short_error}`",
        "",
        "### Which step failed",
        "1. Step 1 executed the hosted upload command against the live GitHub repository.",
        "2. Step 2 failed while inspecting the exit code and error object because the returned contract was not the explicit unsupported result required by the ticket.",
        "",
        "### Actual vs Expected",
        f"- **Expected:** explicit unsupported failure for hosted Git LFS upload with `ok: false`, an unsupported machine-readable code/category, and a message stating the upload is not implemented.",
        f"- **Actual:** {actual_vs_expected}",
        "",
        "### Human-style verification",
        "1. Checked the visible CLI output and confirmed the user would see the observed error payload below.",
        "2. Checked the hosted repository state after the command and confirmed `assets.zip` still was not created, so the defect is the surfaced error contract.",
        "",
        "### Observed stdout",
        "```json",
        stdout.rstrip(),
        "```",
        "",
        "### Observed stderr",
        "```text",
        stderr.rstrip(),
        "```",
    ]
    bug_lines = [
        f"# Bug report for {TICKET_KEY}",
        "",
        "## Steps to reproduce",
        (
            "1. Execute command: "
            f"`{result.get('requested_command')}`.\n"
            f"   - ✅ Preconditions were satisfied: `.gitattributes` contained "
            f"`{config.required_gitattributes_fragment}`, the hosted `DEMO` project exposed a seeded "
            "`TS-22` issue, and the issue had no pre-existing `assets.zip` attachment.\n"
            f"   - ✅ The command executed and returned exit code `{result.get('exit_code')}`.\n"
            f"   - Visible CLI output at this step:\n\n```json\n{stdout.rstrip()}\n```"
        ),
        (
            "2. Inspect the exit code and error object.\n"
            "   - ❌ This step failed because the response did not expose the explicit "
            "unsupported error contract required by the ticket.\n"
            f"   - Observed error payload: `{json.dumps(observed_payload, sort_keys=True)}`\n"
            f"   - Visible stderr at the failure point:\n\n```text\n{stderr.rstrip()}\n```"
        ),
        "",
        "## Exact error message or assertion failure",
        "```text",
        str(result.get("traceback", "")).rstrip(),
        "```",
        "",
        "## Actual vs Expected",
        f"- **Expected:** explicit unsupported failure for hosted Git LFS upload with `ok: false`, unsupported code/category, and a message saying hosted Git LFS upload is not implemented.",
        f"- **Actual:** {actual_vs_expected}",
        "",
        "## Environment details",
        f"- Repository: `{result.get('repository', config.repository)}`",
        f"- Branch: `{result.get('branch', config.branch)}`",
        f"- OS: `{platform.platform()}`",
        f"- Python: `{sys.version.split()[0]}`",
        f"- Working directory: `{result.get('working_directory')}`",
        f"- Local upload file: `{result.get('local_attachment_path')}`",
        "",
        "## Remote repository state",
        f"- Initial state: `{json.dumps(initial_state, sort_keys=True)}`",
        f"- Final state: `{json.dumps(final_state, sort_keys=True)}`",
        "",
        "## Logs",
        "```json",
        stdout.rstrip(),
        "```",
        "",
        "```text",
        stderr.rstrip(),
        "```",
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
