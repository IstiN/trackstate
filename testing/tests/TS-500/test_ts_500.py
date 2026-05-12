from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_auth_failure_validator import (  # noqa: E402
    TrackStateCliReleaseAuthFailureValidator,
)
from testing.core.config.trackstate_cli_release_auth_failure_config import (  # noqa: E402
    TrackStateCliReleaseAuthFailureConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_auth_failure_result import (  # noqa: E402
    TrackStateCliReleaseAuthFailureRepositoryState,
    TrackStateCliReleaseAuthFailureStoredFile,
    TrackStateCliReleaseAuthFailureValidationResult,
)
from testing.tests.support.trackstate_cli_release_auth_failure_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_auth_failure_probe,
)

TICKET_KEY = "TS-500"
TICKET_SUMMARY = (
    "Local runtime upload with missing auth — explicit failure without "
    "repository-path fallback"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-500/test_ts_500.py"
RUN_COMMAND = "python testing/tests/TS-500/test_ts_500.py"


class Ts500ReleaseAuthFailureScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-500/config.yaml"
        self.config = TrackStateCliReleaseAuthFailureConfig.from_file(self.config_path)
        self.validator = TrackStateCliReleaseAuthFailureValidator(
            probe=create_trackstate_cli_release_auth_failure_probe(self.repository_root)
        )

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
        validation: TrackStateCliReleaseAuthFailureValidationResult,
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
            "project_key": self.config.project_key,
            "issue_key": self.config.issue_key,
            "expected_attachment_relative_path": self.config.expected_attachment_relative_path,
            "remote_origin_url": self.config.remote_origin_url,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "error": error_dict,
            "observed_error_code": error_dict.get("code") if isinstance(error_dict, dict) else None,
            "observed_error_category": error_dict.get("category")
            if isinstance(error_dict, dict)
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
                "Precondition failed: TS-500 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-500 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        initial_state: TrackStateCliReleaseAuthFailureRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-475 before "
                "running TS-500.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_attachment_exists or initial_state.stored_files:
            failures.append(
                "Precondition failed: the seeded repository already contained a local "
                "attachment before TS-500 ran.\n"
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
        validation: TrackStateCliReleaseAuthFailureValidationResult,
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
                "repository is configured for github-releases storage without GitHub auth.\n"
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
        missing_release_context = [
            fragment
            for fragment in self.config.expected_release_fragments
            if fragment not in lowered_error
        ]
        if len(missing_release_context) == len(self.config.expected_release_fragments):
            failures.append(
                "Step 1 failed: the visible CLI error was not an explicit release-backed "
                "auth/configuration failure.\n"
                "The output did not mention GitHub Releases or release-backed storage.\n"
                f"Visible output:\n{visible_error}\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
            )

        has_auth_context = any(
            fragment in lowered_error for fragment in self.config.expected_auth_fragments
        )
        if not has_auth_context:
            failures.append(
                "Step 1 failed: the visible CLI error did not explain that GitHub "
                "authentication or release-upload configuration is required.\n"
                f"Visible output:\n{visible_error}\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
            )

        if not failures:
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
                    "with release-backed auth/configuration guidance instead of a success "
                    "or fallback-shaped result."
                ),
                observed=visible_error,
            )
        return failures

    def _validate_repository_state(
        self,
        validation: TrackStateCliReleaseAuthFailureValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_state
        if final_state.expected_attachment_exists:
            failures.append(
                "Step 2 failed: the file was written to the local repository attachment "
                "path even though release-backed auth was missing.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.stored_files:
            failures.append(
                "Step 2 failed: the repository gained files under the local attachments "
                "directory even though repository-path fallback is prohibited.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.git_status_lines:
            failures.append(
                "Step 2 failed: the failed upload left local repository changes behind.\n"
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
                    f"git_status={list(final_state.git_status_lines)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified from a user's perspective that no `attachments/` file "
                    "appeared in the repository after the failed command."
                ),
                observed=(
                    f"attachment_directory_exists={final_state.attachment_directory_exists}; "
                    f"stored_files={attachment_listing}"
                ),
            )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts500ReleaseAuthFailureScenario()

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
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured with {_jira_inline('attachmentStorage.mode = github-releases')}.",
        "* Removed GitHub credentials from the runtime environment and inspected the caller-visible CLI error output.",
        f"* Inspected the repository path {_jira_inline(_as_text(result.get('expected_attachment_relative_path')))} and the local attachments directory after the command.",
        "",
        "h4. Result",
        "* Step 1 passed: the CLI failed immediately with explicit release-backed auth/configuration guidance.",
        f"* Observed error: {_jira_inline(visible_error)}",
        "* Step 2 passed: no local attachment file was written and the repository stayed clean.",
        "* Human-style verification passed: the terminal output clearly explained the auth/configuration problem, and no fallback file appeared in the repository.",
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
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases`.",
        "- Removed GitHub credentials from the runtime environment and inspected the caller-visible CLI error output.",
        f"- Inspected `{_as_text(result.get('expected_attachment_relative_path'))}` and the local attachments directory after the command.",
        "",
        "## Result",
        "- Step 1 passed: the CLI failed immediately with explicit release-backed auth/configuration guidance.",
        f"- Observed error: `{visible_error}`",
        "- Step 2 passed: no local attachment file was written and the repository stayed clean.",
        "- Human-style verification passed: the terminal output clearly explained the auth/configuration problem, and no fallback file appeared in the repository.",
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
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    final_state = result.get("final_state")
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    expected_path = _as_text(result.get("expected_attachment_relative_path"))
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured with {_jira_inline('attachmentStorage.mode = github-releases')} and no GitHub token in CLI args or environment.",
        "* Inspected the caller-visible CLI output and the repository attachment path after the command.",
        "",
        "h4. Result",
        "* ❌ Step 1 failed: the command failed, but the visible output was generic and did not explicitly mention missing GitHub auth/configuration for GitHub Releases storage.",
        f"* Observed error code/category: {_jira_inline(_as_text(result.get('observed_error_code')))} / {_jira_inline(_as_text(result.get('observed_error_category')))}",
        f"* Observed visible output: {_jira_inline(visible_error)}",
        "* ✅ Step 2 passed: no file was written to the local repository attachment path.",
        "* Human-style verification observed a terminal error and no local attachment file, but the visible error text did not match the expected explicit release-auth/configuration guidance.",
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
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured with `attachmentStorage.mode = github-releases` and no GitHub token in CLI args or environment.",
        "- Inspected the caller-visible CLI output and the repository attachment path after the command.",
        "",
        "## Result",
        "- ❌ Step 1 failed: the command failed, but the visible output was generic and did not explicitly mention missing GitHub auth/configuration for GitHub Releases storage.",
        f"- Observed error code/category: `{_as_text(result.get('observed_error_code'))}` / `{_as_text(result.get('observed_error_category'))}`",
        f"- Observed visible output: `{visible_error}`",
        "- ✅ Step 2 passed: no file was written to the local repository attachment path.",
        "- Human-style verification observed a terminal error and no local attachment file, but the visible error text did not match the expected explicit release-auth/configuration guidance.",
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
        f"h4. Environment",
        f"* Repository path: {_jira_inline(_as_text(result.get('repository_path')))}",
        f"* Command: {_jira_inline(_as_text(result.get('ticket_command')))}",
        f"* OS: {platform.system()}",
        f"* Remote origin: {_jira_inline(_as_text(result.get('remote_origin_url')))}",
        "* Auth setup: GH_TOKEN, GITHUB_TOKEN, and TRACKSTATE_TOKEN were removed from the process environment before execution.",
        "",
        "h4. Steps to Reproduce",
        (
            f"# ✅ Create a local TrackState repository whose {_jira_inline('project.json')} sets "
            f"{_jira_inline('attachmentStorage.mode = github-releases')} and whose Git remote points at "
            f"{_jira_inline(_as_text(result.get('remote_origin_url')))}. Observed: the fixture "
            "repository opened normally and contained TS-475 with no seeded attachments."
        ),
        (
            f"# ❌ Execute CLI command: {_jira_inline(_as_text(result.get('ticket_command')))}. "
            f"Observed: exit code {_as_text(result.get('exit_code'))}; visible output = "
            f"{visible_error}"
        ),
        (
            f"# ✅ Inspect the command output and the repository {_jira_inline('attachments/')} path. "
            f"Observed: {_jira_inline(expected_path)} was not created, stdout showed the generic "
            f"repository error envelope below, and the repository stayed clean."
        ),
        "",
        "h4. Expected Result",
        "* The command should fail with an explicit release-auth/configuration error that tells the user GitHub authentication or GitHub Releases configuration is required.",
        f"* The file must not be written to the local repository path {_jira_inline(expected_path)}.",
        "* Silent fallback to repository-path storage must not occur.",
        "",
        "h4. Actual Result",
        "* The file was not written locally, so repository-path fallback did not occur.",
        (
            "* However, the command only returned a generic repository failure "
            f"({_jira_inline(_as_text(result.get('observed_error_code')))} / "
            f"{_jira_inline(_as_text(result.get('observed_error_category')))}) with message "
            f"{_jira_inline(_as_text(result.get('observed_error_message')) or visible_error)} instead of explicit "
            "release-auth/configuration guidance."
        ),
        "",
        "h4. Logs / Error Output",
        "{code}",
        _as_text(result.get("traceback")).rstrip(),
        "{code}",
        "",
        "h4. Notes",
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
    state: TrackStateCliReleaseAuthFailureRepositoryState,
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
        "remote_origin_url": state.remote_origin_url,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _describe_state(
    state: TrackStateCliReleaseAuthFailureRepositoryState,
) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


def _format_stored_files(
    stored_files: tuple[TrackStateCliReleaseAuthFailureStoredFile, ...],
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
    for fragment in (_collapse_output(stdout), _collapse_output(stderr)):
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
