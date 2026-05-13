from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_identity_multiple_remotes_validator import (  # noqa: E402
    TrackStateCliReleaseIdentityMultipleRemotesValidator,
)
from testing.core.config.trackstate_cli_release_identity_multiple_remotes_config import (  # noqa: E402
    TrackStateCliReleaseIdentityMultipleRemotesConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_identity_multiple_remotes_result import (  # noqa: E402
    TrackStateCliReleaseIdentityMultipleRemotesRepositoryState,
    TrackStateCliReleaseIdentityMultipleRemotesValidationResult,
)
from testing.tests.support.trackstate_cli_release_identity_multiple_remotes_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_identity_multiple_remotes_probe,
)

TICKET_KEY = "TS-542"
TICKET_SUMMARY = (
    "Release-backed local download resolves GitHub identity from an upstream "
    "remote when origin is non-GitHub"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-542/test_ts_542.py"
RUN_COMMAND = "python testing/tests/TS-542/test_ts_542.py"


class Ts542ReleaseIdentityMultipleRemotesScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-542/config.yaml"
        self.config = TrackStateCliReleaseIdentityMultipleRemotesConfig.from_file(
            self.config_path
        )
        self.validator = TrackStateCliReleaseIdentityMultipleRemotesValidator(
            probe=create_trackstate_cli_release_identity_multiple_remotes_probe(
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
                    "Prepare a local github-releases fixture repository whose non-GitHub "
                    "origin is paired with a GitHub upstream remote."
                ),
                observed=(
                    f"remote_names={list(validation.initial_state.remote_names)}; "
                    f"remote_origin_url={validation.initial_state.remote_origin_url}; "
                    f"remote_upstream_url={validation.initial_state.remote_upstream_url}; "
                    f"metadata_attachment_ids={list(validation.initial_state.metadata_attachment_ids)}"
                ),
            )
        failures.extend(self._validate_runtime(validation, result))
        failures.extend(self._validate_filesystem_state(validation, result))
        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseIdentityMultipleRemotesValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        data = payload_dict.get("data") if isinstance(payload_dict, dict) else None
        data_dict = data if isinstance(data, dict) else None
        target = payload_dict.get("target") if isinstance(payload_dict, dict) else None
        target_dict = target if isinstance(target, dict) else None
        attachment = data_dict.get("attachment") if isinstance(data_dict, dict) else None
        attachment_dict = attachment if isinstance(attachment, dict) else None
        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "ticket_command": self.config.ticket_command,
            "supported_ticket_command": self.config.supported_ticket_command,
            "requested_command": validation.observation.requested_command_text,
            "executed_command": validation.observation.executed_command_text,
            "compiled_binary_path": validation.observation.compiled_binary_path,
            "repository_path": validation.observation.repository_path,
            "config_path": str(self.config_path),
            "os": platform.system(),
            "project_key": self.config.project_key,
            "issue_key": self.config.issue_key,
            "attachment_name": self.config.attachment_name,
            "attachment_relative_path": self.config.attachment_relative_path,
            "expected_output_relative_path": self.config.expected_output_relative_path,
            "origin_remote_url": self.config.origin_remote_url,
            "upstream_remote_url": self.config.upstream_remote_url,
            "attachment_release_tag": self.config.attachment_release_tag,
            "attachment_release_asset_name": self.config.attachment_release_asset_name,
            "expected_download_sha256": self.config.expected_download_sha256,
            "expected_download_size_bytes": self.config.expected_download_size_bytes,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "data": data_dict,
            "target": target_dict,
            "attachment": attachment_dict,
            "observed_provider": payload_dict.get("provider")
            if isinstance(payload_dict, dict)
            else None,
            "observed_output_format": payload_dict.get("output")
            if isinstance(payload_dict, dict)
            else None,
            "observed_saved_file": data_dict.get("savedFile")
            if isinstance(data_dict, dict)
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
                "Precondition failed: TS-542 did not execute the current supported "
                "download command equivalent of the ticket scenario.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-542 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        initial_state: TrackStateCliReleaseIdentityMultipleRemotesRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-123 before "
                "running TS-542.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.attachments_metadata_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain attachments.json "
                "with release-backed metadata before running TS-542.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if self.config.attachment_relative_path not in initial_state.metadata_attachment_ids:
            failures.append(
                "Precondition failed: attachments.json did not contain the release-backed "
                "manual.pdf entry required for TS-542.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.expected_output_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained the expected "
                "download output file before TS-542 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != self.config.origin_remote_url:
            failures.append(
                "Precondition failed: the seeded repository origin URL did not match the "
                "non-GitHub remote required by TS-542.\n"
                f"Expected origin: {self.config.origin_remote_url}\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.remote_upstream_url != self.config.upstream_remote_url:
            failures.append(
                "Precondition failed: the seeded repository upstream URL did not match the "
                "GitHub remote required by TS-542.\n"
                f"Expected upstream: {self.config.upstream_remote_url}\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if tuple(sorted(initial_state.remote_names)) != tuple(
            sorted((self.config.origin_remote_name, self.config.upstream_remote_name))
        ):
            failures.append(
                "Precondition failed: the seeded repository did not expose both expected "
                "Git remotes before TS-542 ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseIdentityMultipleRemotesValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        stdout = observation.result.stdout
        stderr = observation.result.stderr
        visible_output = _visible_output_text(payload, stdout=stdout, stderr=stderr)
        result["visible_output_text"] = visible_output

        if observation.result.exit_code != 0:
            lowered_output = visible_output.lower()
            has_provider_capability_context = any(
                fragment in lowered_output
                for fragment in self.config.provider_capability_fragments
            )
            result["failure_mode"] = (
                "local_provider_capability_gate"
                if has_provider_capability_context
                else "runtime_failure"
            )
            failures.append(
                "Step 1 failed: executing the local release-backed download command did "
                "not succeed even though the repository exposed a GitHub upstream remote.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        if not isinstance(payload_dict, dict):
            result["failure_mode"] = "missing_success_payload"
            failures.append(
                "Step 1 failed: the command exited successfully, but stdout did not contain "
                "the expected JSON success payload.\n"
                f"{_observed_command_output(stdout=stdout, stderr=stderr)}"
            )
            return failures

        if payload_dict.get("ok") is not True:
            result["failure_mode"] = "non_success_payload"
            failures.append(
                "Step 1 failed: the JSON payload did not report success.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
            return failures

        data = payload_dict.get("data")
        if not isinstance(data, dict):
            result["failure_mode"] = "missing_data_payload"
            failures.append(
                "Step 1 failed: the JSON success envelope did not contain a `data` object.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
            return failures

        target = payload_dict.get("target")
        if not isinstance(target, dict):
            result["failure_mode"] = "missing_target_payload"
            failures.append(
                "Step 1 failed: the JSON success envelope did not contain a `target` object.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
            return failures

        attachment = data.get("attachment")
        if not isinstance(attachment, dict):
            result["failure_mode"] = "missing_attachment_payload"
            failures.append(
                "Step 1 failed: the JSON success envelope did not contain attachment metadata.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
            return failures

        if payload_dict.get("provider") != "local-git":
            failures.append(
                "Step 1 failed: the success envelope did not report the local-git provider.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if payload_dict.get("output") != "json":
            failures.append(
                "Step 1 failed: the success envelope did not preserve JSON output mode.\n"
                f"Observed payload:\n{json.dumps(payload_dict, indent=2, sort_keys=True)}"
            )
        if target.get("type") != "local":
            failures.append(
                "Step 1 failed: the success envelope did not identify a local target.\n"
                f"Observed target:\n{json.dumps(target, indent=2, sort_keys=True)}"
            )
        if target.get("value") != observation.repository_path:
            failures.append(
                "Step 1 failed: the success envelope did not show the disposable fixture "
                "repository path that the user targeted.\n"
                f"Expected target value: {observation.repository_path}\n"
                f"Observed target:\n{json.dumps(target, indent=2, sort_keys=True)}"
            )
        if data.get("command") != "attachment-download":
            failures.append(
                "Step 1 failed: the success envelope did not report the canonical "
                "attachment-download command.\n"
                f"Observed data:\n{json.dumps(data, indent=2, sort_keys=True)}"
            )
        if data.get("authSource") != "none":
            failures.append(
                "Step 1 failed: the local download unexpectedly reported hosted "
                "authentication usage.\n"
                f"Observed data:\n{json.dumps(data, indent=2, sort_keys=True)}"
            )
        if data.get("issue") != self.config.issue_key:
            failures.append(
                "Step 1 failed: the success envelope did not identify `TS-123` as the "
                "downloaded attachment owner.\n"
                f"Observed data:\n{json.dumps(data, indent=2, sort_keys=True)}"
            )
        expected_saved_file = str(
            (Path(observation.repository_path) / self.config.expected_output_relative_path)
            .resolve()
        )
        observed_saved_file = data.get("savedFile")
        if not isinstance(observed_saved_file, str) or Path(observed_saved_file).resolve() != Path(
            expected_saved_file
        ).resolve():
            failures.append(
                "Step 1 failed: the success envelope did not return the resolved saved-file "
                "path the user requested.\n"
                f"Expected savedFile: {expected_saved_file}\n"
                f"Observed data:\n{json.dumps(data, indent=2, sort_keys=True)}"
            )
        if attachment.get("id") != self.config.attachment_relative_path:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the requested "
                "attachment identifier.\n"
                f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("name") != self.config.attachment_name:
            failures.append(
                "Step 1 failed: the attachment metadata did not show the user-facing "
                "attachment filename.\n"
                f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        if attachment.get("revisionOrOid") != self.config.attachment_revision_or_oid:
            failures.append(
                "Step 1 failed: the attachment metadata did not preserve the configured "
                "revision identifier.\n"
                f"Observed attachment:\n{json.dumps(attachment, indent=2, sort_keys=True)}"
            )
        lowered_output = visible_output.lower()
        leaked_provider_capability_fragments = [
            fragment
            for fragment in self.config.provider_capability_fragments
            if fragment in lowered_output
        ]
        if leaked_provider_capability_fragments:
            result["failure_mode"] = "local_provider_capability_gate"
            failures.append(
                "Step 1 failed: the caller-visible output still exposed the provider "
                "capability gate instead of a clean success result.\n"
                f"Observed visible output: {visible_output}\n"
                f"Unexpected fragments: {leaked_provider_capability_fragments}"
            )

        if not failures:
            _record_step(
                result,
                step=1,
                status="passed",
                action=self.config.supported_ticket_command,
                observed=(
                    f"exit_code={observation.result.exit_code}; "
                    f"provider={payload_dict.get('provider')}; "
                    f"target_value={target.get('value')}; "
                    f"savedFile={observed_saved_file}; "
                    f"attachment_name={attachment.get('name')}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the exact user-visible JSON success envelope showed the local "
                    "repository target, the `manual.pdf` attachment metadata, and the saved "
                    "file path without any provider-capability error."
                ),
                observed=visible_output,
            )
        return failures

    def _validate_filesystem_state(
        self,
        validation: TrackStateCliReleaseIdentityMultipleRemotesValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        final_state = validation.final_state
        preview_text = "\n".join(final_state.expected_output_preview_lines)
        if not final_state.expected_output_exists:
            failures.append(
                "Step 2 failed: the local runtime did not create the requested output file.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
            return failures

        if final_state.expected_output_size_bytes != self.config.expected_download_size_bytes:
            failures.append(
                "Step 2 failed: the downloaded file size did not match the live release asset.\n"
                f"Expected size: {self.config.expected_download_size_bytes}\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if final_state.expected_output_sha256 != self.config.expected_download_sha256:
            failures.append(
                "Step 2 failed: the downloaded file checksum did not match the live release asset.\n"
                f"Expected sha256: {self.config.expected_download_sha256}\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        lowered_preview = preview_text.lower()
        missing_preview_fragments = [
            fragment
            for fragment in self.config.expected_output_fragments
            if fragment not in lowered_preview
        ]
        if missing_preview_fragments:
            failures.append(
                "Step 2 failed: the downloaded file preview did not contain the expected "
                "release-asset content.\n"
                f"Missing fragments: {missing_preview_fragments}\n"
                f"Observed preview:\n{preview_text}"
            )
        if final_state.git_status_lines != ("?? downloads/",):
            failures.append(
                "Step 2 failed: the repository changed in an unexpected way after the "
                "download. Only the requested downloads directory should be untracked.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )
        if not final_state.downloads_directory_exists:
            failures.append(
                "Step 2 failed: the downloads directory was not created for the saved file.\n"
                f"Observed state:\n{_describe_state(final_state)}"
            )

        if not failures:
            _record_step(
                result,
                step=2,
                status="passed",
                action="Inspect the saved file and repository state after the successful download.",
                observed=(
                    f"expected_output_exists={final_state.expected_output_exists}; "
                    f"expected_output_size_bytes={final_state.expected_output_size_bytes}; "
                    f"expected_output_sha256={final_state.expected_output_sha256}; "
                    f"git_status={list(final_state.git_status_lines)}"
                ),
            )
            _record_human_verification(
                result,
                check=(
                    "Verified from a user's perspective that `downloads/manual.pdf` was "
                    "actually created and its visible text content matched the expected "
                    "release checksum file preview."
                ),
                observed=preview_text,
            )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts542ReleaseIdentityMultipleRemotesScenario()

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

    visible_output = _as_text(result.get("visible_output_text"))
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
        (
            f"* Seeded a disposable local TrackState repository with non-GitHub "
            f"{_jira_inline('origin')} = {_jira_inline(_as_text(result.get('origin_remote_url')))} "
            f"and GitHub {_jira_inline('upstream')} = "
            f"{_jira_inline(_as_text(result.get('upstream_remote_url')))}."
        ),
        (
            f"* Verified the downloaded file at "
            f"{_jira_inline(_as_text(result.get('expected_output_relative_path')))} "
            f"matched the live GitHub release asset "
            f"{_jira_inline(_as_text(result.get('attachment_release_asset_name')))} "
            f"from tag {_jira_inline(_as_text(result.get('attachment_release_tag')))}."
        ),
        "",
        "h4. Result",
        "* Step 1 passed: the command succeeded with a local JSON success envelope instead of a provider-capability failure.",
        f"* Observed success output: {_jira_inline(visible_output)}",
        (
            f"* Step 2 passed: {_jira_inline(_as_text(result.get('expected_output_relative_path')))} "
            f"was created with sha256 "
            f"{_jira_inline(_as_text(result.get('expected_download_sha256')))} and size "
            f"{_jira_inline(_as_text(result.get('expected_download_size_bytes')))} bytes."
        ),
        "* Human-style verification passed: the visible result identified `TS-123`, `manual.pdf`, and the saved file path, and opening the saved file showed the expected release checksum lines.",
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
        (
            f"- Seeded a disposable local TrackState repository with non-GitHub `origin` = "
            f"`{_as_text(result.get('origin_remote_url'))}` and GitHub `upstream` = "
            f"`{_as_text(result.get('upstream_remote_url'))}`."
        ),
        (
            f"- Verified `{_as_text(result.get('expected_output_relative_path'))}` matched the live GitHub "
            f"release asset `{_as_text(result.get('attachment_release_asset_name'))}` from tag "
            f"`{_as_text(result.get('attachment_release_tag'))}`."
        ),
        "",
        "## Result",
        "- Step 1 passed: the command succeeded with a local JSON success envelope instead of a provider-capability failure.",
        f"- Observed success output: `{visible_output}`",
        (
            f"- Step 2 passed: `{_as_text(result.get('expected_output_relative_path'))}` was created "
            f"with sha256 `{_as_text(result.get('expected_download_sha256'))}` and size "
            f"`{_as_text(result.get('expected_download_size_bytes'))}` bytes."
        ),
        "- Human-style verification passed: the visible result identified `TS-123`, `manual.pdf`, and the saved file path, and opening the saved file showed the expected release checksum lines.",
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
    visible_output = _visible_output_text(result.get("payload"), stdout=stdout, stderr=stderr)
    observed_output = _observed_command_output(stdout=stdout, stderr=stderr)
    final_state = result.get("final_state")
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    expected_output_path = _as_text(result.get("expected_output_relative_path"))
    failure_mode = _as_text(result.get("failure_mode"))
    runtime_succeeded = bool(
        _as_dict(result.get("payload")).get("ok") is True and result.get("exit_code") == 0
    )

    if failure_mode == "local_provider_capability_gate":
        step_two_summary = (
            "the command still surfaced the generic provider capability gate instead of "
            "resolving the GitHub upstream remote"
        )
        actual_result_line = (
            "The visible output still reported the local provider capability failure "
            "(`does not support GitHub Releases attachment downloads`) even though a GitHub "
            "`upstream` remote was configured."
        )
    elif runtime_succeeded:
        step_two_summary = (
            "the command returned success, but the downloaded file did not match the live "
            "release asset or the repository state was not the expected user-visible result"
        )
        actual_result_line = (
            "The command returned a success envelope, but the saved file content or resulting "
            "filesystem state did not match the expected live release-backed download outcome."
        )
    else:
        step_two_summary = (
            "the command did not complete the release-backed download successfully despite "
            "the GitHub upstream remote being available"
        )
        actual_result_line = (
            "The command failed instead of resolving repository identity through the GitHub "
            "`upstream` remote and writing the requested file."
        )

    if runtime_succeeded:
        step_lines = [
            (
                "1. ✅ Prepare a local TrackState repository with multiple remotes: "
                "`origin` pointing to a non-GitHub host and `upstream` pointing to the "
                "correct GitHub repository. Observed: the fixture repository opened "
                "normally, contained `TS-123`, and exposed both configured remotes."
            ),
            (
                f"2. ✅ Execute CLI command for the ticket scenario (automation executed the "
                f"supported equivalent `{_as_text(result.get('supported_ticket_command'))}`). "
                f"Observed: exit code `{_as_text(result.get('exit_code'))}` and a JSON success "
                "envelope on stdout."
            ),
            (
                f"3. ❌ Inspect the command output and downloaded file at `{expected_output_path}`. "
                f"Observed: {error_message}. Final repository state and captured output are included below."
            ),
        ]
    else:
        step_lines = [
            (
                "1. ✅ Prepare a local TrackState repository with multiple remotes: "
                "`origin` pointing to a non-GitHub host and `upstream` pointing to the "
                "correct GitHub repository. Observed: the fixture repository opened "
                "normally, contained `TS-123`, and exposed both configured remotes."
            ),
            (
                f"2. ❌ Execute CLI command for the ticket scenario (automation executed the "
                f"supported equivalent `{_as_text(result.get('supported_ticket_command'))}`). "
                f"Observed: exit code `{_as_text(result.get('exit_code'))}` and visible output "
                f"`{visible_output}`."
            ),
            (
                f"3. ✅ Inspect the command output and local filesystem path `{expected_output_path}`. "
                "Observed: the final repository state below shows what was or was not written."
            ),
        ]

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
        (
            f"* Disposable remotes: {_jira_inline('origin')} = "
            f"{_jira_inline(_as_text(result.get('origin_remote_url')))}, "
            f"{_jira_inline('upstream')} = {_jira_inline(_as_text(result.get('upstream_remote_url')))}."
        ),
        (
            f"* Expected downloaded file: {_jira_inline(expected_output_path)} from release asset "
            f"{_jira_inline(_as_text(result.get('attachment_release_asset_name')))} "
            f"at tag {_jira_inline(_as_text(result.get('attachment_release_tag')))}."
        ),
        "",
        "h4. Result",
        f"* ❌ Step 2/3 failed: {step_two_summary}.",
        f"* Observed visible output: {_jira_inline(visible_output)}",
        f"* Exact failure: {_jira_inline(error_message)}",
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
            f"- Ticket step reviewed: `{_as_text(result.get('ticket_command'))}`. Automation executed "
            f"the current supported equivalent `{_as_text(result.get('supported_ticket_command'))}`."
        ),
        (
            f"- Disposable remotes: `origin` = `{_as_text(result.get('origin_remote_url'))}`, "
            f"`upstream` = `{_as_text(result.get('upstream_remote_url'))}`."
        ),
        (
            f"- Expected downloaded file: `{expected_output_path}` from release asset "
            f"`{_as_text(result.get('attachment_release_asset_name'))}` at tag "
            f"`{_as_text(result.get('attachment_release_tag'))}`."
        ),
        "",
        "## Result",
        f"- ❌ Step 2/3 failed: {step_two_summary}.",
        f"- Observed visible output: `{visible_output}`",
        f"- Exact failure: `{error_message}`",
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
        f"- Ticket step: `{_as_text(result.get('ticket_command'))}`",
        f"- Supported executed command: `{_as_text(result.get('supported_ticket_command'))}`",
        f"- OS: `{platform.system()}`",
        f"- Origin remote: `{_as_text(result.get('origin_remote_url'))}`",
        f"- Upstream remote: `{_as_text(result.get('upstream_remote_url'))}`",
        f"- Release tag: `{_as_text(result.get('attachment_release_tag'))}`",
        f"- Release asset: `{_as_text(result.get('attachment_release_asset_name'))}`",
        "- Auth setup: `GH_TOKEN`, `GITHUB_TOKEN`, and `TRACKSTATE_TOKEN` were removed from the process environment before execution.",
        "",
        "## Steps to reproduce",
        *step_lines,
        "",
        "## Expected result",
        "- The download flow should ignore the non-GitHub `origin`, resolve repository identity from the GitHub `upstream` remote, and bypass the provider capability gate.",
        "- The command should complete successfully and return a local JSON success envelope.",
        (
            f"- The saved file `{expected_output_path}` should match the live release asset "
            f"`{_as_text(result.get('attachment_release_asset_name'))}`."
        ),
        "",
        "## Actual result",
        f"- {actual_result_line}",
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
    state: TrackStateCliReleaseIdentityMultipleRemotesRepositoryState,
) -> dict[str, object]:
    return {
        "issue_main_exists": state.issue_main_exists,
        "attachments_metadata_exists": state.attachments_metadata_exists,
        "metadata_attachment_ids": list(state.metadata_attachment_ids),
        "expected_output_exists": state.expected_output_exists,
        "expected_output_size_bytes": state.expected_output_size_bytes,
        "expected_output_sha256": state.expected_output_sha256,
        "expected_output_preview_lines": list(state.expected_output_preview_lines),
        "downloads_directory_exists": state.downloads_directory_exists,
        "git_status_lines": list(state.git_status_lines),
        "remote_names": list(state.remote_names),
        "remote_origin_url": state.remote_origin_url,
        "remote_upstream_url": state.remote_upstream_url,
        "head_commit_subject": state.head_commit_subject,
        "head_commit_count": state.head_commit_count,
    }


def _describe_state(
    state: TrackStateCliReleaseIdentityMultipleRemotesRepositoryState,
) -> str:
    return json.dumps(_state_to_dict(state), indent=2, sort_keys=True)


def _visible_output_text(
    payload: object,
    *,
    stdout: str = "",
    stderr: str = "",
) -> str:
    fragments: list[str] = []
    payload_text = _json_visible_text(payload)
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


def _json_visible_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    if payload.get("ok") is True:
        target = payload.get("target")
        data = payload.get("data")
        attachment = data.get("attachment") if isinstance(data, dict) else None
        parts = [
            _as_text(payload.get("provider")).strip(),
            _as_text(payload.get("output")).strip(),
            _as_text(data.get("command")).strip() if isinstance(data, dict) else "",
            _as_text(data.get("issue")).strip() if isinstance(data, dict) else "",
            _as_text(attachment.get("name")).strip() if isinstance(attachment, dict) else "",
            _as_text(data.get("savedFile")).strip() if isinstance(data, dict) else "",
            _as_text(target.get("value")).strip() if isinstance(target, dict) else "",
        ]
        return " | ".join(part for part in parts if part)
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


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    return (
        "Observed output:\n"
        f"stdout:\n{stdout or '<empty>'}\n"
        f"stderr:\n{stderr or '<empty>'}"
    )


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


def _as_dict(value: object | None) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    main()
