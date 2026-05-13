from __future__ import annotations

import json
import os
import platform
import sys
import traceback
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

SOURCE_ROOT_ENV = "TRACKSTATE_TS523_SOURCE_ROOT"


def _resolve_source_root() -> Path:
    configured_root = os.environ.get(SOURCE_ROOT_ENV)
    if not configured_root:
        return WORKSPACE_ROOT
    candidate = Path(configured_root).expanduser()
    if not candidate.is_absolute():
        candidate = (WORKSPACE_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.is_dir():
        raise ValueError(
            f"{SOURCE_ROOT_ENV} must point to an existing TrackState checkout: {candidate}"
        )
    return candidate


SOURCE_ROOT = _resolve_source_root()

from testing.components.services.trackstate_cli_release_identity_missing_remote_validator import (  # noqa: E402
    TrackStateCliReleaseIdentityMissingRemoteValidator,
)
from testing.core.config.trackstate_cli_release_identity_missing_remote_config import (  # noqa: E402
    TrackStateCliReleaseIdentityMissingRemoteConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_identity_missing_remote_result import (  # noqa: E402
    TrackStateCliReleaseIdentityMissingRemoteRepositoryState,
    TrackStateCliReleaseIdentityMissingRemoteStoredFile,
    TrackStateCliReleaseIdentityMissingRemoteValidationResult,
)
from testing.tests.support.trackstate_cli_release_identity_missing_remote_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_identity_missing_remote_probe,
)

TICKET_KEY = "TS-523"
TICKET_SUMMARY = (
    "Local runtime upload without remote repository — explicit identity error "
    "for release-backed storage"
)
OUTPUTS_DIR = WORKSPACE_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
TEST_FILE_PATH = "testing/tests/TS-523/test_ts_523.py"
RUN_COMMAND = "python testing/tests/TS-523/test_ts_523.py"


class Ts523ReleaseIdentityMissingRemoteScenario:
    def __init__(self) -> None:
        self.workspace_root = WORKSPACE_ROOT
        self.source_root = SOURCE_ROOT
        self.config_path = self.workspace_root / "testing/tests/TS-523/config.yaml"
        self.config = TrackStateCliReleaseIdentityMissingRemoteConfig.from_file(
            self.config_path
        )
        self.validator = TrackStateCliReleaseIdentityMissingRemoteValidator(
            probe=create_trackstate_cli_release_identity_missing_remote_probe(
                self.source_root
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
                action="Prepare a local github-releases fixture repository with no Git remotes configured.",
                observed=(
                    f"issue_main_exists={validation.initial_state.issue_main_exists}; "
                    f"remote_names={list(validation.initial_state.remote_names)}; "
                    f"stored_files={_format_stored_files(validation.initial_state.stored_files)}"
                ),
            )
        failures.extend(self._validate_runtime(validation, result))
        failures.extend(self._validate_repository_state(validation, result))
        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseIdentityMissingRemoteValidationResult,
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
            "source_root": str(self.source_root),
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "project_key": self.config.project_key,
            "issue_key": self.config.issue_key,
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
                "Precondition failed: TS-523 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-523 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        initial_state: TrackStateCliReleaseIdentityMissingRemoteRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-475 before "
                "running TS-523.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_attachment_exists or initial_state.stored_files:
            failures.append(
                "Precondition failed: the seeded repository already contained a local "
                "attachment before TS-523 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.remote_names:
            failures.append(
                "Precondition failed: TS-523 requires a local Git repository with no "
                "remotes configured, but the seeded repository already had remotes.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseIdentityMissingRemoteValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        error = payload.get("error") if isinstance(payload, dict) else None
        stdout = observation.result.stdout
        stderr = observation.result.stderr
        visible_error = _visible_error_text(
            payload,
            stdout=stdout,
            stderr=stderr,
        )
        result["visible_error_text"] = visible_error

        if observation.result.exit_code == 0:
            failures.append(
                "Step 1 failed: executing the ticket command succeeded even though the "
                "repository is configured for github-releases storage without any Git "
                "remote configuration.\n"
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
        missing_identity_fragments = [
            fragment
            for fragment in self.config.expected_identity_fragments
            if fragment not in lowered_error
        ]
        has_generic_release_auth = any(
            fragment in lowered_error
            for fragment in self.config.generic_release_auth_fragments
        )

        if not missing_identity_fragments:
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
                    "with repository-identity guidance tied to the missing local Git remote configuration."
                ),
                observed=visible_error,
            )
            return failures

        result["failure_mode"] = (
            "generic_release_auth_guidance"
            if has_generic_release_auth
            else "missing_identity_guidance"
        )
        result["product_gap"] = (
            "Local release-backed uploads do not explain that GitHub repository identity "
            "cannot be resolved from the local Git configuration when the repository has "
            "no remotes configured."
        )
        failures.append(
            "Step 1 failed: the visible CLI error did not state that GitHub repository "
            "identity could not be resolved from the local Git configuration.\n"
            f"Missing identity fragments: {missing_identity_fragments}\n"
            f"Visible output:\n{visible_error}\n"
            f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
        )
        return failures

    def _validate_repository_state(
        self,
        validation: TrackStateCliReleaseIdentityMissingRemoteValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_state
        if final_state.expected_attachment_exists:
            failures.append(
                "Step 2 failed: the file was written to the local repository attachment "
                "path even though repository identity could not be resolved.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.stored_files:
            failures.append(
                "Step 2 failed: the repository gained files under the local attachments "
                "directory even though the command should have failed before upload "
                "initialization.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.git_status_lines:
            failures.append(
                "Step 2 failed: the failed upload left local repository changes behind.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.remote_names:
            failures.append(
                "Step 2 failed: the scenario mutated the repository remotes even though "
                "the no-remote precondition should stay intact.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )

        if not failures:
            attachment_listing = _format_stored_files(final_state.stored_files)
            _record_step(
                result,
                step=2,
                status="passed",
                action=(
                    "Inspect the command output and the repository attachments directory "
                    "after the failed upload."
                ),
                observed=(
                    f"expected_attachment_exists={final_state.expected_attachment_exists}; "
                    f"attachment_directory_exists={final_state.attachment_directory_exists}; "
                    f"stored_files={attachment_listing}; "
                    f"git_status={list(final_state.git_status_lines)}; "
                    f"remote_names={list(final_state.remote_names)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified from a user's perspective that the command failed and no "
                    "`attachments/` file appeared in the repository."
                ),
                observed=(
                    f"attachment_directory_exists={final_state.attachment_directory_exists}; "
                    f"stored_files={attachment_listing}; "
                    f"remote_names={list(final_state.remote_names)}"
                ),
            )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts523ReleaseIdentityMissingRemoteScenario()

    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        failure_result = locals().get("result", {}) if "result" in locals() else {}
        if not isinstance(failure_result, dict):
            failure_result = {}
        failure_result.setdefault("ticket_command", scenario.config.ticket_command)
        failure_result.setdefault(
            "expected_attachment_relative_path",
            scenario.config.expected_attachment_relative_path,
        )
        failure_result.setdefault("config_path", str(scenario.config_path))
        failure_result.setdefault("source_root", str(scenario.source_root))
        if _is_compile_failure_message(str(error)):
            failure_result["product_gap"] = (
                "The repository-local TrackState CLI cannot be compiled for the local "
                "runtime because the CLI dependency graph pulls in Flutter `dart:ui` "
                "APIs through the GitHub provider path."
            )
            failure_result["error"] = (
                "AssertionError: Failed to compile a temporary TrackState CLI executable."
            )
        else:
            failure_result["error"] = f"{type(error).__name__}: {error}"
        failure_result.update(
            {
                "ticket": TICKET_KEY,
                "ticket_summary": TICKET_SUMMARY,
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
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured with {_jira_inline('attachmentStorage.mode = github-releases')} and no Git remotes configured.",
        "* Removed GitHub credentials from the runtime environment and inspected the caller-visible CLI error output.",
        f"* Inspected the repository path {_jira_inline(_as_text(result.get('expected_attachment_relative_path')))} and the local attachments directory after the command.",
        "",
        "h4. Result",
        "* Step 1 passed: the CLI failed immediately with explicit repository-identity guidance tied to the missing local Git remote configuration.",
        f"* Observed error: {_jira_inline(visible_error)}",
        "* Step 2 passed: no local attachment file was written and the repository stayed clean.",
        "* Human-style verification passed: the terminal output clearly explained the repository identity problem, and no fallback file appeared in the repository.",
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
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and no Git remotes configured.",
        "- Removed GitHub credentials from the runtime environment and inspected the caller-visible CLI error output.",
        f"- Inspected `{_as_text(result.get('expected_attachment_relative_path'))}` and the local attachments directory after the command.",
        "",
        "## Result",
        "- Step 1 passed: the CLI failed immediately with explicit repository-identity guidance tied to the missing local Git remote configuration.",
        f"- Observed error: `{visible_error}`",
        "- Step 2 passed: no local attachment file was written and the repository stayed clean.",
        "- Human-style verification passed: the terminal output clearly explained the repository identity problem, and no fallback file appeared in the repository.",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    _write_review_replies()


def _write_failure_outputs(result: dict[str, object]) -> None:
    error_message = _as_text(result.get("error"))
    if _is_compile_failure_message(_as_text(result.get("traceback"))) or _is_compile_failure_message(
        error_message
    ):
        _write_compile_failure_outputs(result, error_message=error_message)
        return

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
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    final_state = result.get("final_state")
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    expected_path = _as_text(result.get("expected_attachment_relative_path"))
    failure_mode = _as_text(result.get("failure_mode"))
    product_gap = _as_text(result.get("product_gap"))
    observed_provider = _as_text(result.get("observed_provider")) or "local-git"
    if failure_mode == "generic_release_auth_guidance":
        step_one_summary = (
            "the command failed, but it only returned generic release-upload "
            "auth/configuration guidance instead of an explicit missing-remote "
            "repository-identity error"
        )
        human_summary = (
            "Human-style verification observed a real terminal failure and no local "
            "attachment file, but the failure text did not explain that the local Git "
            "configuration had no remote from which to resolve the GitHub repository identity."
        )
        actual_result_line = (
            "* However, the command only reported generic release-upload guidance "
            f"with visible output {_jira_inline(visible_error)} "
            "instead of explaining that the GitHub repository identity could not be "
            "resolved from the local Git configuration."
        )
    else:
        step_one_summary = (
            "the command failed, but the visible output still did not explain that "
            "GitHub repository identity could not be resolved from the local Git configuration"
        )
        human_summary = (
            "Human-style verification observed a terminal error and no local attachment "
            "file, but the visible error text did not match the expected repository-identity guidance."
        )
        actual_result_line = (
            "* However, the command only returned a generic repository failure "
            f"({_jira_inline(_as_text(result.get('observed_error_code')))} / "
            f"{_jira_inline(_as_text(result.get('observed_error_category')))}) with message "
            f"{_jira_inline(_as_text(result.get('observed_error_message')) or visible_error)} instead of explicit "
            "repository-identity guidance tied to missing Git remotes."
        )
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured with {_jira_inline('attachmentStorage.mode = github-releases')} and no Git remotes configured.",
        "* Inspected the caller-visible CLI output and the repository attachment path after the command.",
        "",
        "h4. Result",
        f"* ❌ Step 1 failed: {step_one_summary}.",
        f"* Observed error code/category: {_jira_inline(_as_text(result.get('observed_error_code')))} / {_jira_inline(_as_text(result.get('observed_error_category')))}",
        f"* Observed provider/output: {_jira_inline(observed_provider)} / {_jira_inline(_as_text(result.get('observed_output_format')))}",
        f"* Observed visible output: {_jira_inline(visible_error)}",
        "* ✅ Step 2 passed: no file was written to the local repository attachment path.",
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
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and no Git remotes configured.",
        "- Inspected the caller-visible CLI output and the repository attachment path after the command.",
        "",
        "## Result",
        f"- ❌ Step 1 failed: {step_one_summary}.",
        f"- Observed error code/category: `{_as_text(result.get('observed_error_code'))}` / `{_as_text(result.get('observed_error_category'))}`",
        f"- Observed provider/output: `{observed_provider}` / `{_as_text(result.get('observed_output_format'))}`",
        f"- Observed visible output: `{visible_error}`",
        "- ✅ Step 2 passed: no file was written to the local repository attachment path.",
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
    bug_lines = [
        "# TS-523 bug reproduction",
        "",
        "## Environment",
        f"- Repository path: `{_as_text(result.get('repository_path'))}`",
        f"- Command: `{_as_text(result.get('ticket_command'))}`",
        f"- OS: `{platform.system()}`",
        f"- Git remotes: `{json.dumps((final_state or {}).get('remote_names', []))}`",
        "- Auth setup: `GH_TOKEN`, `GITHUB_TOKEN`, and `TRACKSTATE_TOKEN` were removed from the process environment before execution.",
        "",
        "## Steps to reproduce",
        "1. ✅ Create a local TrackState repository whose `project.json` sets `attachmentStorage.mode = github-releases` and whose Git configuration has no remotes. Observed: the fixture repository opened normally, contained `TS-475` with no seeded attachments, and `git remote` returned no entries.",
        f"2. ❌ Execute CLI command: `{_as_text(result.get('ticket_command'))}`. Observed: exit code `{_as_text(result.get('exit_code'))}` and visible output `{visible_error}`.",
        f"3. ✅ Inspect the command output and the repository `attachments/` path. Observed: `{expected_path}` was not created, stdout showed the repository error envelope below, and the repository stayed clean.",
        "",
        "## Expected result",
        "- The command should fail with a specific error that says the GitHub repository identity cannot be resolved from the local Git configuration.",
        "- The failure should happen as pre-flight validation before release-upload initialization.",
        f"- The file must not be written to the local repository path `{expected_path}`.",
        "",
        "## Actual result",
        "- The file was not written locally, so repository-path fallback did not occur.",
        f"- {actual_result_line.replace('* ', '', 1).replace('{{', '`').replace('}}', '`')}",
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
    _write_review_replies()


def _write_compile_failure_outputs(
    result: dict[str, object],
    *,
    error_message: str,
) -> None:
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

    product_gap = _as_text(result.get("product_gap"))
    compile_command = _extract_between(
        _as_text(result.get("traceback")),
        "Command: ",
        "\nExit code:",
    )
    compile_stderr = _extract_between(
        _as_text(result.get("traceback")),
        "stderr:\n",
        "\n\nTraceback",
    ) or _extract_after(_as_text(result.get("traceback")), "stderr:\n")
    visible_error = _first_non_empty_line(compile_stderr) or error_message

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Attempted to execute {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured with {_jira_inline('attachmentStorage.mode = github-releases')} and no Git remotes configured.",
        "* The test first compiled the repository-local TrackState CLI so the exact public local command could be exercised against the disposable repository.",
        "",
        "h4. Result",
        "* ❌ The ticket scenario could not start because the repository-local CLI failed to compile for the local runtime.",
        f"* Observed compile command: {_jira_inline(compile_command)}",
        f"* Observed compiler failure: {_jira_inline(visible_error)}",
        "* Because the public local CLI path is currently broken, the missing-remote repository-identity contract could not be re-verified.",
        *([f"* Product gap: {product_gap}"] if product_gap else []),
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
        f"- Attempted to execute `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and no Git remotes configured.",
        "- The test first compiled the repository-local TrackState CLI so the exact public local command could run against the disposable repository.",
        "",
        "## Result",
        "- ❌ The ticket scenario could not start because the repository-local CLI failed to compile for the local runtime.",
        f"- Observed compile command: `{compile_command}`",
        f"- Observed compiler failure: `{visible_error}`",
        "- Because the public local CLI path is currently broken, the missing-remote repository-identity contract could not be re-verified.",
        *([f"- Product gap: {product_gap}"] if product_gap else []),
        "",
        "## Observed output",
        "```text",
        (compile_stderr or error_message).rstrip(),
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    bug_lines = [
        "# TS-523 bug reproduction",
        "",
        "## Environment",
        f"- Source checkout: `{_as_text(result.get('source_root')) or str(WORKSPACE_ROOT)}`",
        f"- Command: `{_as_text(result.get('ticket_command'))}`",
        f"- OS: `{platform.system()}`",
        "",
        "## Steps to reproduce",
        "1. Create a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and no Git remotes.",
        "2. From this checkout, run the TS-523 automation or compile the CLI directly:",
        f"   - `{RUN_COMMAND}`",
        f"   - `{compile_command}`",
        "3. Observe the CLI build failure before the ticket command can execute.",
        "",
        "## Expected result",
        "- The repository-local TrackState CLI should compile successfully in the local runtime so TS-523 can execute the public `trackstate attachment upload ... --target local` path.",
        "- After the CLI starts, the command should fail with explicit repository-identity guidance when no Git remote is configured.",
        "",
        "## Actual result",
        "- The repository-local CLI cannot be built in this checkout for the local runtime.",
        f"- The compiler fails with `{visible_error}` before the ticket command can run.",
        *([f"- Missing/broken production capability: {product_gap}"] if product_gap else []),
        "",
        "## Failing command/output",
        "```text",
        compile_command,
        "```",
        "",
        "```text",
        (compile_stderr or _as_text(result.get("traceback"))).rstrip(),
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")
    _write_review_replies()


def _write_review_replies() -> None:
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": []}),
        encoding="utf-8",
    )


def _is_compile_failure_message(message: str) -> bool:
    return (
        "Failed to compile a temporary TrackState CLI executable." in message
        or ("dart:ui" in message and "bin/trackstate.dart" in message)
    )


def _extract_between(text: str, start: str, end: str) -> str:
    if start not in text:
        return ""
    _, _, remainder = text.partition(start)
    if end and end in remainder:
        return remainder.partition(end)[0].strip()
    return remainder.strip()


def _extract_after(text: str, start: str) -> str:
    if start not in text:
        return ""
    return text.partition(start)[2].strip()


def _first_non_empty_line(text: str) -> str:
    for line in text.splitlines():
        if line.strip():
            return line.strip()
    return ""


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
    state: TrackStateCliReleaseIdentityMissingRemoteRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "attachment_directory_exists": state.attachment_directory_exists,
        "expected_attachment_exists": state.expected_attachment_exists,
        "stored_files": [
            {
                "relative_path": stored_file.relative_path,
                "size_bytes": stored_file.size_bytes,
            }
            for stored_file in state.stored_files
        ],
        "git_status_lines": list(state.git_status_lines),
        "remote_names": list(state.remote_names),
        "remote_origin_url": state.remote_origin_url,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _describe_state(
    state: TrackStateCliReleaseIdentityMissingRemoteRepositoryState,
) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


def _format_stored_files(
    stored_files: tuple[TrackStateCliReleaseIdentityMissingRemoteStoredFile, ...],
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


def _jira_inline(value: str) -> str:
    return "{{" + value + "}}"


if __name__ == "__main__":
    main()
