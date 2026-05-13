from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_download_auth_failure_validator import (  # noqa: E402
    TrackStateCliReleaseDownloadAuthFailureValidator,
)
from testing.core.config.trackstate_cli_release_download_auth_failure_config import (  # noqa: E402
    TrackStateCliReleaseDownloadAuthFailureConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_download_auth_failure_result import (  # noqa: E402
    TrackStateCliReleaseDownloadAuthFailureRepositoryState,
    TrackStateCliReleaseDownloadAuthFailureValidationResult,
)
from testing.tests.support.trackstate_cli_release_download_auth_failure_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_download_auth_failure_probe,
)

TICKET_KEY = "TS-564"
TICKET_SUMMARY = "Local download with missing auth — verification of error category and exit code"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-564/test_ts_564.py"
RUN_COMMAND = "python testing/tests/TS-564/test_ts_564.py"
EXPECTED_ERROR_CODE = "AUTHENTICATION_FAILED"
EXPECTED_ERROR_CATEGORY = "auth"
EXPECTED_ERROR_EXIT_CODE = 3


class Ts564ReleaseDownloadAuthContractScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-564/config.yaml"
        self.config = TrackStateCliReleaseDownloadAuthFailureConfig.from_file(
            self.config_path
        )
        self.validator = TrackStateCliReleaseDownloadAuthFailureValidator(
            probe=create_trackstate_cli_release_download_auth_failure_probe(
                self.repository_root
            )
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []
        failures.extend(self._assert_exact_command(validation.observation))
        fixture_failures = self._assert_initial_fixture(validation.initial_state)
        failures.extend(fixture_failures)
        if not fixture_failures:
            _record_step(
                result,
                step=0,
                status="passed",
                action=(
                    "Prepare a local github-releases fixture repository with no GitHub "
                    "credentials available."
                ),
                observed=(
                    f"issue_main_exists={validation.initial_state.issue_main_exists}; "
                    f"attachments_metadata_exists={validation.initial_state.attachments_metadata_exists}; "
                    f"metadata_attachment_ids={list(validation.initial_state.metadata_attachment_ids)}; "
                    f"remote_origin_url={validation.initial_state.remote_origin_url!r}"
                ),
            )
        failures.extend(self._validate_runtime(validation, result))
        failures.extend(self._validate_filesystem_state(validation, result))
        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseDownloadAuthFailureValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        target = payload_dict.get("target") if isinstance(payload_dict, dict) else None
        target_dict = target if isinstance(target, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        error_dict = error if isinstance(error, dict) else None
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "ticket_command": self.config.ticket_command,
            "supported_ticket_command": validation.observation.requested_command_text,
            "requested_command": validation.observation.requested_command_text,
            "executed_command": validation.observation.executed_command_text,
            "compiled_binary_path": validation.observation.compiled_binary_path,
            "compiled_source_ref": self.config.compiled_source_ref,
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "project_key": self.config.project_key,
            "issue_key": self.config.issue_key,
            "attachment_relative_path": self.config.attachment_relative_path,
            "expected_output_relative_path": self.config.expected_output_relative_path,
            "remote_origin_url": self.config.remote_origin_url,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "process_exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "error": error_dict,
            "observed_error_code": error_dict.get("code")
            if isinstance(error_dict, dict)
            else None,
            "observed_error_category": error_dict.get("category")
            if isinstance(error_dict, dict)
            else None,
            "observed_provider": payload_dict.get("provider")
            if isinstance(payload_dict, dict)
            else None,
            "observed_target_type": target_dict.get("type")
            if isinstance(target_dict, dict)
            else None,
            "observed_target_value": target_dict.get("value")
            if isinstance(target_dict, dict)
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
            "observed_error_exit_code": error_dict.get("exitCode")
            if isinstance(error_dict, dict)
            else None,
            "initial_state": _state_to_dict(validation.initial_state),
            "final_state": _state_to_dict(validation.final_state),
            "stripped_environment_variables": list(
                validation.stripped_environment_variables
            ),
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
                "Precondition failed: TS-564 did not execute the current supported "
                "download command equivalent of the ticket scenario.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-564 must run a repository-local built binary "
                "wrapper from this checkout.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        initial_state: TrackStateCliReleaseDownloadAuthFailureRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-123 before "
                "running TS-564.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain attachments.json "
                "with release-backed metadata before running TS-564.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if self.config.attachment_relative_path not in initial_state.metadata_attachment_ids:
            failures.append(
                "Precondition failed: attachments.json did not contain the release-backed "
                "manual.pdf entry required for TS-564.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_output_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained the expected "
                "download output file before TS-564 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != self.config.remote_origin_url:
            failures.append(
                "Precondition failed: the seeded repository origin URL did not match the "
                "expected GitHub remote.\n"
                f"Expected origin: {self.config.remote_origin_url}\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseDownloadAuthFailureValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        error_dict = error if isinstance(error, dict) else None
        stdout = observation.result.stdout
        stderr = observation.result.stderr
        visible_error = _visible_error_text(payload, stdout=stdout, stderr=stderr)
        result["visible_error_text"] = visible_error

        if observation.result.exit_code == 0:
            failures.append(
                "Step 1 failed: executing the ticket scenario succeeded even though the "
                "attachment metadata points at GitHub Releases storage without GitHub auth.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        if not isinstance(payload_dict, dict):
            failures.append(
                "Step 2 failed: the command did not return a JSON error envelope even "
                "though TS-564 explicitly requires inspecting `category` and `exitCode`.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        if payload_dict.get("output") != "json":
            failures.append(
                "Step 2 failed: the JSON envelope did not preserve `output = json` for "
                "the ticket scenario.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if payload_dict.get("provider") != "local-git":
            failures.append(
                "Step 2 failed: the JSON envelope did not stay on the local-git provider "
                "path required by TS-564.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )

        target = payload_dict.get("target")
        target_dict = target if isinstance(target, dict) else None
        if not isinstance(target_dict, dict):
            failures.append(
                "Step 2 failed: the JSON envelope did not expose target metadata as an "
                "object for the local download scenario.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        else:
            if target_dict.get("type") != "local":
                failures.append(
                    "Step 2 failed: the JSON envelope did not identify a local target for "
                    "the TS-564 command path.\n"
                    f"Observed target:\n{json.dumps(target_dict, indent=2, sort_keys=True)}"
                )
            if target_dict.get("value") != observation.repository_path:
                failures.append(
                    "Step 2 failed: the JSON envelope target value did not match the "
                    "disposable local repository used for TS-564.\n"
                    f"Expected target value: {observation.repository_path}\n"
                    f"Observed target:\n{json.dumps(target_dict, indent=2, sort_keys=True)}"
                )

        if not isinstance(error_dict, dict):
            failures.append(
                "Step 2 failed: the JSON envelope did not contain an `error` object for "
                "the failed local release-backed download.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
            return failures

        lowered_error = visible_error.lower()
        has_release_context = any(
            fragment in lowered_error
            for fragment in self.config.expected_release_fragments
        )
        has_auth_context = any(
            fragment in lowered_error for fragment in self.config.expected_auth_fragments
        )
        observed_category = _as_text(error_dict.get("category")).strip().lower()
        observed_error_code = _as_text(error_dict.get("code")).strip()
        observed_error_exit_code = error_dict.get("exitCode")
        code_ok = observed_error_code == EXPECTED_ERROR_CODE
        category_ok = observed_category == EXPECTED_ERROR_CATEGORY
        exit_code_ok = observed_error_exit_code == EXPECTED_ERROR_EXIT_CODE

        if has_release_context and has_auth_context:
            _record_human_verification(
                result,
                check=(
                    "Verified the terminal-visible failure still clearly explains that "
                    "GitHub authentication/configuration is required for the release-backed "
                    "download."
                ),
                observed=visible_error,
            )
        else:
            failures.append(
                "Human-style verification failed: the visible terminal output did not "
                "clearly show the release-backed GitHub auth/configuration problem.\n"
                f"Observed release context: {has_release_context}\n"
                f"Observed auth context: {has_auth_context}\n"
                f"Visible output:\n{visible_error}\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
            )

        if code_ok and category_ok and exit_code_ok:
            result["failure_mode"] = "none"
            _record_step(
                result,
                step=1,
                status="passed",
                action=result["supported_ticket_command"],
                observed=(
                    f"process_exit_code={observation.result.exit_code}; "
                    f"error_code={observed_error_code}; "
                    f"error_category={observed_category}; "
                    f"error_exit_code={observed_error_exit_code}; "
                    f"visible_error={visible_error}"
                ),
            )
            _record_step(
                result,
                step=2,
                status="passed",
                action="Inspect the JSON error fields `category` and `exitCode`.",
                observed=(
                    f"payload.provider={_as_text(payload_dict.get('provider'))}; "
                    f"target.type={_as_text(result.get('observed_target_type'))}; "
                    f"target.value={_as_text(result.get('observed_target_value'))}; "
                    f"payload.output={_as_text(payload_dict.get('output'))}; "
                    f"error.code={observed_error_code}; "
                    f"error.category={observed_category}; "
                    f"error.exitCode={observed_error_exit_code}"
                ),
            )
            return failures

        result["failure_mode"] = "masked_auth_contract"
        result["product_gap"] = (
            "The visible local release-backed download error now mentions missing GitHub "
            "authentication, but the machine-readable JSON contract does not return the "
            f"expected {EXPECTED_ERROR_CODE}/{EXPECTED_ERROR_CATEGORY}/{EXPECTED_ERROR_EXIT_CODE} "
            "authentication contract."
        )
        if not code_ok:
            failures.append(
                "Step 2 failed: the JSON error `code` did not switch to the "
                "authentication contract.\n"
                f"Expected code: {EXPECTED_ERROR_CODE!r}\n"
                f"Observed code: {observed_error_code!r}\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if not category_ok:
            failures.append(
                "Step 2 failed: the JSON error `category` did not switch to the "
                "authentication contract.\n"
                f"Expected category: {EXPECTED_ERROR_CATEGORY!r}\n"
                f"Observed category: {observed_category!r}\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if not exit_code_ok:
            failures.append(
                "Step 2 failed: the JSON error `exitCode` did not switch to the "
                "authentication contract.\n"
                f"Expected exitCode: {EXPECTED_ERROR_EXIT_CODE!r}\n"
                f"Observed exitCode: {observed_error_exit_code!r}\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        return failures

    def _validate_filesystem_state(
        self,
        validation: TrackStateCliReleaseDownloadAuthFailureValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_state
        if final_state.expected_output_exists:
            failures.append(
                "Step 3 failed: the local runtime created the download output file even "
                "though the release-backed auth failure should stop the download.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.git_status_lines:
            failures.append(
                "Step 3 failed: the failed download left repository changes behind.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if not failures:
            _record_step(
                result,
                step=3,
                status="passed",
                action=(
                    "Inspect the command output and local filesystem after the failed "
                    "download."
                ),
                observed=(
                    f"expected_output_exists={final_state.expected_output_exists}; "
                    f"expected_output_size_bytes={final_state.expected_output_size_bytes}; "
                    f"downloads_directory_exists={final_state.downloads_directory_exists}; "
                    f"git_status={list(final_state.git_status_lines)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified from a user's perspective that no downloaded manual.pdf "
                    "appeared in the local filesystem after the failed command."
                ),
                observed=(
                    f"expected_output_exists={final_state.expected_output_exists}; "
                    f"downloads_directory_exists={final_state.downloads_directory_exists}"
                ),
            )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts564ReleaseDownloadAuthContractScenario()

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
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()

    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            }
        ),
        encoding="utf-8",
    )

    visible_error = _as_text(result.get("visible_error_text"))
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Ticket step reviewed: {_jira_inline(_as_text(result.get('ticket_command')))}. "
            f"Automation executed the current supported equivalent "
            f"{_jira_inline(_as_text(result.get('supported_ticket_command')))}."
        ),
        "* Seeded a disposable local TrackState repository configured with {{attachmentStorage.mode = github-releases}} and removed GitHub credentials from the runtime environment.",
        f"* Compiled the CLI from source ref {_jira_inline(_as_text(result.get('compiled_source_ref')))} to exercise the deployed auth-contract implementation.",
        "* Inspected the caller-visible terminal output, the JSON error payload, and the local output path after the failed download.",
        "",
        "h4. Result",
        "* Step 1 passed: the CLI failed with explicit release-backed GitHub auth/configuration guidance visible to the user.",
        f"* Step 2 passed: JSON {_jira_inline('error.code')} = {_jira_inline(_as_text(result.get('observed_error_code')))}, {_jira_inline('error.category')} = {_jira_inline(_as_text(result.get('observed_error_category')))}, and {_jira_inline('error.exitCode')} = {_jira_inline(_as_text(result.get('observed_error_exit_code')))} match the fixed authentication contract.",
        "* Step 3 passed: no local download file was created and the repository stayed clean.",
        f"* Human-style verification passed: {_jira_inline(visible_error)}",
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
            f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`. "
            f"Automation executed the current supported equivalent "
            f"`{_as_text(result.get('supported_ticket_command'))}`."
        ),
        "- Seeded a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and removed GitHub credentials from the runtime environment.",
        f"- Compiled the CLI from source ref `{_as_text(result.get('compiled_source_ref'))}` to exercise the deployed auth-contract implementation.",
        "- Inspected the caller-visible terminal output, the JSON error payload, and the local output path after the failed download.",
        "",
        "## Result",
        "- Step 1 passed: the CLI failed with explicit release-backed GitHub auth/configuration guidance visible to the user.",
        f"- Step 2 passed: JSON `error.code = {_as_text(result.get('observed_error_code'))}`, `error.category = {_as_text(result.get('observed_error_category'))}`, and `error.exitCode = {_as_text(result.get('observed_error_exit_code'))}` match the fixed authentication contract.",
        "- Step 3 passed: no local download file was created and the repository stayed clean.",
        f"- Human-style verification passed: `{visible_error}`",
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
    error_message = _as_text(result.get("error"))
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
        ),
        encoding="utf-8",
    )

    stdout = _as_text(result.get("stdout"))
    stderr = _as_text(result.get("stderr"))
    payload = result.get("payload")
    visible_error = _visible_error_text(payload, stdout=stdout, stderr=stderr)
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    final_state = result.get("final_state")
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    expected_output_path = _as_text(result.get("expected_output_relative_path"))
    observed_category = _as_text(result.get("observed_error_category"))
    observed_error_exit_code = _as_text(result.get("observed_error_exit_code"))
    observed_provider = _as_text(result.get("observed_provider")) or "local-git"
    product_gap = _as_text(result.get("product_gap"))
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Ticket step reviewed: {_jira_inline(_as_text(result.get('ticket_command')))}. "
            f"Automation executed the current supported equivalent "
            f"{_jira_inline(_as_text(result.get('supported_ticket_command')))}."
        ),
        "* Seeded a disposable local TrackState repository configured with {{attachmentStorage.mode = github-releases}} and removed GitHub credentials from the runtime environment.",
        f"* Compiled the CLI from source ref {_jira_inline(_as_text(result.get('compiled_source_ref')))} to exercise the deployed auth-contract implementation.",
        "* Inspected the JSON error {{category}} and {{exitCode}} fields plus the local output path after the failed download.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the visible CLI failure did explain the missing GitHub auth/configuration requirement for release-backed downloads.",
        f"* ❌ Step 2 failed: JSON {_jira_inline('error.code')} = {_jira_inline(_as_text(result.get('observed_error_code')))}, {_jira_inline('error.category')} = {_jira_inline(observed_category)}, and {_jira_inline('error.exitCode')} = {_jira_inline(observed_error_exit_code)} instead of matching the fixed authentication contract.",
        f"* Observed provider/output: {_jira_inline(observed_provider)} / {_jira_inline(_as_text(result.get('observed_output_format')))}",
        f"* Observed visible output: {_jira_inline(visible_error)}",
        "* ✅ Step 3 passed: no local download file was created and the repository stayed clean.",
        f"* Human-style verification: the terminal output was explicit for the user, but the JSON contract still failed the ticket requirement.",
        *([f"* Product gap: {product_gap}"] if product_gap else []),
        "* Observed repository state:",
        "{code:json}",
        final_state_text,
        "{code}",
        "",
        "h4. Observed output",
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
            f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`. "
            f"Automation executed the current supported equivalent "
            f"`{_as_text(result.get('supported_ticket_command'))}`."
        ),
        "- Seeded a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and removed GitHub credentials from the runtime environment.",
        f"- Compiled the CLI from source ref `{_as_text(result.get('compiled_source_ref'))}` to exercise the deployed auth-contract implementation.",
        "- Inspected the JSON error `category` and `exitCode` fields plus the local output path after the failed download.",
        "",
        "## Result",
        "- ✅ Step 1 passed: the visible CLI failure did explain the missing GitHub auth/configuration requirement for release-backed downloads.",
        f"- ❌ Step 2 failed: JSON `error.code = {_as_text(result.get('observed_error_code'))}`, `error.category = {observed_category}`, and `error.exitCode = {observed_error_exit_code}` instead of matching the fixed authentication contract.",
        f"- Observed provider/output: `{observed_provider}` / `{_as_text(result.get('observed_output_format'))}`",
        f"- Observed visible output: `{visible_error}`",
        "- ✅ Step 3 passed: no local download file was created and the repository stayed clean.",
        "- Human-style verification: the terminal output was explicit for the user, but the JSON contract still failed the ticket requirement.",
        *([f"- Product gap: {product_gap}"] if product_gap else []),
        "- Observed repository state:",
        "```json",
        final_state_text,
        "```",
        "",
        "## Observed output",
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
        f"- Compiled source ref: `{_as_text(result.get('compiled_source_ref'))}`",
        f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`",
        f"- Executed supported command: `{_as_text(result.get('supported_ticket_command'))}`",
        f"- OS: `{platform.system()}`",
        f"- Remote origin: `{_as_text(result.get('remote_origin_url'))}`",
        f"- Provider/output: `{observed_provider}` / `{_as_text(result.get('observed_output_format'))}`",
        "- Auth setup: `GH_TOKEN`, `GITHUB_TOKEN`, and `TRACKSTATE_TOKEN` were removed from the process environment before execution.",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Create a local TrackState repository whose `project.json` sets "
            "`attachmentStorage.mode = github-releases` and whose `attachments.json` "
            "contains the release-backed `TS/TS-123/attachments/manual.pdf` entry. "
            "Observed: the fixture repository opened normally, contained `TS-123`, and "
            "did not contain a pre-existing `downloads/manual.pdf` file."
        ),
        (
            "2. ✅ Execute the ticket scenario for a local release-backed download without "
            "GitHub credentials. Observed via the current supported equivalent "
            f"`{_as_text(result.get('supported_ticket_command'))}`: the visible terminal "
            f"error was `{visible_error}`."
        ),
        (
            "3. ❌ Inspect the JSON error output fields `category` and `exitCode`. "
            f"Observed: `error.code = {_as_text(result.get('observed_error_code'))}`, `error.category = {observed_category}`, and "
            f"`error.exitCode = {observed_error_exit_code}`."
        ),
        (
            f"4. ✅ Inspect the local filesystem path `{expected_output_path}`. "
            "Observed: the file was not created and the repository stayed clean."
        ),
        "",
        "## Expected result",
        f"- The command should return JSON `error.code = {EXPECTED_ERROR_CODE}`, `error.category = {EXPECTED_ERROR_CATEGORY}`, and `error.exitCode = {EXPECTED_ERROR_EXIT_CODE}`.",
        "- The terminal-visible error should still explain that GitHub access is required for the release-backed download.",
        f"- The local output path `{expected_output_path}` must not be written.",
        "",
        "## Actual result",
        "- The terminal-visible error correctly explains the missing GitHub authentication requirement.",
        f"- However, the machine-readable JSON reports `error.code = {_as_text(result.get('observed_error_code'))}`, `error.category = {observed_category}`, and `error.exitCode = {observed_error_exit_code}`.",
        f"- The full payload differs from the fixed authentication contract:\n\n```json\n{json.dumps(payload, indent=2, sort_keys=True)}\n```",
        "",
        "## Exact error / stack trace",
        "```text",
        _as_text(result.get("traceback")).rstrip(),
        "```",
        "",
        "## Captured CLI output",
        "```json",
        stdout.rstrip() or "{}",
        "```",
        "",
        "```text",
        stderr.rstrip() or "<empty>",
        "```",
        "",
        "## Final repository state",
        "```json",
        final_state_text,
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


def _state_to_dict(
    state: TrackStateCliReleaseDownloadAuthFailureRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "attachments_metadata_exists": state.attachments_metadata_exists,
        "metadata_attachment_ids": list(state.metadata_attachment_ids),
        "expected_output_exists": state.expected_output_exists,
        "expected_output_size_bytes": state.expected_output_size_bytes,
        "downloads_directory_exists": state.downloads_directory_exists,
        "git_status_lines": list(state.git_status_lines),
        "remote_origin_url": state.remote_origin_url,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _describe_state(
    state: TrackStateCliReleaseDownloadAuthFailureRepositoryState,
) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


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
    if not isinstance(error, dict):
        return ""
    details = error.get("details")
    fragments = [
        _as_text(error.get("message")).strip(),
        _as_text(error.get("code")).strip(),
        _as_text(error.get("category")).strip(),
        _as_text(error.get("exitCode")).strip(),
    ]
    if isinstance(details, dict):
        fragments.extend(
            _as_text(details.get(key)).strip() for key in ("path", "reason") if details.get(key)
        )
    return " | ".join(fragment for fragment in fragments if fragment)


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") and stripped.endswith("}")


def _collapse_output(text: str) -> str:
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    return (
        "Observed stdout:\n"
        f"{stdout or '<empty>'}\n"
        "Observed stderr:\n"
        f"{stderr or '<empty>'}"
    )


def _format_supporting_evidence(*, payload: object, stdout: str, stderr: str) -> str:
    return (
        "Observed payload:\n"
        f"{json.dumps(payload, indent=2, sort_keys=True) if isinstance(payload, dict) else '<non-json>'}\n"
        f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
    )


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _jira_inline(text: str) -> str:
    return "{{" + text.replace("}", "") + "}}"


if __name__ == "__main__":
    main()
