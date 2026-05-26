from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_unpushed_branch_validator import (  # noqa: E402
    TrackStateCliReleaseUnpushedBranchValidator,
)
from testing.core.config.trackstate_cli_release_unpushed_branch_config import (  # noqa: E402
    TrackStateCliReleaseUnpushedBranchConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_unpushed_branch_result import (  # noqa: E402
    TrackStateCliReleaseUnpushedBranchRemoteState,
    TrackStateCliReleaseUnpushedBranchRepositoryState,
    TrackStateCliReleaseUnpushedBranchStoredFile,
    TrackStateCliReleaseUnpushedBranchValidationResult,
)
from testing.tests.support.trackstate_cli_release_unpushed_branch_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_unpushed_branch_probe,
)

TICKET_KEY = "TS-593"
TICKET_SUMMARY = (
    "Release creation with unpushed branch fails with explicit target_commitish API error"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-593/test_ts_593.py"
RUN_COMMAND = "python testing/tests/TS-593/test_ts_593.py"


class Ts593ReleaseUnpushedBranchScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-593/config.yaml"
        self.config = TrackStateCliReleaseUnpushedBranchConfig.from_file(self.config_path)
        self.validator = TrackStateCliReleaseUnpushedBranchValidator(
            probe=create_trackstate_cli_release_unpushed_branch_probe(
                self.repository_root,
            ),
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []

        failures.extend(self._assert_exact_command(validation.observation))
        failures.extend(self._assert_initial_fixture(validation, result))
        failures.extend(self._validate_runtime(validation, result))
        failures.extend(self._validate_repository_state(validation, result))
        failures.extend(self._validate_remote_state(validation, result))
        failures.extend(self._validate_cleanup(validation))

        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseUnpushedBranchValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        error_dict = error if isinstance(error, dict) else None
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "ticket_command": self.config.ticket_command,
            "requested_command": validation.observation.requested_command_text,
            "executed_command": validation.observation.executed_command_text,
            "compiled_binary_path": validation.observation.compiled_binary_path,
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "repository": self.config.repository,
            "base_branch": self.config.base_branch,
            "unpushed_branch": self.config.unpushed_branch,
            "project_key": self.config.project_key,
            "project_name": self.config.project_name,
            "issue_key": self.config.issue_key,
            "issue_summary": self.config.issue_summary,
            "remote_origin_url": self.config.remote_origin_url,
            "expected_release_tag": self.config.expected_release_tag,
            "expected_attachment_relative_path": self.config.expected_attachment_relative_path,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "error": error_dict,
            "observed_error_code": error_dict.get("code") if isinstance(error_dict, dict) else None,
            "observed_error_category": error_dict.get("category")
            if isinstance(error_dict, dict)
            else None,
            "observed_provider": payload_dict.get("provider")
            if isinstance(payload_dict, dict)
            else None,
            "observed_output_format": payload_dict.get("output")
            if isinstance(payload_dict, dict)
            else None,
            "observed_error_message": error_dict.get("message")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_details": error_dict.get("details")
            if isinstance(error_dict, dict)
            else None,
            "initial_state": _repository_state_to_dict(
                validation.initial_repository_state,
            ),
            "final_state": _repository_state_to_dict(validation.final_repository_state),
            "initial_remote_state": _remote_state_to_dict(validation.initial_remote_state),
            "final_remote_state": _remote_state_to_dict(validation.final_remote_state),
            "setup_actions": list(validation.setup_actions),
            "pre_run_cleanup_actions": list(validation.pre_run_cleanup_actions),
            "cleanup_actions": list(validation.cleanup_actions),
            "cleanup_error": validation.cleanup_error,
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
                "Precondition failed: TS-593 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}",
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-593 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}",
            )
        return failures

    def _assert_initial_fixture(
        self,
        validation: TrackStateCliReleaseUnpushedBranchValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        initial_state = validation.initial_repository_state
        initial_remote_state = validation.initial_remote_state

        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-101 before "
                "running TS-593.\n"
                f"Observed state:\n{_describe_repository_state(initial_state)}",
            )
        if not initial_state.source_file_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain report.pdf "
                "before running TS-593.\n"
                f"Observed state:\n{_describe_repository_state(initial_state)}",
            )
        if initial_state.expected_attachment_exists or initial_state.stored_files:
            failures.append(
                "Precondition failed: the seeded repository already contained local "
                "attachment output before TS-593 ran.\n"
                f"Observed state:\n{_describe_repository_state(initial_state)}",
            )
        if initial_state.manifest_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained "
                "attachments.json before TS-593 ran.\n"
                f"Observed state:\n{_describe_repository_state(initial_state)}",
            )
        if initial_state.remote_origin_url != self.config.remote_origin_url:
            failures.append(
                "Precondition failed: the seeded repository origin did not point at the "
                "configured live setup repository.\n"
                f"Expected origin: {self.config.remote_origin_url}\n"
                f"Observed state:\n{_describe_repository_state(initial_state)}",
            )
        if initial_state.current_branch != self.config.unpushed_branch:
            failures.append(
                "Precondition failed: the active local branch was not the unpushed branch "
                "required by TS-593.\n"
                f"Expected branch: {self.config.unpushed_branch}\n"
                f"Observed state:\n{_describe_repository_state(initial_state)}",
            )
        if initial_remote_state.branch_exists_on_remote:
            failures.append(
                "Precondition failed: the remote repository already contains the "
                f"{self.config.unpushed_branch!r} branch.\n"
                f"Observed remote state:\n{_describe_remote_state(initial_remote_state)}",
            )
        if (
            initial_remote_state.release_count != 0
            or initial_remote_state.matching_tag_refs
        ):
            failures.append(
                "Precondition failed: TS-593 expected no pre-existing release/tag artifacts "
                f"for {self.config.expected_release_tag} after pre-run cleanup.\n"
                f"Observed remote state:\n{_describe_remote_state(initial_remote_state)}",
            )

        if not failures:
            _record_step(
                result,
                step=0,
                status="passed",
                action=(
                    "Prepare a disposable local TrackState repository on the unpushed "
                    f"branch `{self.config.unpushed_branch}` and confirm the remote does "
                    f"not already contain `{self.config.expected_release_tag}` artifacts."
                ),
                observed=(
                    f"current_branch={initial_state.current_branch}; "
                    f"remote_origin_url={initial_state.remote_origin_url}; "
                    "pre_run_cleanup_actions="
                    f"{list(validation.pre_run_cleanup_actions)}; "
                    f"initial_remote_state={_compact_text(_describe_remote_state(initial_remote_state))}"
                ),
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseUnpushedBranchValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        stdout = observation.result.stdout
        stderr = observation.result.stderr
        visible_error = _visible_error_text(payload, stdout=stdout, stderr=stderr)
        result["visible_error_text"] = visible_error

        if observation.result.exit_code == 0:
            failures.append(
                "Step 1 failed: executing the ticket command succeeded even though the "
                "active local branch was not pushed to the remote.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}",
            )
            return failures

        if not visible_error:
            failures.append(
                "Step 1 failed: the CLI failed, but it did not surface any caller-visible "
                "error text on stdout or stderr.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}",
            )
            return failures

        lowered_error = visible_error.lower()
        missing_fragments = [
            fragment
            for fragment in self.config.required_visible_fragments
            if fragment not in lowered_error
        ]
        required_any_matches = [
            fragment
            for fragment in self.config.required_any_visible_fragments
            if fragment in lowered_error
        ]
        prohibited_fragments = [
            fragment
            for fragment in self.config.prohibited_visible_fragments
            if fragment in lowered_error
        ]

        if not missing_fragments and (
            not self.config.required_any_visible_fragments or required_any_matches
        ) and not prohibited_fragments:
            _record_step(
                result,
                step=1,
                status="passed",
                action=self.config.ticket_command,
                observed=(
                    f"exit_code={observation.result.exit_code}; "
                    f"visible_error={visible_error}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the exact terminal output shown to a user surfaced the "
                    "GitHub release-creation branch-resolution failure with `422` and "
                    "`target_commitish` details."
                ),
                observed=visible_error,
            )
            return failures

        result["failure_mode"] = "missing_explicit_target_commitish_error"
        result["product_gap"] = (
            "The local github-releases upload path did not surface the explicit GitHub "
            "API target_commitish validation failure required for an unpushed local branch."
        )
        if missing_fragments:
            failures.append(
                "Step 1 failed: the visible CLI error did not include the required "
                "GitHub API branch-resolution fragments for TS-593.\n"
                f"Missing fragments: {missing_fragments}\n"
                f"Visible output:\n{visible_error}\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}",
            )
        if self.config.required_any_visible_fragments and not required_any_matches:
            failures.append(
                "Step 1 failed: the visible CLI error did not expose an explicit GitHub "
                "API validation status such as `Validation Failed` or `Unprocessable "
                "Entity`.\n"
                f"Expected one of: {list(self.config.required_any_visible_fragments)}\n"
                f"Visible output:\n{visible_error}\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}",
            )
        if prohibited_fragments:
            failures.append(
                "Step 1 failed: the command regressed to a generic provider failure instead "
                "of surfacing the explicit GitHub API branch-resolution error.\n"
                f"Prohibited fragments present: {prohibited_fragments}\n"
                f"Visible output:\n{visible_error}\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}",
            )
        return failures

    def _validate_repository_state(
        self,
        validation: TrackStateCliReleaseUnpushedBranchValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_repository_state

        if final_state.expected_attachment_exists:
            failures.append(
                "Step 2 failed: the file was written to the local repository attachment "
                "path even though release creation should have failed on the unpushed "
                "branch.\n"
                f"Observed state:\n{_describe_repository_state(final_state)}",
            )
        if final_state.stored_files:
            failures.append(
                "Step 2 failed: the repository gained files under the local attachments "
                "directory even though the upload should have failed before asset storage.\n"
                f"Observed state:\n{_describe_repository_state(final_state)}",
            )
        if final_state.manifest_exists:
            failures.append(
                "Step 2 failed: the repository gained attachments.json even though the "
                "release creation call failed for the unpushed branch.\n"
                f"Observed state:\n{_describe_repository_state(final_state)}",
            )
        if final_state.git_status_lines:
            failures.append(
                "Step 2 failed: the failed upload left local repository changes behind.\n"
                f"Observed state:\n{_describe_repository_state(final_state)}",
            )

        if not failures:
            _record_step(
                result,
                step=2,
                status="passed",
                action=(
                    "Inspect the local repository after the failed upload attempt."
                ),
                observed=(
                    f"expected_attachment_exists={final_state.expected_attachment_exists}; "
                    f"manifest_exists={final_state.manifest_exists}; "
                    f"stored_files={_format_stored_files(final_state.stored_files)}; "
                    f"git_status={list(final_state.git_status_lines)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified from a user's perspective that no local attachment file or "
                    "manifest appeared in the repository after the failed command."
                ),
                observed=(
                    f"attachment_directory_exists={final_state.attachment_directory_exists}; "
                    f"manifest_exists={final_state.manifest_exists}; "
                    f"stored_files={_format_stored_files(final_state.stored_files)}"
                ),
            )
        return failures

    def _validate_remote_state(
        self,
        validation: TrackStateCliReleaseUnpushedBranchValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_remote_state = validation.final_remote_state

        if final_remote_state.branch_exists_on_remote:
            failures.append(
                "Step 3 failed: the scenario unexpectedly created or exposed the "
                f"{self.config.unpushed_branch!r} branch on the remote repository.\n"
                f"Observed remote state:\n{_describe_remote_state(final_remote_state)}",
            )
        if final_remote_state.release_count != 0:
            failures.append(
                "Step 3 failed: the failed upload still created a GitHub Release for the "
                f"expected tag {self.config.expected_release_tag}.\n"
                f"Observed remote state:\n{_describe_remote_state(final_remote_state)}",
            )
        if final_remote_state.matching_tag_refs:
            failures.append(
                "Step 3 failed: the failed upload still created a Git tag/ref for the "
                f"expected release tag {self.config.expected_release_tag}.\n"
                f"Observed remote state:\n{_describe_remote_state(final_remote_state)}",
            )

        if not failures:
            _record_step(
                result,
                step=3,
                status="passed",
                action=(
                    "Inspect the remote repository state after the failed upload attempt."
                ),
                observed=(
                    f"release_count={final_remote_state.release_count}; "
                    f"matching_tag_refs={list(final_remote_state.matching_tag_refs)}; "
                    f"branch_exists_on_remote={final_remote_state.branch_exists_on_remote}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the observable GitHub-side outcome remained empty: no "
                    "release container or tag appeared for the failed upload."
                ),
                observed=_describe_remote_state(final_remote_state),
            )
        return failures

    def _validate_cleanup(
        self,
        validation: TrackStateCliReleaseUnpushedBranchValidationResult,
    ) -> list[str]:
        if validation.cleanup_error:
            return [
                "Cleanup failed after TS-593 completed.\n"
                f"{validation.cleanup_error}",
            ]
        return []


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts593ReleaseUnpushedBranchScenario()

    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", {}) if "result" in locals() else {}
        if not isinstance(failure_result, dict):
            failure_result = {}
        failure_result.update(
            {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
                "error": f"{type(error).__name__}: {error}",
                "traceback": traceback.format_exc(),
            }
        )
        _write_failure_outputs(failure_result)
        raise


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

    visible_error = _as_text(result.get("visible_error_text"))
    expected_release_tag = _as_text(result.get("expected_release_tag"))
    expected_attachment_path = _as_text(result.get("expected_attachment_relative_path"))
    remote_origin_url = _as_text(result.get("remote_origin_url"))
    unpushed_branch = _as_text(result.get("unpushed_branch"))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        (
            f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a "
            f"disposable local TrackState repository configured with "
            f"{_jira_inline('attachmentStorage.mode = github-releases')} and Git origin "
            f"{_jira_inline(remote_origin_url)}."
        ),
        (
            f"* Ran the command from the active local branch "
            f"{_jira_inline(unpushed_branch)}, which was verified to be absent from the "
            "remote repository before the upload attempt."
        ),
        (
            f"* Inspected the caller-visible CLI failure output plus local path "
            f"{_jira_inline(expected_attachment_path)} and remote release/tag state for "
            f"{_jira_inline(expected_release_tag)}."
        ),
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the fixture repository was prepared on the unpushed local branch and the remote started clean.",
        "* ✅ Step 2 passed: the CLI failed with explicit GitHub API branch-resolution guidance naming `422` and `target_commitish`.",
        f"* Observed terminal output: {_jira_inline(visible_error)}",
        "* ✅ Step 3 passed: no local attachment file or manifest was written.",
        "* ✅ Step 4 passed: no remote release or tag was created for the failed upload.",
        "* ✅ Human-style verification passed: the real terminal output a user would see clearly identified the GitHub API validation failure, and the user-visible local/remote side effects remained absent.",
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
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable "
            "local TrackState repository configured with "
            "`attachmentStorage.mode = github-releases` and the live setup Git remote."
        ),
        (
            f"- Ran the command from the active local branch `{unpushed_branch}`, "
            "confirmed absent from the remote before execution."
        ),
        (
            f"- Inspected the caller-visible CLI failure output plus local path "
            f"`{expected_attachment_path}` and remote release/tag state for "
            f"`{expected_release_tag}`."
        ),
        "",
        "## Result",
        "- Step 1 passed: the fixture repository was prepared on the unpushed local branch and the remote started clean.",
        "- Step 2 passed: the CLI failed with explicit GitHub API branch-resolution guidance naming `422` and `target_commitish`.",
        f"- Observed terminal output: `{visible_error}`",
        "- Step 3 passed: no local attachment file or manifest was written.",
        "- Step 4 passed: no remote release or tag was created for the failed upload.",
        "- Human-style verification passed: the real terminal output a user would see clearly identified the GitHub API validation failure, and the user-visible local/remote side effects remained absent.",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error")) or "AssertionError: unknown failure"
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error_message,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    stdout = _as_text(result.get("stdout"))
    stderr = _as_text(result.get("stderr"))
    visible_error = _visible_error_text(result.get("payload"), stdout=stdout, stderr=stderr)
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    final_state_text = json.dumps(result.get("final_state"), indent=2, sort_keys=True)
    final_remote_state_text = json.dumps(
        result.get("final_remote_state"),
        indent=2,
        sort_keys=True,
    )
    expected_path = _as_text(result.get("expected_attachment_relative_path"))
    expected_release_tag = _as_text(result.get("expected_release_tag"))
    unpushed_branch = _as_text(result.get("unpushed_branch"))
    product_gap = _as_text(result.get("product_gap"))
    observed_error_code = _as_text(result.get("observed_error_code"))
    observed_error_category = _as_text(result.get("observed_error_category"))
    observed_error_message = _as_text(result.get("observed_error_message"))
    observed_details = result.get("observed_error_details")
    observed_reason = ""
    if isinstance(observed_details, dict):
        observed_reason = _as_text(observed_details.get("reason"))

    actual_vs_expected = (
        "Actual: the CLI returned "
        f"`{observed_error_code}` / `{observed_error_category}` with message "
        f"`{observed_error_message or visible_error}`"
        + (
            f" and reason `{observed_reason}`"
            if observed_reason
            else ""
        )
        + ". Expected: the caller-visible output should explicitly surface the GitHub "
        "API branch-resolution failure, including `422` / `Validation Failed` (or "
        "`Unprocessable Entity`) and `target_commitish`."
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        (
            f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a "
            f"disposable local TrackState repository configured with "
            f"{_jira_inline('attachmentStorage.mode = github-releases')} and checked out "
            f"on {_jira_inline(unpushed_branch)}."
        ),
        (
            f"* Inspected the caller-visible CLI output, local repository path "
            f"{_jira_inline(expected_path)}, and remote release/tag state for "
            f"{_jira_inline(expected_release_tag)}."
        ),
        "",
        "h4. Result",
        "* ✅ Step 0 passed: the fixture repository was prepared on the unpushed local branch and the remote started clean.",
        (
            "* ❌ Step 1 failed: the CLI did not present the required explicit GitHub API "
            "branch-resolution failure for an unpushed branch."
        ),
        f"* Actual vs Expected: {_jira_inline(actual_vs_expected)}",
        f"* Observed visible output: {_jira_inline(visible_error)}",
        "* Step 2 local-state observation:",
        "{code:json}",
        final_state_text,
        "{code}",
        "* Step 3 remote-state observation:",
        "{code:json}",
        final_remote_state_text,
        "{code}",
        *([f"* Product gap: {product_gap}"] if product_gap else []),
        "",
        "h4. Observed command output",
        "{code}",
        observed_output,
        "{code}",
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
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable "
            "local TrackState repository configured with "
            "`attachmentStorage.mode = github-releases` and checked out on the "
            f"unpushed branch `{unpushed_branch}`."
        ),
        (
            f"- Inspected the caller-visible CLI output, local repository path "
            f"`{expected_path}`, and remote release/tag state for "
            f"`{expected_release_tag}`."
        ),
        "",
        "## Result",
        "- Step 0 passed: the fixture repository was prepared on the unpushed local branch and the remote started clean.",
        "- ❌ Step 1 failed: the CLI did not present the required explicit GitHub API branch-resolution failure for an unpushed branch.",
        f"- Actual vs Expected: {actual_vs_expected}",
        f"- Observed visible output: `{visible_error}`",
        "- Step 2 local-state observation:",
        "```json",
        final_state_text,
        "```",
        "- Step 3 remote-state observation:",
        "```json",
        final_remote_state_text,
        "```",
        *([f"- Product gap: {product_gap}"] if product_gap else []),
        "",
        "## Observed command output",
        "```text",
        observed_output,
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    bug_lines = [
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository path: `{_as_text(result.get('repository_path'))}`",
        f"- Command: `{_as_text(result.get('ticket_command'))}`",
        f"- OS: `{platform.system()}`",
        f"- Git remote: `{_as_text(result.get('remote_origin_url'))}`",
        f"- Local active branch: `{unpushed_branch}`",
        f"- Expected release tag: `{expected_release_tag}`",
        "",
        "## Steps to reproduce",
        "1. ✅ Configure the project with `attachmentStorage.mode = github-releases`. Observed: the disposable fixture repository used that storage mode.",
        (
            f"2. ✅ Work on a new local branch `{unpushed_branch}` that does not exist in "
            "the GitHub remote repository. Observed: the fixture repository checked out "
            "that branch locally and the remote branch lookup was empty before the command."
        ),
        (
            f"3. ❌ Execute CLI command: `{_as_text(result.get('ticket_command'))}`. "
            f"Observed: exit code `{_as_text(result.get('exit_code'))}` with visible output "
            f"`{visible_error}`."
        ),
        (
            "4. ❌ Inspect the command output. Observed: the caller-visible failure did "
            "not clearly surface the required explicit GitHub API branch-resolution "
            "error for `target_commitish` / HTTP 422."
        ),
        (
            f"5. ✅ Inspect local and remote side effects. Observed local state at "
            f"`{expected_path}` and remote state for `{expected_release_tag}` are shown "
            "below."
        ),
        "",
        "## Expected result",
        "- The command should fail because `target_commitish` cannot be resolved on GitHub for the unpushed local branch.",
        "- The user-visible output should explicitly surface the GitHub API failure, such as `422 Unprocessable Entity` / `Validation Failed` and `target_commitish`.",
        "- No local attachment file, local manifest entry, remote release, or remote tag should be created.",
        "",
        "## Actual result",
        f"- The user-visible output was: `{visible_error}`",
        f"- {actual_vs_expected}",
        "- Detailed local and remote state observations are included below.",
        "",
        "## Exact error / stack trace",
        "```text",
        _as_text(result.get("traceback")).rstrip(),
        "```",
        "",
        "## Captured CLI output",
        "```text",
        observed_output,
        "```",
        "",
        "## Final local repository state",
        "```json",
        final_state_text,
        "```",
        "",
        "## Final remote repository state",
        "```json",
        final_remote_state_text,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


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


def _repository_state_to_dict(
    state: TrackStateCliReleaseUnpushedBranchRepositoryState,
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
        "current_branch": state.current_branch,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _remote_state_to_dict(
    state: TrackStateCliReleaseUnpushedBranchRemoteState,
) -> dict[str, object]:
    return {
        "branch_exists_on_remote": state.branch_exists_on_remote,
        "release_count": state.release_count,
        "release_ids": list(state.release_ids),
        "release_names": list(state.release_names),
        "release_asset_names": list(state.release_asset_names),
        "matching_tag_refs": list(state.matching_tag_refs),
    }


def _describe_repository_state(
    state: TrackStateCliReleaseUnpushedBranchRepositoryState,
) -> str:
    return json.dumps(_repository_state_to_dict(state), indent=2, sort_keys=True)


def _describe_remote_state(
    state: TrackStateCliReleaseUnpushedBranchRemoteState,
) -> str:
    return json.dumps(_remote_state_to_dict(state), indent=2, sort_keys=True)


def _format_stored_files(
    stored_files: tuple[TrackStateCliReleaseUnpushedBranchStoredFile, ...],
) -> list[str]:
    return [
        f"{stored_file.relative_path} ({stored_file.size_bytes} bytes)"
        for stored_file in stored_files
    ]


def _visible_error_text(
    payload: object,
    *,
    stdout: str = "",
    stderr: str = "",
) -> str:
    fragments: list[str] = []
    payload_text = _json_visible_error_text(payload)
    if payload_text:
        fragments.append(payload_text)
    text_fragments = []
    if not (payload_text and _looks_like_json(stdout)):
        text_fragments.append(_collapse_output(stdout))
    if not (payload_text and _looks_like_json(stderr)):
        text_fragments.append(_collapse_output(stderr))
    for fragment in text_fragments:
        if fragment and all(fragment.lower() not in existing.lower() for existing in fragments):
            fragments.append(fragment)
    return " | ".join(fragment for fragment in fragments if fragment)


def _json_visible_error_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        details = error.get("details")
        fragments = [
            _as_text(error.get("message")).strip(),
            _as_text(error.get("code")).strip(),
            _as_text(error.get("category")).strip(),
        ]
        if isinstance(details, dict):
            fragments.extend(
                _as_text(details.get(key)).strip()
                for key in ("reason", "provider", "target", "path", "file", "repository")
            )
        return " | ".join(fragment for fragment in fragments if fragment)

    fragments = [
        _as_text(payload.get("message")).strip(),
        _as_text(payload.get("status")).strip(),
    ]
    errors = payload.get("errors")
    if isinstance(errors, list):
        for item in errors:
            if not isinstance(item, dict):
                continue
            fragments.extend(
                _as_text(item.get(key)).strip()
                for key in ("resource", "code", "field", "message")
            )
    return " | ".join(fragment for fragment in fragments if fragment)


def _collapse_output(text: str) -> str:
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") or stripped.startswith("[")


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    fragments: list[str] = []
    if stdout.strip():
        fragments.append(f"stdout:\n{stdout.rstrip()}")
    if stderr.strip():
        fragments.append(f"stderr:\n{stderr.rstrip()}")
    return "\n\n".join(fragments) or "<empty>"


def _format_supporting_evidence(
    *,
    payload: object,
    stdout: str,
    stderr: str,
) -> str:
    evidence = []
    if isinstance(payload, dict):
        evidence.append(
            "Observed JSON payload:\n"
            + json.dumps(payload, indent=2, sort_keys=True)
        )
    evidence.append(_observed_command_output(stdout=stdout, stderr=stderr))
    return "\n\n".join(evidence)


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _jira_inline(value: str) -> str:
    return "{{" + value + "}}"


if __name__ == "__main__":
    main()
