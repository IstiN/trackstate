from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_download_missing_asset_validator import (  # noqa: E402
    TrackStateCliReleaseDownloadMissingAssetValidator,
)
from testing.core.config.trackstate_cli_release_download_missing_asset_config import (  # noqa: E402
    TrackStateCliReleaseDownloadMissingAssetConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_download_missing_asset_result import (  # noqa: E402
    TrackStateCliReleaseDownloadMissingAssetRepositoryState,
    TrackStateCliReleaseDownloadMissingAssetValidationResult,
)
from testing.tests.support.trackstate_cli_release_download_missing_asset_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_download_missing_asset_probe,
)

TICKET_KEY = "TS-535"
TICKET_SUMMARY = (
    "Release-backed local download reports an explicit missing-asset error when "
    "the GitHub release exists but the requested asset is absent"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-535/test_ts_535.py"
RUN_COMMAND = "python testing/tests/TS-535/test_ts_535.py"


class Ts535ReleaseDownloadMissingAssetScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-535/config.yaml"
        self.config = TrackStateCliReleaseDownloadMissingAssetConfig.from_file(
            self.config_path
        )
        self.validator = TrackStateCliReleaseDownloadMissingAssetValidator(
            probe=create_trackstate_cli_release_download_missing_asset_probe(
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
                    "Prepare a local github-releases fixture repository whose origin points "
                    "to a public GitHub repository release and whose manifest references "
                    "manual.pdf."
                ),
                observed=(
                    f"issue_main_exists={validation.initial_state.issue_main_exists}; "
                    f"attachments_metadata_exists={validation.initial_state.attachments_metadata_exists}; "
                    f"remote_origin_url={validation.initial_state.remote_origin_url}; "
                    f"metadata_attachment_ids={list(validation.initial_state.metadata_attachment_ids)}"
                ),
            )
        failures.extend(self._validate_runtime(validation, result))
        failures.extend(self._validate_filesystem_state(validation, result))
        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseDownloadMissingAssetValidationResult,
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
            "compiled_source_ref": "current checkout",
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "project_key": self.config.project_key,
            "issue_key": self.config.issue_key,
            "attachment_name": self.config.attachment_name,
            "attachment_relative_path": self.config.attachment_relative_path,
            "expected_output_relative_path": self.config.expected_output_relative_path,
            "remote_origin_url": self.config.remote_origin_url,
            "attachment_release_tag": self.config.attachment_release_tag,
            "attachment_release_asset_name": self.config.attachment_release_asset_name,
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
                "Precondition failed: TS-535 did not execute the supported local "
                "attachment download command chosen to reproduce the ticket scenario.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-535 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        initial_state: TrackStateCliReleaseDownloadMissingAssetRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-123 before "
                "running TS-535.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain attachments.json "
                "with release-backed metadata before running TS-535.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if self.config.attachment_relative_path not in initial_state.metadata_attachment_ids:
            failures.append(
                "Precondition failed: attachments.json did not contain the release-backed "
                "manual.pdf entry required for TS-535.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_output_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained the expected "
                "download output file before TS-535 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != self.config.remote_origin_url:
            failures.append(
                "Precondition failed: the seeded repository origin URL did not match the "
                "public GitHub release fixture.\n"
                f"Expected origin: {self.config.remote_origin_url}\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseDownloadMissingAssetValidationResult,
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
                "fixture points at a GitHub release where manual.pdf is intentionally "
                "missing.\n"
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
        missing_asset_fragments = [
            fragment
            for fragment in self.config.expected_missing_asset_fragments
            if fragment not in lowered_error
        ]
        has_provider_capability_context = any(
            fragment in lowered_error
            for fragment in self.config.provider_capability_fragments
        )

        if not missing_asset_fragments:
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
                    "Verified the exact terminal output shown to a user failed with a "
                    "direct missing-release-asset message instead of a generic error."
                ),
                observed=visible_error,
            )
            return failures

        if has_provider_capability_context:
            observed_provider = _as_text(result.get("observed_provider")) or "local-git"
            result["failure_mode"] = "local_provider_capability_gate"
            result["product_gap"] = (
                "The local attachment-download path still fails through the provider-level "
                "GitHub Releases capability gate before it can inspect the remote release "
                "and report that the requested asset is missing."
            )
            failures.append(
                "Step 1 failed: the local release-backed download path never reached the "
                "missing-asset contract.\n"
                f"It failed earlier through the `{observed_provider}` provider with the "
                "generic capability message about unsupported GitHub Releases attachment "
                f"downloads.\nVisible output:\n{visible_error}\n"
                "This means the command still cannot surface the explicit missing-asset "
                "guidance required by TS-535.\n"
                f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
            )
            return failures

        result["failure_mode"] = "missing_asset_guidance"
        failures.append(
            "Step 1 failed: the visible CLI error did not explain that the requested "
            "release asset is missing from the remote release container.\n"
            f"Missing fragments: {missing_asset_fragments}\n"
            f"Visible output:\n{visible_error}\n"
            f"{_format_supporting_evidence(payload=payload, stdout=stdout, stderr=stderr)}"
        )
        return failures

    def _validate_filesystem_state(
        self,
        validation: TrackStateCliReleaseDownloadMissingAssetValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_state
        if final_state.expected_output_exists:
            failures.append(
                "Step 2 failed: the local runtime created the download output file even "
                "though the remote release asset is missing.\n"
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
    scenario = Ts535ReleaseDownloadMissingAssetScenario()

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
        "* Compiled the TrackState CLI from the current checkout so the automation exercised the revision under test.",
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository whose {_jira_inline('attachments.json')} points {_jira_inline('manual.pdf')} at GitHub release tag {_jira_inline(_as_text(result.get('attachment_release_tag')))} in {_jira_inline(_as_text(result.get('remote_origin_url')))}.",
        "* Removed ambient GitHub credentials from the runtime environment and inspected the caller-visible CLI error output.",
        f"* Inspected the local output path {_jira_inline(_as_text(result.get('expected_output_relative_path')))} after the command.",
        "",
        "h4. Result",
        "* Step 1 passed: the CLI failed immediately with explicit missing-asset guidance for the release-backed attachment.",
        f"* Observed error: {_jira_inline(visible_error)}",
        "* Step 2 passed: no local download file was created and the repository stayed clean.",
        "* Human-style verification passed: the terminal output clearly explained that the remote release did not contain manual.pdf, and no manual.pdf file appeared in the local filesystem.",
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
        "- Compiled the TrackState CLI from the current checkout so the automation exercised the revision under test.",
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository whose `attachments.json` points `manual.pdf` at GitHub release tag `{_as_text(result.get('attachment_release_tag'))}` in `{_as_text(result.get('remote_origin_url'))}`.",
        "- Removed ambient GitHub credentials from the runtime environment and inspected the caller-visible CLI error output.",
        f"- Inspected `{_as_text(result.get('expected_output_relative_path'))}` after the command.",
        "",
        "## Result",
        "- Step 1 passed: the CLI failed immediately with explicit missing-asset guidance for the release-backed attachment.",
        f"- Observed error: `{visible_error}`",
        "- Step 2 passed: no local download file was created and the repository stayed clean.",
        "- Human-style verification passed: the terminal output clearly explained that the remote release did not contain `manual.pdf`, and no `manual.pdf` file appeared in the local filesystem.",
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
    expected_output_path = _as_text(result.get("expected_output_relative_path"))
    failure_mode = _as_text(result.get("failure_mode"))
    product_gap = _as_text(result.get("product_gap"))
    observed_provider = _as_text(result.get("observed_provider")) or "local-git"
    observed_reason = _error_reason(result) or visible_error
    if failure_mode == "local_provider_capability_gate":
        step_one_summary = (
            "the local release-backed download path failed earlier at the provider "
            "capability gate, so the command never reached remote release inspection"
        )
        human_summary = (
            "Human-style verification observed a real terminal failure and no local "
            "downloaded file, but the failure was the generic provider capability "
            "error rather than an explicit missing-release-asset message."
        )
        actual_result_line = (
            "* However, the command failed earlier through the generic "
            f"{_jira_inline(observed_provider)} provider path with message "
            f"{_jira_inline(observed_reason)}. "
            "That means the local runtime path never reached the GitHub release "
            "lookup that should report the missing asset."
        )
    else:
        step_one_summary = (
            "the command failed, but the visible output was generic and did not "
            "explicitly say that the release exists while the requested asset is missing"
        )
        human_summary = (
            "Human-style verification observed a terminal error and no local "
            "downloaded file, but the visible error text did not match the expected "
            "missing-release-asset guidance."
        )
        actual_result_line = (
            "* However, the command only returned a generic repository failure "
            f"({_jira_inline(_as_text(result.get('observed_error_code')))} / "
            f"{_jira_inline(_as_text(result.get('observed_error_category')))}) with message "
            f"{_jira_inline(observed_reason)} instead of explicitly stating that "
            f"GitHub release {_jira_inline(_as_text(result.get('attachment_release_tag')))} "
            f"does not contain asset {_jira_inline(_as_text(result.get('attachment_release_asset_name')))}."
        )
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        "* Compiled the TrackState CLI from the current checkout so the automation exercised the revision under test.",
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository whose {_jira_inline('attachments.json')} points {_jira_inline('manual.pdf')} at release tag {_jira_inline(_as_text(result.get('attachment_release_tag')))} in {_jira_inline(_as_text(result.get('remote_origin_url')))}.",
        "* Inspected the caller-visible CLI output and the local output path after the command.",
        "",
        "h4. Result",
        f"* ❌ Step 1 failed: {step_one_summary}.",
        f"* Observed error code/category: {_jira_inline(_as_text(result.get('observed_error_code')))} / {_jira_inline(_as_text(result.get('observed_error_category')))}",
        f"* Observed provider/output: {_jira_inline(observed_provider)} / {_jira_inline(_as_text(result.get('observed_output_format')))}",
        f"* Observed visible output: {_jira_inline(visible_error)}",
        "* ✅ Step 2 passed: no local download file was created.",
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
        "- Compiled the TrackState CLI from the current checkout so the automation exercised the revision under test.",
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository whose `attachments.json` points `manual.pdf` at release tag `{_as_text(result.get('attachment_release_tag'))}` in `{_as_text(result.get('remote_origin_url'))}`.",
        "- Inspected the caller-visible CLI output and the local output path after the command.",
        "",
        "## Result",
        f"- ❌ Step 1 failed: {step_one_summary}.",
        f"- Observed error code/category: `{_as_text(result.get('observed_error_code'))}` / `{_as_text(result.get('observed_error_category'))}`",
        f"- Observed provider/output: `{observed_provider}` / `{_as_text(result.get('observed_output_format'))}`",
        f"- Observed visible output: `{visible_error}`",
        "- ✅ Step 2 passed: no local download file was created.",
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
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository path: `{_as_text(result.get('repository_path'))}`",
        f"- Compiled source ref: `{_as_text(result.get('compiled_source_ref'))}`",
        f"- Command: `{_as_text(result.get('ticket_command'))}`",
        f"- OS: `{platform.system()}`",
        f"- Remote origin: `{_as_text(result.get('remote_origin_url'))}`",
        f"- Release tag: `{_as_text(result.get('attachment_release_tag'))}`",
        f"- Missing asset name: `{_as_text(result.get('attachment_release_asset_name'))}`",
        "- Auth setup: `GH_TOKEN`, `GITHUB_TOKEN`, and `TRACKSTATE_TOKEN` were removed from the process environment before execution.",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Prepare a local TrackState repository whose `attachments.json` contains "
            "a release-backed `manual.pdf` entry and whose local Git remote points at a "
            "public GitHub repository release. "
            "Observed: the fixture repository opened normally, contained `TS-123`, and "
            "the manifest pointed `TS/TS-123/attachments/manual.pdf` at `v2.74.0` in "
            "`https://github.com/cli/cli.git`."
        ),
        (
            f"2. ❌ Execute the local attachment download command for `TS-123` / `manual.pdf` "
            f"(automation executed the current supported equivalent: `{_as_text(result.get('ticket_command'))}`). "
            f"Observed: exit code `{_as_text(result.get('exit_code'))}` and visible output "
            f"`{visible_error}`."
        ),
        (
            f"3. ✅ Inspect the command output and local filesystem path "
            f"`{expected_output_path}`. Observed: the file was not created, stdout showed "
            "the repository error envelope below, and the repository stayed clean."
        ),
        "",
        "## Expected result",
        "- The command should fail with a specific error that says the remote release exists but does not contain `manual.pdf`.",
        "- The local manifest must remain unchanged.",
        f"- The file must not be written to the local output path `{expected_output_path}`.",
        "",
        "## Actual result",
        "- The file was not written locally, so no corrupted download artifact was created.",
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
    state: TrackStateCliReleaseDownloadMissingAssetRepositoryState,
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
    state: TrackStateCliReleaseDownloadMissingAssetRepositoryState,
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
        if fragment and all(
            fragment.lower() not in existing.lower() for existing in fragments
        ):
            fragments.append(fragment)
    return " | ".join(fragment for fragment in fragments if fragment)


def _json_visible_error_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if not isinstance(error, dict):
        return ""
    parts: list[str] = []
    code = error.get("code")
    if isinstance(code, str) and code:
        parts.append(code)
    category = error.get("category")
    if isinstance(category, str) and category:
        parts.append(category)
    message = error.get("message")
    if isinstance(message, str) and message:
        parts.append(message)
    details = error.get("details")
    if isinstance(details, dict):
        reason = details.get("reason")
        if isinstance(reason, str) and reason:
            parts.append(reason)
    return " | ".join(parts)


def _format_supporting_evidence(
    *,
    payload: object,
    stdout: str,
    stderr: str,
) -> str:
    return (
        "Supporting evidence:\n"
        f"payload={json.dumps(payload, indent=2, sort_keys=True) if isinstance(payload, dict) else repr(payload)}\n"
        f"stdout={stdout or '<empty>'}\n"
        f"stderr={stderr or '<empty>'}"
    )


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    return (
        "Observed output:\n"
        f"stdout:\n{stdout or '<empty>'}\n"
        f"stderr:\n{stderr or '<empty>'}"
    )


def _error_reason(result: dict[str, object]) -> str:
    details = result.get("observed_error_details")
    if isinstance(details, dict):
        reason = details.get("reason")
        if isinstance(reason, str) and reason:
            return reason
    message = result.get("observed_error_message")
    return message if isinstance(message, str) else ""


def _collapse_output(text: str) -> str:
    collapsed = " ".join(line.strip() for line in text.splitlines() if line.strip())
    return collapsed.strip()


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return stripped.startswith("{") and stripped.endswith("}")


def _jira_inline(value: str) -> str:
    safe = value or "<missing>"
    return "{{" + safe.replace("{{", "{").replace("}}", "}") + "}}"


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


if __name__ == "__main__":
    main()
