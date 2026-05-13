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

TICKET_KEY = "TS-522"
TICKET_SUMMARY = (
    "Local runtime download with missing auth — explicit failure for "
    "release-backed attachments"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-522/test_ts_522.py"
RUN_COMMAND = "python testing/tests/TS-522/test_ts_522.py"


class Ts522ReleaseDownloadAuthFailureScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-522/config.yaml"
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
        failures.extend(self._assert_initial_fixture(validation.initial_state))
        failures.extend(self._validate_runtime(validation, result))
        failures.extend(self._validate_filesystem_state(validation, result))
        return result, failures

    def _build_base_result(self) -> dict[str, object]:
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "ticket_command": self.config.ticket_command,
            "requested_command": " ".join(self.config.requested_command),
            "config_path": str(self.config_path),
            "os": platform.system(),
            "project_key": self.config.project_key,
            "issue_key": self.config.issue_key,
            "attachment_relative_path": self.config.attachment_relative_path,
            "expected_output_relative_path": self.config.expected_output_relative_path,
            "remote_origin_url": self.config.remote_origin_url,
            "steps": [],
            "human_verification": [],
        }

    def _build_result(
        self,
        validation: TrackStateCliReleaseDownloadAuthFailureValidationResult,
    ) -> dict[str, object]:
        result = self._build_base_result()
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        error_dict = error if isinstance(error, dict) else None
        result.update(
            {
                "requested_command": validation.observation.requested_command_text,
                "executed_command": validation.observation.executed_command_text,
                "compiled_binary_path": validation.observation.compiled_binary_path,
                "repository_path": validation.observation.repository_path,
                "stdout": validation.observation.result.stdout,
                "stderr": validation.observation.result.stderr,
                "exit_code": validation.observation.result.exit_code,
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
                "observed_output_format": payload_dict.get("output")
                if isinstance(payload_dict, dict)
                else None,
                "observed_error_message": error_dict.get("message")
                if isinstance(error_dict, dict)
                else None,
                "observed_error_details": error_dict.get("details")
                if isinstance(error_dict, dict)
                else None,
                "initial_state": _state_to_dict(validation.initial_state),
                "final_state": _state_to_dict(validation.final_state),
                "stripped_environment_variables": list(
                    validation.stripped_environment_variables
                ),
            }
        )
        return result

    def _assert_exact_command(
        self,
        observation: TrackStateCliCommandObservation,
    ) -> list[str]:
        failures: list[str] = []
        if observation.requested_command != self.config.requested_command:
            failures.append(
                "Precondition failed: TS-522 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-522 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
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
                "running TS-522.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain attachments.json "
                "with release-backed metadata before running TS-522.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if self.config.attachment_relative_path not in initial_state.metadata_attachment_ids:
            failures.append(
                "Precondition failed: attachments.json did not contain the release-backed "
                "manual.pdf entry required for TS-522.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_output_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained the expected "
                "download output file before TS-522 ran.\n"
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
        error = payload.get("error") if isinstance(payload, dict) else None
        stdout = observation.result.stdout
        stderr = observation.result.stderr
        visible_error = _visible_error_text(payload, stdout=stdout, stderr=stderr)
        result["visible_error_text"] = visible_error

        if observation.result.exit_code == 0:
            failures.append(
                "Step 1 failed: executing the ticket command succeeded even though the "
                "attachment metadata points at GitHub Releases storage without GitHub auth.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        if not visible_error:
            failures.append(
                "Step 1 failed: the CLI failed, but it did not surface any caller-visible "
                "error text on stdout or stderr.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
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
        has_provider_capability_context = any(
            fragment in lowered_error
            for fragment in self.config.provider_capability_fragments
        )

        if has_release_context and has_auth_context:
            result["failure_mode"] = "none"
            error_code = error.get("code") if isinstance(error, dict) else ""
            error_category = error.get("category") if isinstance(error, dict) else ""
            _record_step(
                result,
                step=1,
                status="passed",
                action=self.config.ticket_command,
                observed=(
                    f"exit_code={observation.result.exit_code}; "
                    f"error_code={error_code}; "
                    f"error_category={error_category}; "
                    f"visible_error={visible_error}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the exact terminal output shown to a user failed immediately "
                    "with release-backed auth/configuration guidance instead of a generic "
                    "provider capability error."
                ),
                observed=visible_error,
            )
            return failures

        if has_provider_capability_context:
            observed_provider = _as_text(result.get("observed_provider")) or "local provider"
            result["failure_mode"] = "local_provider_capability_gate"
            result["product_gap"] = (
                "The local attachment-download path still fails through the provider-level "
                "GitHub Releases download capability gate before surfacing missing-auth "
                "guidance for release-backed attachments."
            )
            failures.append(
                "Step 1 failed: the local release-backed download path did not reach the "
                "missing-auth contract.\n"
                f"It failed earlier through the `{observed_provider}` provider with "
                "the generic capability message about unsupported GitHub Releases "
                "attachment downloads.\n"
                f"Visible output:\n{visible_error}\n"
                "This means the command still cannot surface the explicit GitHub "
                "auth/configuration guidance required by TS-522.\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
            )
            return failures

        result["failure_mode"] = "missing_release_auth_guidance"
        if not has_release_context:
            failures.append(
                "Step 1 failed: the visible CLI error was not an explicit release-backed "
                "auth/configuration failure.\n"
                "The output did not mention GitHub Releases or release-backed storage.\n"
                f"Visible output:\n{visible_error}\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
            )
        if not has_auth_context:
            failures.append(
                "Step 1 failed: the visible CLI error did not explain that GitHub "
                "authentication or release-download configuration is required.\n"
                f"Visible output:\n{visible_error}\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
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
                "Step 2 failed: the local runtime created the download output file even "
                "though release-backed auth/configuration was missing.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.git_status_lines:
            failures.append(
                "Step 2 failed: the failed download left repository changes behind.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )

        if not failures:
            _record_step(
                result,
                step=2,
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
    scenario = Ts522ReleaseDownloadAuthFailureScenario()
    base_result = scenario._build_base_result()

    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", base_result)
        if not isinstance(failure_result, dict):
            failure_result = dict(base_result)
        if not failure_result.get("final_state"):
            failure_result.setdefault("failure_mode", "runtime_setup_failure")
            failure_result.setdefault("observed_error_code", "TEST_RUNTIME_FAILED")
            failure_result.setdefault("observed_error_category", "runtime")
            failure_result.setdefault("observed_provider", "test-runtime")
            failure_result.setdefault("observed_output_format", "runtime")
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

    summary = "1 passed, 0 failed"
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": summary,
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
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository whose {_jira_inline('attachments.json')} points {_jira_inline('manual.pdf')} at {_jira_inline('storageBackend = github-releases')}.",
        "* Removed GitHub credentials from the runtime environment and inspected the caller-visible CLI error output.",
        f"* Inspected the local output path {_jira_inline(_as_text(result.get('expected_output_relative_path')))} after the command.",
        "",
        "h4. Result",
        "* Step 1 passed: the CLI failed immediately with explicit release-backed auth/configuration guidance.",
        f"* Observed error: {_jira_inline(visible_error)}",
        "* Step 2 passed: no local download file was created and the repository stayed clean.",
        "* Human-style verification passed: the terminal output clearly explained the auth/configuration problem, and no manual.pdf file appeared in the local filesystem.",
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
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository whose `attachments.json` points `manual.pdf` at `storageBackend = github-releases`.",
        "- Removed GitHub credentials from the runtime environment and inspected the caller-visible CLI error output.",
        f"- Inspected `{_as_text(result.get('expected_output_relative_path'))}` after the command.",
        "",
        "## Result",
        "- Step 1 passed: the CLI failed immediately with explicit release-backed auth/configuration guidance.",
        f"- Observed error: `{visible_error}`",
        "- Step 2 passed: no local download file was created and the repository stayed clean.",
        "- Human-style verification passed: the terminal output clearly explained the auth/configuration problem, and no `manual.pdf` file appeared in the local filesystem.",
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
    visible_error = _visible_error_text(result.get("payload"), stdout=stdout, stderr=stderr)
    if not visible_error:
        visible_error = error_message
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    if observed_output == "<empty>":
        observed_output = error_message or _as_text(result.get("traceback"))
    final_state = result.get("final_state")
    final_state_dict = final_state if isinstance(final_state, dict) else {}
    final_state_text = json.dumps(final_state_dict, indent=2, sort_keys=True)
    expected_output_path = _as_text(result.get("expected_output_relative_path"))
    failure_mode = _as_text(result.get("failure_mode"))
    product_gap = _as_text(result.get("product_gap"))
    default_provider = "test-runtime" if failure_mode == "runtime_setup_failure" else "local-git"
    observed_provider = _as_text(result.get("observed_provider")) or default_provider
    observed_reason = _error_reason(result) or visible_error or error_message
    what_was_tested_line = (
        f"* Attempted to execute {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured with {_jira_inline('attachmentStorage.mode = github-releases')} and no GitHub token in CLI args or environment."
        if failure_mode == "runtime_setup_failure"
        else f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured with {_jira_inline('attachmentStorage.mode = github-releases')} and no GitHub token in CLI args or environment."
    )
    markdown_tested_line = (
        f"- Attempted to execute `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and no GitHub token in CLI args or environment."
        if failure_mode == "runtime_setup_failure"
        else f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and no GitHub token in CLI args or environment."
    )

    if failure_mode == "runtime_setup_failure":
        step_one_summary = (
            "the test runtime failed before the attachment-download command could be "
            "observed on the checked-out revision"
        )
        human_summary = (
            "Human-style verification could not reach the TS-522 command boundary "
            "because the test runtime failed before any caller-visible "
            "attachment-download result was produced."
        )
        actual_result_line = (
            "* The checked-out TrackState CLI could not be executed far enough to "
            "validate the release-backed missing-auth boundary; the failure stayed "
            f"at test/runtime level with {_jira_inline(observed_reason)}."
        )
        step_two_line = (
            "* ⚪ Step 2 was not reached because the attachment download command "
            "never completed."
        )
    elif failure_mode == "local_provider_capability_gate":
        step_one_summary = (
            "the local release-backed download path failed earlier at the provider "
            "capability gate, so the command never reached missing-auth handling"
        )
        human_summary = (
            "Human-style verification observed a real terminal failure and no local "
            "downloaded file, but the failure was the generic provider capability "
            "error rather than explicit GitHub auth/configuration guidance."
        )
        actual_result_line = (
            "* However, the command failed earlier through the generic "
            f"{_jira_inline(observed_provider)} provider path with message "
            f"{_jira_inline(observed_reason)}. "
            "That means the local runtime path never reached GitHub "
            "auth/configuration handling for the release-backed attachment."
        )
        step_two_line = "* ✅ Step 2 passed: no local download file was created."
    else:
        step_one_summary = (
            "the command failed, but the visible output was generic and did not "
            "explicitly mention missing GitHub auth/configuration for GitHub Releases storage"
        )
        human_summary = (
            "Human-style verification observed a terminal error and no local "
            "downloaded file, but the visible error text did not match the expected "
            "explicit release-auth/configuration guidance."
        )
        actual_result_line = (
            "* However, the command only returned a generic repository failure "
            f"({_jira_inline(_as_text(result.get('observed_error_code')))} / "
            f"{_jira_inline(_as_text(result.get('observed_error_category')))}) with message "
            f"{_jira_inline(observed_reason)} instead of explicit "
            "release-auth/configuration guidance."
        )
        step_two_line = "* ✅ Step 2 passed: no local download file was created."

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        what_was_tested_line,
        "* Inspected the caller-visible CLI output and the local output path after the command.",
        "",
        "h4. Result",
        f"* ❌ Step 1 failed: {step_one_summary}.",
        f"* Observed error code/category: {_jira_inline(_as_text(result.get('observed_error_code')))} / {_jira_inline(_as_text(result.get('observed_error_category')))}",
        f"* Observed provider/output: {_jira_inline(observed_provider)} / {_jira_inline(_as_text(result.get('observed_output_format')))}",
        f"* Observed visible output: {_jira_inline(visible_error)}",
        step_two_line,
        f"* {human_summary}",
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
        markdown_tested_line,
        "- Inspected the caller-visible CLI output and the local output path after the command.",
        "",
        "## Result",
        f"- ❌ Step 1 failed: {step_one_summary}.",
        f"- Observed error code/category: `{_as_text(result.get('observed_error_code'))}` / `{_as_text(result.get('observed_error_category'))}`",
        f"- Observed provider/output: `{observed_provider}` / `{_as_text(result.get('observed_output_format'))}`",
        f"- Observed visible output: `{visible_error}`",
        (
            "- ⚪ Step 2 was not reached because the attachment download command "
            "never completed."
            if failure_mode == "runtime_setup_failure"
            else "- ✅ Step 2 passed: no local download file was created."
        ),
        f"- {human_summary}",
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
    if failure_mode == "runtime_setup_failure":
        bug_steps = [
            "h4. Steps to Reproduce",
            (
                f"# ⚪ Prepare a disposable local TrackState repository whose {_jira_inline('project.json')} sets "
                f"{_jira_inline('attachmentStorage.mode = github-releases')} and whose "
                f"{_jira_inline('attachments.json')} contains the release-backed entry "
                f"{_jira_inline(_as_text(result.get('attachment_relative_path')))}."
            ),
            (
                f"# ❌ Execute CLI command: {_jira_inline(_as_text(result.get('ticket_command')))}. "
                "Observed: the checked-out CLI/runtime failed before the attachment-download "
                f"boundary could be observed: {_jira_inline(observed_reason)}"
            ),
            (
                f"# ⚪ Inspect the command output and local filesystem path "
                f"{_jira_inline(expected_output_path)}. Observed: not reached because the "
                "test/runtime failure prevented the command from completing."
            ),
        ]
        actual_result_prefix = [
            "* The command boundary was not exercised, so no filesystem assertion could be completed."
        ]
    else:
        bug_steps = [
            "h4. Steps to Reproduce",
            (
                f"# ✅ Create a local TrackState repository whose {_jira_inline('project.json')} sets "
                f"{_jira_inline('attachmentStorage.mode = github-releases')} and whose "
                f"{_jira_inline('attachments.json')} contains the release-backed entry "
                f"{_jira_inline(_as_text(result.get('attachment_relative_path')))}. "
                "Observed: the fixture repository opened normally and contained TS-123 with a release-backed manual.pdf attachment entry and no local download output file."
            ),
            (
                f"# ❌ Execute CLI command: {_jira_inline(_as_text(result.get('ticket_command')))}. "
                f"Observed: exit code {_as_text(result.get('exit_code'))}; visible output = "
                f"{visible_error}"
            ),
            (
                f"# ✅ Inspect the command output and local filesystem path "
                f"{_jira_inline(expected_output_path)}. Observed: the file was not created, "
                "stdout showed the repository error envelope below, and the repository stayed clean."
            ),
        ]
        actual_result_prefix = [
            "* The file was not written locally, so no download artifact was created."
        ]
    bug_lines = [
        "h4. Environment",
        f"* Repository path: {_jira_inline(_as_text(result.get('repository_path')))}",
        f"* Command: {_jira_inline(_as_text(result.get('ticket_command')))}",
        f"* OS: {platform.system()}",
        f"* Remote origin: {_jira_inline(_as_text(result.get('remote_origin_url')))}",
        "* Auth setup: GH_TOKEN, GITHUB_TOKEN, and TRACKSTATE_TOKEN were removed from the process environment before execution.",
        "",
        *bug_steps,
        "",
        "h4. Expected Result",
        "* The command should fail with an explicit release-auth/configuration error that tells the user GitHub access is required for a release-backed attachment download.",
        f"* The file must not be written to the local output path {_jira_inline(expected_output_path)}.",
        "* Silent fallback to local attachment storage must not occur.",
        "",
        "h4. Actual Result",
        *actual_result_prefix,
        actual_result_line,
        "",
        "h4. Logs / Error Output",
        "{code}",
        _as_text(result.get("traceback")).rstrip(),
        "{code}",
        "",
        "h4. Notes",
        *([f"* Missing/broken production capability: {product_gap}"] if product_gap else []),
        "* Full stdout:",
        "{code:json}",
        stdout.rstrip() or "{}",
        "{code}",
        "* stderr:",
        "{code}",
        stderr.rstrip() or "<empty>",
        "{code}",
        "* Final repository state:",
        "{code:json}",
        final_state_text,
        "{code}",
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
    ]
    if isinstance(details, dict):
        fragments.extend(
            _as_text(details.get(key)).strip()
            for key in ("reason", "provider", "target", "path", "file", "repository")
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


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _error_reason(result: dict[str, object]) -> str:
    details = result.get("observed_error_details")
    if isinstance(details, dict):
        reason = details.get("reason")
        if isinstance(reason, str) and reason:
            return reason
    return ""


def _jira_inline(value: str) -> str:
    return "{{" + value + "}}"


if __name__ == "__main__":
    main()
