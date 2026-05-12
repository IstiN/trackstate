from __future__ import annotations

import json
import platform
import traceback
from datetime import datetime
import hashlib
from pathlib import Path
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_local_attachment_upload_validator import (  # noqa: E402
    TrackStateCliLocalAttachmentUploadValidator,
)
from testing.core.config.trackstate_cli_local_attachment_upload_config import (  # noqa: E402
    TrackStateCliLocalAttachmentUploadConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_local_attachment_upload_result import (  # noqa: E402
    TrackStateCliLocalAttachmentUploadRepositoryState,
    TrackStateCliLocalAttachmentUploadStoredFile,
    TrackStateCliLocalAttachmentUploadValidationResult,
)
from testing.tests.support.trackstate_cli_local_attachment_upload_probe_factory import (  # noqa: E402
    create_trackstate_cli_local_attachment_upload_probe,
)

TICKET_KEY = "TS-381"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


class Ts381LocalAttachmentUploadScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-381/config.yaml"
        self.config = TrackStateCliLocalAttachmentUploadConfig.from_file(self.config_path)
        self.validator = TrackStateCliLocalAttachmentUploadValidator(
            probe=create_trackstate_cli_local_attachment_upload_probe(self.repository_root)
        )
        self._source_sha256 = hashlib.sha256(self.config.source_file_bytes).hexdigest()

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []
        failures.extend(self._assert_exact_command(validation.observation))
        failures.extend(self._assert_initial_fixture(validation.initial_state))
        failures.extend(self._validate_runtime(validation, result))
        failures.extend(self._validate_repository_state(validation, result))
        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliLocalAttachmentUploadValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        data = payload_dict.get("data") if isinstance(payload_dict, dict) else None
        attachment = data.get("attachment") if isinstance(data, dict) else None
        return {
            "ticket": TICKET_KEY,
            "ticket_command": self.config.ticket_command,
            "requested_command": validation.observation.requested_command_text,
            "executed_command": validation.observation.executed_command_text,
            "compiled_binary_path": validation.observation.compiled_binary_path,
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "source_file_name": self.config.source_file_name,
            "source_file_size_bytes": self.config.expected_size_bytes,
            "source_file_sha256": self._source_sha256,
            "expected_issue_key": self.config.expected_issue_key,
            "expected_attachment_name": self.config.expected_attachment_name,
            "expected_media_type": self.config.expected_media_type,
            "expected_attachment_directory": self.config.expected_attachment_directory,
            "observed_issue_key": data.get("issue") if isinstance(data, dict) else None,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "observed_attachment": attachment,
            "initial_state": _state_to_dict(validation.initial_state),
            "final_state": _state_to_dict(validation.final_state),
            "steps": [],
            "human_verification": [],
        }

    def _assert_exact_command(
        self,
        observation: TrackStateCliCommandObservation,
    ) -> list[str]:
        failures: list[str] = []
        if observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-381 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-381 must run a repository-local compiled binary "
                "so the seeded repository remains the current working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        initial_state: TrackStateCliLocalAttachmentUploadRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-22 before "
                "running TS-381.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.attachment_directory_exists or initial_state.stored_files:
            failures.append(
                "Precondition failed: the seeded repository already contained uploaded "
                "attachments before TS-381 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliLocalAttachmentUploadValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload

        if observation.result.exit_code != 0:
            failures.append(
                "Step 1 failed: executing the ticket command did not return a success "
                "exit code.\n"
                f"Expected exit code: 0\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )
        else:
            _record_step(
                result,
                step=1,
                status="passed",
                action=self.config.ticket_command,
                observed=(
                    f"exit_code=0; repository_path={observation.repository_path}; "
                    f"executed_command={observation.executed_command_text}"
                ),
            )

        if not isinstance(payload, dict):
            failures.append(
                "Step 2 failed: the command did not return a machine-readable JSON "
                "envelope.\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}"
            )
            return failures

        if payload.get("ok") is not True:
            failures.append(
                "Step 2 failed: the JSON envelope did not report `ok: true`.\n"
                f"Observed payload: {payload}"
            )

        data = payload.get("data")
        if not isinstance(data, dict):
            failures.append(
                "Step 2 failed: the JSON envelope did not include a `data` object.\n"
                f"Observed payload: {payload}"
            )
            return failures

        if data.get("issue") != self.config.expected_issue_key:
            failures.append(
                "Expected result failed: the success envelope did not expose the "
                "requested issue key.\n"
                f"Expected issue: {self.config.expected_issue_key}\n"
                f"Observed data: {data}"
            )
        result["observed_issue_key"] = data.get("issue")

        attachment = data.get("attachment")
        if not isinstance(attachment, dict):
            failures.append(
                "Step 2 failed: the success envelope did not include attachment "
                "metadata.\n"
                f"Observed payload: {payload}"
            )
            return failures

        result["observed_attachment"] = attachment
        observed_name = attachment.get("name")
        observed_media_type = attachment.get("mediaType")
        observed_size = attachment.get("sizeBytes")
        observed_id = attachment.get("id")
        observed_created_at = attachment.get("createdAt")
        observed_revision = attachment.get("revisionOrOid")

        if observed_name != self.config.expected_attachment_name:
            failures.append(
                "Step 2 failed: the JSON output did not preserve the requested "
                "attachment name.\n"
                f"Expected name: {self.config.expected_attachment_name}\n"
                f"Observed name: {observed_name}\n"
                f"Observed attachment payload: {attachment}"
            )
        if observed_media_type != self.config.expected_media_type:
            failures.append(
                "Step 2 failed: the JSON output did not report the PDF media type for "
                "the uploaded `sample.pdf` file.\n"
                f"Expected mediaType: {self.config.expected_media_type}\n"
                f"Observed mediaType: {observed_media_type}\n"
                f"Observed attachment payload: {attachment}"
            )
        if observed_size != self.config.expected_size_bytes:
            failures.append(
                "Expected result failed: the JSON output did not report the uploaded "
                "file size.\n"
                f"Expected sizeBytes: {self.config.expected_size_bytes}\n"
                f"Observed sizeBytes: {observed_size}\n"
                f"Observed attachment payload: {attachment}"
            )
        if not isinstance(observed_id, str) or not observed_id:
            failures.append(
                "Expected result failed: the JSON output did not include a non-empty "
                "`id` for the uploaded attachment.\n"
                f"Observed attachment payload: {attachment}"
            )
        if not isinstance(observed_revision, str) or not observed_revision:
            failures.append(
                "Expected result failed: the JSON output did not include a non-empty "
                "`revisionOrOid` value.\n"
                f"Observed attachment payload: {attachment}"
            )
        if not isinstance(observed_created_at, str) or not observed_created_at:
            failures.append(
                "Expected result failed: the JSON output did not include a non-empty "
                "`createdAt` timestamp.\n"
                f"Observed attachment payload: {attachment}"
            )
        else:
            try:
                datetime.fromisoformat(observed_created_at.replace("Z", "+00:00"))
            except ValueError as error:
                failures.append(
                    "Expected result failed: the JSON output returned an invalid "
                    "`createdAt` timestamp.\n"
                    f"Observed createdAt: {observed_created_at}\n"
                    f"Parser error: {error}"
                )

        _record_step(
            result,
            step=2,
            status="passed" if not failures else "failed",
            action="Inspect the JSON output.",
            observed=json.dumps(
                {
                    "ok": payload.get("ok"),
                    "issue": data.get("issue"),
                    "attachment": attachment,
                },
                indent=2,
                sort_keys=True,
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the visible CLI JSON output showed a success envelope with the "
                "issue key and attachment metadata fields a user would rely on."
            ),
            observed=observation.result.stdout.strip() or "<empty stdout>",
        )
        return failures

    def _validate_repository_state(
        self,
        validation: TrackStateCliLocalAttachmentUploadValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_state
        stored_files = final_state.stored_files
        observed_attachment = result.get("observed_attachment")
        attachment_id = (
            observed_attachment.get("id")
            if isinstance(observed_attachment, dict)
            else None
        )

        if not final_state.attachment_directory_exists:
            failures.append(
                "Expected result failed: the repository did not gain an attachments "
                "directory after the upload succeeded.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
            return failures

        if len(stored_files) != 1:
            failures.append(
                "Expected result failed: the repository did not contain exactly one "
                "uploaded attachment after TS-381 ran.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
            return failures

        stored_file = stored_files[0]
        if not stored_file.relative_path.startswith(
            f"{self.config.expected_attachment_directory}/"
        ):
            failures.append(
                "Expected result failed: the uploaded file was not stored under the "
                "issue attachments directory.\n"
                f"Expected directory: {self.config.expected_attachment_directory}\n"
                f"Observed stored file: {stored_file.relative_path}"
            )
        if stored_file.size_bytes != self.config.expected_size_bytes:
            failures.append(
                "Expected result failed: the physically stored attachment size did not "
                "match the uploaded source file.\n"
                f"Expected size: {self.config.expected_size_bytes}\n"
                f"Observed stored file: {stored_file.relative_path} "
                f"({stored_file.size_bytes} bytes)"
            )
        if stored_file.sha256 != self._source_sha256:
            failures.append(
                "Expected result failed: the physically stored attachment content did not "
                "match the uploaded source file.\n"
                f"Expected SHA-256: {self._source_sha256}\n"
                f"Observed stored file: {stored_file.relative_path}\n"
                f"Observed SHA-256: {stored_file.sha256}"
            )
        if isinstance(attachment_id, str) and attachment_id != stored_file.relative_path:
            failures.append(
                "Expected result failed: the JSON attachment id did not match the file "
                "that was physically stored in the repository.\n"
                f"Observed attachment id: {attachment_id}\n"
                f"Observed stored file: {stored_file.relative_path}"
            )

        _record_human_verification(
            result,
            check=(
                "Verified the repository side effect a local user would observe: one "
                "attachment file appeared under the issue attachments directory and its "
                "bytes matched the uploaded source file."
            ),
            observed=(
                f"stored_file={stored_file.relative_path}; "
                f"size_bytes={stored_file.size_bytes}; "
                f"sha256={stored_file.sha256}"
            ),
        )
        return failures


class CliAttachmentUploadLocalMetadataTest(unittest.TestCase):
    maxDiff = None

    def test_cli_attachment_upload_returns_canonical_metadata_envelope(self) -> None:
        scenario = Ts381LocalAttachmentUploadScenario()
        _, failures = scenario.execute()
        self.assertFalse(failures, "\n\n".join(failures))


def _state_to_dict(
    state: TrackStateCliLocalAttachmentUploadRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "attachment_directory_exists": state.attachment_directory_exists,
        "stored_files": [
            {
                "relative_path": file.relative_path,
                "size_bytes": file.size_bytes,
                "sha256": file.sha256,
            }
            for file in state.stored_files
        ],
        "git_status_lines": list(state.git_status_lines),
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _describe_state(
    state: TrackStateCliLocalAttachmentUploadRepositoryState,
) -> str:
    return "\n".join(
        (
            f"issue_main_exists={state.issue_main_exists}",
            f"attachment_directory_exists={state.attachment_directory_exists}",
            f"stored_files={[file.relative_path for file in state.stored_files]}",
            f"git_status_lines={state.git_status_lines}",
            f"head_commit_subject={state.head_commit_subject}",
            f"head_commit_count={state.head_commit_count}",
        )
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
        }
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
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    attachment = result.get("observed_attachment")
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        "* Seeded a disposable local TrackState repository with issue TS-22 and a local {{sample.pdf}} file.",
        "* Executed the exact ticket command from the repository working directory.",
        "* Inspected the visible JSON envelope for issue and attachment metadata fields.",
        "* Verified the repository side effect by checking the file stored under the issue {{attachments/}} directory.",
        "",
        "*Observed result*",
        (
            "* Matched the expected result."
            if passed
            else "* Did not match the expected result."
        ),
        (
            f"* Environment: repository path {{{{{result['repository_path']}}}}}, "
            f"OS {{{{{result['os']}}}}}, command {{{{{result['ticket_command']}}}}}."
        ),
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
        "",
        "*Observed attachment payload*",
        "{code}",
        json.dumps(attachment, indent=2, sort_keys=True) if isinstance(attachment, dict) else "<missing>",
        "{code}",
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
    attachment = result.get("observed_attachment")
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        "- Seeded a disposable local TrackState repository with issue `TS-22` and a local `sample.pdf` file.",
        f"- Ran the exact ticket command: `{result['ticket_command']}`.",
        "- Checked the visible JSON output for the issue key plus `id`, `name`, `mediaType`, `sizeBytes`, `createdAt`, and `revisionOrOid`.",
        "- Verified the uploaded file was physically stored under the issue `attachments/` directory.",
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
        "",
        "### Observed result",
        (
            "- Matched the expected result."
            if passed
            else "- Did not match the expected result."
        ),
        (
            f"- Environment: repository path `{result['repository_path']}`, "
            f"OS `{result['os']}`, command `{result['ticket_command']}`."
        ),
        "",
        "### Observed attachment payload",
        "```json",
        json.dumps(attachment, indent=2, sort_keys=True) if isinstance(attachment, dict) else "<missing>",
        "```",
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
    status = "passed" if passed else "failed"
    attachment = result.get("observed_attachment")
    return (
        f"# {TICKET_KEY} {status}\n\n"
        f"- Command: `{result['ticket_command']}`\n"
        f"- Repository path: `{result['repository_path']}`\n"
        f"- OS: `{result['os']}`\n"
        f"- Observed attachment payload: `{json.dumps(attachment, sort_keys=True) if isinstance(attachment, dict) else '<missing>'}`\n"
    )


def _bug_description(result: dict[str, object]) -> str:
    final_state = result.get("final_state")
    attachment = result.get("observed_attachment")
    stdout = str(result.get("stdout", ""))
    stderr = str(result.get("stderr", ""))
    traceback_text = str(result.get("traceback", result.get("error", "")))
    expected_name = result.get("expected_attachment_name")
    expected_media_type = result.get("expected_media_type")
    expected_issue = result.get("expected_issue_key")
    observed_issue = result.get("observed_issue_key")
    actual_name = attachment.get("name") if isinstance(attachment, dict) else None
    actual_media_type = (
        attachment.get("mediaType") if isinstance(attachment, dict) else None
    )
    stored_files = final_state.get("stored_files", []) if isinstance(final_state, dict) else []
    stored_file_summary = (
        ", ".join(
            f"{item['relative_path']} ({item['size_bytes']} bytes)"
            for item in stored_files
            if isinstance(item, dict)
        )
        or "<none>"
    )
    return "\n".join(
        [
            f"# {TICKET_KEY} - CLI attachment upload metadata does not match the ticket contract",
            "",
            "## Steps to Reproduce",
            "1. Execute command: `trackstate attachment upload --issue TS-22 --file sample.pdf --name \"Spec Document\" --target local`.",
            (
                "   - ✅ The command executed successfully with exit code 0 and returned a JSON envelope."
                if result.get("exit_code") == 0
                else f"   - ❌ The command failed with exit code {result.get('exit_code')}."
            ),
            f"   - Observed stdout: `{stdout.strip() or '<empty>'}`",
            "2. Inspect the JSON output.",
            (
                "   - ❌ The returned metadata did not match the expected ticket values."
                if isinstance(attachment, dict)
                else "   - ❌ The command did not return an attachment metadata object."
            ),
            (
                f"   - Expected issue `{expected_issue}`, attachment name `{expected_name}`, media type `{expected_media_type}`."
            ),
            (
                f"   - Actual issue `{observed_issue}`, "
                f"attachment name `{actual_name}`, media type `{actual_media_type}`."
                if isinstance(attachment, dict)
                else "   - Actual attachment payload was missing."
            ),
            f"   - Repository side effect: stored files under `attachments/`: `{stored_file_summary}`.",
            "",
            "## Actual vs Expected",
            f"- Expected: the success envelope should include issue `TS-22` and attachment metadata with `name` = `{expected_name}` and `mediaType` = `{expected_media_type}` while storing the uploaded file under the issue `attachments/` directory.",
            (
                f"- Actual: the command returned attachment metadata `{json.dumps(attachment, sort_keys=True)}` "
                f"and stored `{stored_file_summary}`. The stored file name was normalized to "
                f"`{actual_name}` without the original `.pdf` extension, which also caused the "
                f"reported media type to fall back to `{actual_media_type}`."
                if isinstance(attachment, dict)
                else "- Actual: the command did not return attachment metadata."
            ),
            "",
            "## Exact Error Message or Assertion Failure",
            "```text",
            traceback_text,
            "```",
            "",
            "## Environment",
            f"- Repository path: `{result.get('repository_path', '<unknown>')}`",
            f"- OS: `{result.get('os', platform.system())}`",
            f"- Command: `{result.get('ticket_command', '<unknown>')}`",
            f"- Config: `{result.get('config_path', '<unknown>')}`",
            "",
            "## Logs",
            "### stdout",
            "```text",
            stdout,
            "```",
            "### stderr",
            "```text",
            stderr,
            "```",
        ]
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    steps = result.get("steps")
    if not isinstance(steps, list) or not steps:
        return ["* No step results were recorded."]

    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} Step {step.get('step')}: {step.get('status')} - "
            f"{step.get('action')}"
        )
        lines.append(f"{prefix} Observed: {step.get('observed')}")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    checks = result.get("human_verification")
    if not isinstance(checks, list) or not checks:
        return ["* No human-style verification was recorded."]

    lines: list[str] = []
    for check in checks:
        if not isinstance(check, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(f"{prefix} {check.get('check')}")
        lines.append(f"{prefix} Observed: {check.get('observed')}")
    return lines


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts381LocalAttachmentUploadScenario()
    result: dict[str, object] | None = None
    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        if result is None:
            result = {
                "ticket": TICKET_KEY,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
                "steps": [],
                "human_verification": [],
                "stdout": "",
                "stderr": "",
                "os": platform.system(),
            }
        else:
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


if __name__ == "__main__":
    main()
