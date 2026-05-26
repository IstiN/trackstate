from __future__ import annotations

import json
import platform
from pathlib import Path
import sys
import traceback
import unittest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_attachment_upload_boundary_validator import (  # noqa: E402
    TrackStateCliAttachmentUploadBoundaryValidator,
)
from testing.core.config.trackstate_cli_attachment_upload_boundary_config import (  # noqa: E402
    TrackStateCliAttachmentUploadBoundaryConfig,
)
from testing.core.models.trackstate_cli_attachment_upload_boundary_result import (  # noqa: E402
    TrackStateCliAttachmentUploadBoundaryRepositoryState,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.tests.support.trackstate_cli_attachment_upload_boundary_probe_factory import (  # noqa: E402
    create_trackstate_cli_attachment_upload_boundary_probe,
)

TICKET_KEY = "TS-387"
TEST_CASE_TITLE = "CLI Attachment Upload — Multi-file rejection boundary"
RUN_COMMAND = (
    "mkdir -p outputs && PYTHONPATH=. python3 -m unittest discover "
    "-s testing/tests/TS-387 -p 'test_*.py' -v"
)
INPUT_DIR = REPO_ROOT / "input" / TICKET_KEY
OUTPUTS_DIR = REPO_ROOT / "outputs"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
DISCUSSIONS_RAW_PATH = INPUT_DIR / "pr_discussions_raw.json"


class CliAttachmentUploadMultiFileBoundaryTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = REPO_ROOT
        self.config = TrackStateCliAttachmentUploadBoundaryConfig.from_defaults()
        self.validator = TrackStateCliAttachmentUploadBoundaryValidator(
            probe=create_trackstate_cli_attachment_upload_boundary_probe(
                self.repository_root
            )
        )

    def test_attachment_upload_rejects_multiple_file_flags(self) -> None:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        result = self._result_template()

        try:
            validation = self.validator.validate(config=self.config)
            result.update(
                {
                    "requested_command": validation.observation.requested_command_text,
                    "executed_command": validation.observation.executed_command_text,
                    "repository_path": validation.observation.repository_path,
                    "compiled_binary_path": validation.observation.compiled_binary_path,
                    "fallback_reason": validation.observation.fallback_reason,
                    "stdout": validation.observation.result.stdout,
                    "stderr": validation.observation.result.stderr,
                    "output": validation.observation.output,
                    "json_payload": validation.observation.result.json_payload,
                    "initial_state": self._state_payload(validation.initial_state),
                    "final_state": self._state_payload(validation.final_state),
                }
            )

            failures: list[str] = []
            failures.extend(self._collect_exact_command_failures(validation.observation))
            failures.extend(self._collect_initial_fixture_failures(validation.initial_state))

            runtime_failures = self._collect_runtime_failures(validation.observation)
            repository_failures = self._collect_repository_side_effect_failures(
                initial_state=validation.initial_state,
                final_state=validation.final_state,
            )
            if runtime_failures or repository_failures:
                result["product_failure"] = True
            failures.extend(runtime_failures)
            failures.extend(repository_failures)

            _record_step(
                result,
                step=1,
                status="passed" if not runtime_failures and not repository_failures else "failed",
                action=(
                    "Execute `trackstate attachment upload --issue TS-22 --file "
                    "file1.png --file file2.png --target local` from the seeded local "
                    "TrackState repository."
                ),
                observed=self._step_observation_text(
                    validation.observation,
                    validation.final_state,
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Observed the user-visible CLI JSON output to confirm it clearly "
                    "reported a single-file validation failure instead of a success "
                    "upload envelope."
                ),
                observed=(
                    f"exit_code={validation.observation.result.exit_code}; "
                    f"visible_output={validation.observation.output or '<empty>'}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Inspected the local repository the same way a user would after the "
                    "command: attachment files on disk and git history."
                ),
                observed=self._repository_observation_text(validation.final_state),
            )

            if failures:
                raise AssertionError("\n\n".join(failures))

            _write_pass_outputs(result)
        except Exception as error:  # noqa: BLE001
            result["error"] = f"{type(error).__name__}: {error}"
            result["traceback"] = traceback.format_exc()
            _write_failure_outputs(result, include_bug_description=result["product_failure"])
            raise

    def _collect_exact_command_failures(
        self,
        observation: TrackStateCliCommandObservation,
    ) -> list[str]:
        failures: list[str] = []
        if observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-387 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}",
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-387 must execute a repository-local compiled "
                "binary so the seeded repository stays the current working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}",
            )
        elif observation.executed_command[0] != observation.compiled_binary_path:
            failures.append(
                "Precondition failed: TS-387 did not run the compiled repository-local "
                "CLI binary.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Compiled binary path: {observation.compiled_binary_path}",
            )
        return failures

    def _collect_initial_fixture_failures(
        self,
        state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-22 before "
                "executing the duplicate-file upload scenario.\n"
                f"Observed repository state:\n{self._describe_state(state)}",
            )
        if state.attachment_directory_exists or state.uploaded_attachment_paths:
            failures.append(
                "Precondition failed: the seeded repository already contained uploaded "
                "attachments before TS-387 ran.\n"
                f"Observed repository state:\n{self._describe_state(state)}",
            )
        if state.head_commit_count != 1:
            failures.append(
                "Precondition failed: TS-387 expected a single seed commit before the "
                "upload command executed.\n"
                f"Observed repository state:\n{self._describe_state(state)}",
            )
        return failures

    def _collect_runtime_failures(
        self,
        observation: TrackStateCliCommandObservation,
    ) -> list[str]:
        failures: list[str] = []
        payload = observation.result.json_payload

        if self.config.expected_exit_code is None:
            if observation.result.exit_code == 0:
                failures.append(
                    "Step 1 failed: executing the exact duplicate-file command "
                    "succeeded instead of failing with a validation error.\n"
                    f"Observed exit code: {observation.result.exit_code}\n"
                    f"Repository path: {observation.repository_path}\n"
                    f"Requested command: {observation.requested_command_text}\n"
                    f"Executed command: {observation.executed_command_text}\n"
                    f"Fallback reason: {observation.fallback_reason}\n"
                    f"stdout:\n{observation.result.stdout}\n"
                    f"stderr:\n{observation.result.stderr}",
                )
        elif observation.result.exit_code != self.config.expected_exit_code:
            failures.append(
                "Step 1 failed: executing the exact duplicate-file command did not fail "
                "with the expected validation exit code.\n"
                f"Expected exit code: {self.config.expected_exit_code}\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"Repository path: {observation.repository_path}\n"
                f"Requested command: {observation.requested_command_text}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}",
            )

        if not isinstance(payload, dict):
            failures.append(
                "Step 1 failed: the duplicate-file CLI invocation did not return a "
                "machine-readable JSON envelope.\n"
                f"Observed stdout:\n{observation.result.stdout}\n"
                f"Observed stderr:\n{observation.result.stderr}",
            )
            return failures

        if payload.get("ok") is not False:
            failures.append(
                "Expected result failed: the duplicate-file invocation did not return "
                "`ok: false`.\n"
                f"Observed payload: {payload}",
            )

        error = payload.get("error")
        if not isinstance(error, dict):
            failures.append(
                "Step 1 failed: the failure envelope did not include an `error` object.\n"
                f"Observed payload: {payload}",
            )
        elif error.get("category") != self.config.expected_error_category:
            failures.append(
                "Expected result failed: the duplicate-file invocation did not classify "
                "the outcome as a validation error.\n"
                f"Expected category: {self.config.expected_error_category}\n"
                f"Observed error: {error}",
            )

        output = observation.output
        if not self._contains_single_file_validation_message(output):
            failures.append(
                "Human-style verification failed: the visible CLI output did not tell "
                "the user that only one file may be uploaded per invocation.\n"
                f"Observed output:\n{output}",
            )

        for fragment in self.config.required_failure_stdout_fragments:
            if fragment not in observation.result.stdout:
                failures.append(
                    "Human-style verification failed: the visible CLI output did not "
                    "show the expected failure envelope markers.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.result.stdout}",
                )

        if '"command": "attachment-upload"' in observation.result.stdout:
            failures.append(
                "Expected result failed: the visible CLI output still reported an "
                "attachment-upload success payload instead of rejecting the duplicate "
                "`--file` options.\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )
        return failures

    def _collect_repository_side_effect_failures(
        self,
        *,
        initial_state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
        final_state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if final_state.attachment_directory_exists:
            failures.append(
                "Expected result failed: the repository gained an attachment directory "
                "even though the duplicate-file command should have been rejected.\n"
                f"Observed repository state:\n{self._describe_state(final_state)}",
            )
        if final_state.uploaded_attachment_paths:
            failures.append(
                "Expected result failed: the duplicate-file command uploaded at least "
                "one attachment instead of leaving the issue unchanged.\n"
                f"Uploaded attachment paths: {final_state.uploaded_attachment_paths}\n"
                f"Observed repository state:\n{self._describe_state(final_state)}",
            )
        if final_state.head_commit_count != initial_state.head_commit_count:
            failures.append(
                "Expected result failed: the duplicate-file command created a new git "
                "commit even though no upload should occur.\n"
                f"Initial commit count: {initial_state.head_commit_count}\n"
                f"Final commit count: {final_state.head_commit_count}\n"
                f"Observed repository state:\n{self._describe_state(final_state)}",
            )
        if final_state.head_commit_subject != initial_state.head_commit_subject:
            failures.append(
                "Expected result failed: the duplicate-file command changed HEAD from "
                "the seed commit, which indicates the CLI persisted upload side "
                "effects.\n"
                f"Initial HEAD: {initial_state.head_commit_subject}\n"
                f"Final HEAD: {final_state.head_commit_subject}\n"
                f"Observed repository state:\n{self._describe_state(final_state)}",
            )
        return failures

    def _contains_single_file_validation_message(self, output: str) -> bool:
        normalized = output.lower()
        if "file" not in normalized:
            return False
        return any(
            marker in normalized for marker in self.config.accepted_error_message_markers
        )

    def _describe_state(
        self,
        state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> str:
        return "\n".join(
            (
                f"issue_main_exists={state.issue_main_exists}",
                f"attachment_directory_exists={state.attachment_directory_exists}",
                f"uploaded_attachment_paths={state.uploaded_attachment_paths}",
                f"head_commit_subject={state.head_commit_subject}",
                f"head_commit_count={state.head_commit_count}",
                f"git_status_lines={state.git_status_lines}",
                "issue_main_content=",
                state.issue_main_content or "<missing>",
            )
        )

    def _result_template(self) -> dict[str, object]:
        return {
            "ticket": TICKET_KEY,
            "test_case_title": TEST_CASE_TITLE,
            "run_command": RUN_COMMAND,
            "repository_root": str(REPO_ROOT),
            "os": platform.platform(),
            "requested_command": " ".join(self.config.requested_command),
            "expected_result": (
                "The command fails with a validation error indicating that exactly one "
                "file must be provided per invocation. No files are uploaded (AC2)."
            ),
            "steps": [],
            "human_verification": [],
            "product_failure": False,
        }

    def _step_observation_text(
        self,
        observation: TrackStateCliCommandObservation,
        final_state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> str:
        payload_text = (
            json.dumps(observation.result.json_payload, indent=2, sort_keys=True)
            if isinstance(observation.result.json_payload, dict)
            else "<non-json>"
        )
        return "\n".join(
            (
                f"exit_code={observation.result.exit_code}",
                f"repository_path={observation.repository_path}",
                f"executed_command={observation.executed_command_text}",
                f"payload={payload_text}",
                f"uploaded_attachment_paths={final_state.uploaded_attachment_paths}",
                f"head_commit_subject={final_state.head_commit_subject}",
                f"head_commit_count={final_state.head_commit_count}",
            )
        )

    def _repository_observation_text(
        self,
        state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> str:
        return (
            f"attachment_directory_exists={state.attachment_directory_exists}; "
            f"uploaded_attachment_paths={state.uploaded_attachment_paths}; "
            f"head_commit_subject={state.head_commit_subject}; "
            f"head_commit_count={state.head_commit_count}; "
            f"git_status_lines={state.git_status_lines}"
        )

    def _state_payload(
        self,
        state: TrackStateCliAttachmentUploadBoundaryRepositoryState,
    ) -> dict[str, object]:
        return {
            "issue_main_exists": state.issue_main_exists,
            "attachment_directory_exists": state.attachment_directory_exists,
            "uploaded_attachment_paths": list(state.uploaded_attachment_paths),
            "issue_main_content": state.issue_main_content,
            "git_status_lines": list(state.git_status_lines),
            "head_commit_subject": state.head_commit_subject,
            "head_commit_count": state.head_commit_count,
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
    RESPONSE_PATH.write_text(_tracker_rework_summary(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_comment_body(result, passed=True), encoding="utf-8")
    _write_review_replies(result, passed=True)


def _write_failure_outputs(
    result: dict[str, object],
    *,
    include_bug_description: bool,
) -> None:
    error = str(result.get("error", "AssertionError: TS-387 failed"))
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
    RESPONSE_PATH.write_text(
        _tracker_rework_summary(result, passed=False),
        encoding="utf-8",
    )
    PR_BODY_PATH.write_text(_pr_comment_body(result, passed=False), encoding="utf-8")
    _write_review_replies(result, passed=False)
    if include_bug_description:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _tracker_rework_summary(result: dict[str, object], *, passed: bool) -> str:
    lines = [
        "h3. PR Rework Result",
        "",
        "*Fixed:* Resolved the TS-387 merge conflicts in the attachment-upload boundary "
        "config, compiled-local CLI helper, and test so the branch keeps the exact "
        "ticket command, shared helper extraction, and rework artifact output.",
        f"*Test Run:* `{RUN_COMMAND}`",
        f"*Result:* {'✅ PASSED' if passed else '❌ FAILED'}",
    ]
    if passed:
        lines.append("*Summary:* 1 passed, 0 failed.")
    else:
        lines.extend(
            [
                "*Summary:* 0 passed, 1 failed.",
                f"*Error:* {result.get('error')}",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _pr_comment_body(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error')}`."
    )
    lines = [
        "## Rework completed",
        "",
        "- Resolved the TS-387 merge conflicts in the attachment-upload boundary config, "
        "compiled-local CLI framework helper, and failing test module.",
        "- Preserved the exact ticket command (`trackstate attachment upload --issue "
        "TS-22 --file file1.png --file file2.png --target local`) and the neutral "
        "compiled-local helper extraction used by TS-387.",
        f"- {rerun_summary}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "## Failure details",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": _review_reply_text(result=result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}, indent=2) + "\n",
        encoding="utf-8",
    )


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [
        thread
        for thread in threads
        if isinstance(thread, dict)
        and thread.get("resolved") is False
        and thread.get("rootCommentId") is not None
        and thread.get("threadId") is not None
    ]


def _review_reply_text(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        f"Re-ran `{RUN_COMMAND}`: passed (`1 passed, 0 failed`)."
        if passed
        else f"Re-ran `{RUN_COMMAND}`: failed with `{result.get('error', 'unknown error')}`."
    )
    return (
        "Fixed: resolved the TS-387 merge conflicts in the attachment-upload boundary "
        "config, compiled-local CLI helper, and test module while keeping the exact "
        "ticket command plus neutral shared-helper layering intact. "
        f"{rerun_summary}"
    )


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY} regression: duplicate `--file` upload still succeeds",
            "",
            "## Steps to reproduce",
            "1. Seed a local TrackState repository containing issue `TS-22`, `file1.png`, "
            "and `file2.png` at the repository root.",
            "2. Run `trackstate attachment upload --issue TS-22 --file file1.png --file "
            "file2.png --target local` from that repository.",
            "3. Inspect the CLI JSON output, attachment directory, and git history.",
            "",
            "## Expected result",
            str(result.get("expected_result", "")),
            "",
            "## Actual result",
            "The command exits successfully, returns an attachment-upload success payload "
            "instead of a validation error, uploads `TS/TS-22/attachments/file2.png`, "
            "and creates the git commit `Upload attachment to TS-22`.",
            "",
            "## Missing or broken production capability",
            "The public `trackstate attachment upload` CLI does not enforce the documented "
            "single-file-per-invocation boundary for duplicate `--file` flags. The "
            "command should reject duplicate `--file` input before any repository write "
            "or git commit occurs.",
            "",
            "## Failing command",
            "```text",
            str(result.get("requested_command", "")),
            "```",
            "",
            "## Exact failing output",
            "```text",
            f"stdout:\n{result.get('stdout', '')}\n",
            f"stderr:\n{result.get('stderr', '')}\n",
            str(result.get("error", "")),
            "```",
            "",
            "## Repository side effects",
            "```json",
            json.dumps(result.get("final_state", {}), indent=2, sort_keys=True),
            "```",
        ]
    ).strip() + "\n"


if __name__ == "__main__":
    unittest.main()
