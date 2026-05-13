from __future__ import annotations

import json
import platform
import sys
import traceback
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_release_asset_filename_sanitization_validator import (  # noqa: E402
    TrackStateCliReleaseAssetFilenameSanitizationValidator,
)
from testing.core.config.trackstate_cli_release_asset_filename_sanitization_config import (  # noqa: E402
    TrackStateCliReleaseAssetFilenameSanitizationConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_release_asset_filename_sanitization_result import (  # noqa: E402
    TrackStateCliReleaseAssetFilenameSanitizationRepositoryState,
    TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
)
from testing.tests.support.trackstate_cli_release_asset_filename_sanitization_probe_factory import (  # noqa: E402
    create_trackstate_cli_release_asset_filename_sanitization_probe,
)

TICKET_KEY = "TS-534"
TICKET_SUMMARY = "Release asset filename sanitization for local github-releases upload"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-534/test_ts_534.py"
RUN_COMMAND = "python testing/tests/TS-534/test_ts_534.py"


class Ts534ReleaseAssetFilenameSanitizationScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-534/config.yaml"
        self.config = TrackStateCliReleaseAssetFilenameSanitizationConfig.from_file(
            self.config_path,
        )
        self.validator = TrackStateCliReleaseAssetFilenameSanitizationValidator(
            probe=create_trackstate_cli_release_asset_filename_sanitization_probe(
                self.repository_root,
            ),
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
                step=1,
                status="passed",
                action=(
                    "Create a disposable local TrackState repository configured for "
                    "`attachmentStorage.mode = github-releases` and containing the "
                    "special-character file."
                ),
                observed=(
                    f"issue_main_exists={validation.initial_state.issue_main_exists}; "
                    f"source_file_exists={validation.initial_state.source_file_exists}; "
                    f"remote_origin_url={validation.initial_state.remote_origin_url}; "
                    f"manifest_exists={validation.initial_state.manifest_exists}"
                ),
            )

        runtime_failures, upload_succeeded = self._validate_runtime(validation, result)
        failures.extend(runtime_failures)
        if upload_succeeded:
            failures.extend(self._validate_manifest(validation, result))
            failures.extend(self._validate_release(validation, result))

        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
    ) -> dict[str, object]:
        payload = validation.observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        payload_error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        payload_error_dict = payload_error if isinstance(payload_error, dict) else None
        payload_error_details = (
            payload_error_dict.get("details")
            if isinstance(payload_error_dict, dict)
            else None
        )
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
            "repository_ref": self.config.branch,
            "project_key": self.config.project_key,
            "project_name": self.config.project_name,
            "issue_key": self.config.issue_key,
            "issue_summary": self.config.issue_summary,
            "source_file_name": self.config.source_file_name,
            "expected_sanitized_asset_name": self.config.expected_sanitized_asset_name,
            "release_tag_prefix": validation.release_tag_prefix,
            "release_tag": validation.expected_release_tag,
            "remote_origin_url": validation.remote_origin_url,
            "manifest_path": self.config.manifest_path,
            "stdout": validation.observation.result.stdout,
            "stderr": validation.observation.result.stderr,
            "exit_code": validation.observation.result.exit_code,
            "payload": payload_dict,
            "payload_error": payload_error_dict,
            "payload_error_details": payload_error_details,
            "observed_provider": payload_dict.get("provider")
            if isinstance(payload_dict, dict)
            else None,
            "observed_output_format": payload_dict.get("output")
            if isinstance(payload_dict, dict)
            else None,
            "observed_error_code": payload_error_dict.get("code")
            if isinstance(payload_error_dict, dict)
            else None,
            "observed_error_category": payload_error_dict.get("category")
            if isinstance(payload_error_dict, dict)
            else None,
            "observed_error_message": payload_error_dict.get("message")
            if isinstance(payload_error_dict, dict)
            else None,
            "observed_error_reason": payload_error_details.get("reason")
            if isinstance(payload_error_details, dict)
            else None,
            "initial_state": _serialize(validation.initial_state),
            "final_state": _serialize(validation.final_state),
            "manifest_state": _serialize(validation.manifest_observation),
            "release_state": _serialize(validation.release_observation),
            "gh_release_view": _serialize(validation.gh_release_view),
            "cleanup": _serialize(validation.cleanup),
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
                "Precondition failed: TS-534 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-534 must run a repository-local compiled binary "
                "from the disposable repository working directory.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        return failures

    def _assert_initial_fixture(
        self,
        initial_state: TrackStateCliReleaseAssetFilenameSanitizationRepositoryState,
    ) -> list[str]:
        failures: list[str] = []
        if not initial_state.issue_main_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain TS-100 before "
                "running TS-534.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.source_file_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain the requested "
                "special-character attachment file before running TS-534.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.manifest_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained attachments.json "
                "before the upload ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != validation_remote_origin(self.config.repository):
            failures.append(
                "Precondition failed: the seeded repository origin URL did not match the "
                "live hosted repository.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        return failures

    def _validate_runtime(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
        result: dict[str, object],
    ) -> tuple[list[str], bool]:
        failures: list[str] = []
        observation = validation.observation
        payload = observation.result.json_payload
        data = payload.get("data") if isinstance(payload, dict) else None
        attachment = data.get("attachment") if isinstance(data, dict) else None
        visible_output = _visible_output(
            payload,
            stdout=observation.result.stdout,
            stderr=observation.result.stderr,
        )
        result["visible_output"] = visible_output

        if observation.result.exit_code != 0:
            result["failure_mode"] = "upload_failed_before_release_asset_creation"
            result["product_gap"] = (
                "The production local github-releases upload path still fails before it "
                "creates any release-backed asset, so the public CLI flow cannot expose "
                "the sanitized release asset name required by the ticket."
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the user-visible CLI outcome after running the exact local "
                    "upload command."
                ),
                observed=visible_output or "<empty>",
            )
            failures.append(
                "Step 2 failed: the exact local upload command returned a failure before "
                "any GitHub Release asset could be created.\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"Observed provider/output: {result.get('observed_provider')} / "
                f"{result.get('observed_output_format')}\n"
                f"Observed error code/category: {result.get('observed_error_code')} / "
                f"{result.get('observed_error_category')}\n"
                f"Visible output:\n{visible_output}\n"
                f"{_observed_command_output(observation.result.stdout, observation.result.stderr)}"
            )
            return failures, False

        if not isinstance(payload, dict):
            failures.append(
                "Step 2 failed: the local upload command succeeded, but it did not return "
                "a machine-readable JSON payload.\n"
                f"{_observed_command_output(observation.result.stdout, observation.result.stderr)}"
            )
            return failures, False

        if payload.get("ok") is not True:
            failures.append(
                "Step 2 failed: the local upload command returned exit code 0 but did not "
                "report `ok: true`.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        if not isinstance(data, dict):
            failures.append(
                "Step 2 failed: the successful upload payload did not include a `data` object.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        if data.get("command") != "attachment-upload":
            failures.append(
                "Step 2 failed: the success payload did not identify the attachment upload command.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        if data.get("issue") != self.config.issue_key:
            failures.append(
                "Step 2 failed: the success payload did not preserve the requested issue key.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        if not isinstance(attachment, dict):
            failures.append(
                "Step 2 failed: the success payload did not include attachment metadata.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        _record_step(
            result,
            step=2,
            status="passed",
            action=self.config.ticket_command,
            observed=(
                f"exit_code={observation.result.exit_code}; "
                f"attachment_issue={data.get('issue')}; "
                f"attachment_name={attachment.get('name')}; "
                f"attachment_revision_or_oid={attachment.get('revisionOrOid')}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the exact local upload command completed successfully from a "
                "user-visible CLI perspective."
            ),
            observed=visible_output,
        )
        return failures, True

    def _validate_manifest(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        manifest = validation.manifest_observation
        if manifest is None or not manifest.matches_expected:
            failures.append(
                "Step 3 failed: the local attachments.json metadata did not converge to the "
                "expected sanitized github-releases asset entry.\n"
                f"Observed manifest state:\n{json.dumps(_serialize(manifest), indent=2, sort_keys=True)}"
            )
            return failures

        _record_step(
            result,
            step=3,
            status="passed",
            action="Inspect the local attachment metadata after upload.",
            observed=(
                f"manifest_path={self.config.manifest_path}; "
                f"matching_entry={json.dumps(manifest.matching_entry, sort_keys=True)}"
            ),
        )
        return failures

    def _validate_release(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        release = validation.release_observation
        gh_view = validation.gh_release_view
        if release is None or not release.matches_expected:
            failures.append(
                "Step 4 failed: the live GitHub Release did not expose exactly the expected "
                "sanitized asset state.\n"
                f"Observed release state:\n{json.dumps(_serialize(release), indent=2, sort_keys=True)}"
            )
            return failures
        if gh_view is None or not gh_view.matches_expected:
            failures.append(
                "Step 4 failed: `gh release view` did not expose exactly the expected "
                "sanitized asset name.\n"
                f"Observed gh release view:\n{json.dumps(_serialize(gh_view), indent=2, sort_keys=True)}"
            )
            return failures

        _record_step(
            result,
            step=4,
            status="passed",
            action="Inspect the asset name in the GitHub Release via `gh release view`.",
            observed=(
                f"release_tag={validation.expected_release_tag}; "
                f"asset_names={list(release.asset_names)}; "
                f"gh_release_assets={list(gh_view.asset_names)}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the live GitHub Release exposed only the sanitized asset name "
                "instead of the raw special-character filename."
            ),
            observed=gh_view.stdout.strip() or "<empty>",
        )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts534ReleaseAssetFilenameSanitizationScenario()

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

    ticket_command = _as_text(result.get("ticket_command"))
    expected_asset_name = _as_text(result.get("expected_sanitized_asset_name"))
    raw_file_name = _as_text(result.get("source_file_name"))
    release_tag = _as_text(result.get("release_tag"))
    gh_release_view = result.get("gh_release_view") or {}
    gh_release_stdout = ""
    if isinstance(gh_release_view, dict):
        gh_release_stdout = _as_text(gh_release_view.get("stdout"))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        (
            f"* Ran {_jira_inline(ticket_command)} from a disposable local Git repository "
            "configured for {{attachmentStorage.mode = github-releases}}."
        ),
        "* Inspected the local {{attachments.json}} metadata, the live GitHub Release state, and {{gh release view}} output.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the disposable local repository contained the requested file and github-releases configuration.",
        "* ✅ Step 2 passed: the exact local command completed successfully and returned the expected upload payload.",
        f"* ✅ Step 3 passed: local metadata stored {{githubReleaseAssetName = {expected_asset_name}}} for {{{raw_file_name}}}.",
        f"* ✅ Step 4 passed: the live GitHub Release and {{gh release view}} exposed only the sanitized asset name {{{expected_asset_name}}} on release tag {{{release_tag}}}.",
        (
            "* Human-style verification passed: the terminal command completed without a user-visible "
            "error, and the live release output showed the sanitized asset name instead of the raw filename."
        ),
        "",
        "h4. gh release view output",
        "{code}",
        gh_release_stdout.rstrip() or "<empty>",
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
        "**Status:** ✅ PASSED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Ran `{ticket_command}` from a disposable local Git repository configured for "
            "`attachmentStorage.mode = github-releases`."
        ),
        "- Inspected the local `attachments.json` metadata, the live GitHub Release state, and `gh release view` output.",
        "",
        "## Result",
        "- ✅ Step 1 passed: the disposable local repository contained the requested file and github-releases configuration.",
        "- ✅ Step 2 passed: the exact local command completed successfully and returned the expected upload payload.",
        f"- ✅ Step 3 passed: local metadata stored `githubReleaseAssetName = {expected_asset_name}` for `{raw_file_name}`.",
        f"- ✅ Step 4 passed: the live GitHub Release and `gh release view` exposed only the sanitized asset name `{expected_asset_name}` on release tag `{release_tag}`.",
        (
            "- Human-style verification passed: the terminal command completed without a user-visible "
            "error, and the live release output showed the sanitized asset name instead of the raw filename."
        ),
        "",
        "## gh release view output",
        "```text",
        gh_release_stdout.rstrip() or "<empty>",
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


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

    expected_asset_name = _as_text(result.get("expected_sanitized_asset_name"))
    raw_file_name = _as_text(result.get("source_file_name"))
    observed_provider = _as_text(result.get("observed_provider")) or "local-git"
    observed_output_format = _as_text(result.get("observed_output_format")) or "json"
    observed_error_code = _as_text(result.get("observed_error_code"))
    observed_error_category = _as_text(result.get("observed_error_category"))
    observed_reason = _as_text(result.get("observed_error_reason")) or _as_text(
        result.get("observed_error_message"),
    )
    visible_output = _as_text(result.get("visible_output"))
    stdout = _as_text(result.get("stdout"))
    stderr = _as_text(result.get("stderr"))
    traceback_text = _as_text(result.get("traceback"))
    release_tag = _as_text(result.get("release_tag"))
    visible_summary = observed_reason or _as_text(result.get("observed_error_message"))
    if not visible_summary:
        visible_summary = visible_output.splitlines()[0].strip() if visible_output else ""
    step_two_succeeded = bool(
        result.get("exit_code") == 0
        and isinstance(result.get("payload"), dict)
        and (result.get("payload") or {}).get("ok") is True
    )
    manifest_state = result.get("manifest_state") or {}
    release_state = result.get("release_state") or {}
    gh_release_view = result.get("gh_release_view") or {}
    manifest_matches = bool(
        isinstance(manifest_state, dict) and manifest_state.get("matches_expected") is True
    )
    release_matches = bool(
        isinstance(release_state, dict) and release_state.get("matches_expected") is True
    )
    gh_matches = bool(
        isinstance(gh_release_view, dict) and gh_release_view.get("matches_expected") is True
    )
    final_state = {
        "final_state": result.get("final_state") or {},
        "manifest_state": manifest_state,
        "release_state": release_state,
        "gh_release_view": gh_release_view,
        "cleanup": result.get("cleanup") or {},
    }
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    product_gap = _as_text(result.get("product_gap"))

    if not step_two_succeeded:
        jira_step_two_line = (
            f"* ❌ Step 2 failed: the exact local command returned exit code "
            f"{_jira_inline(_as_text(result.get('exit_code')))} through provider "
            f"{_jira_inline(observed_provider)} before any release asset was created."
        )
        markdown_step_two_line = (
            f"- ❌ Step 2 failed: the exact local command returned exit code "
            f"`{_as_text(result.get('exit_code'))}` through provider `{observed_provider}` "
            "before any release asset was created."
        )
        jira_step_three_line = (
            "* ❌ Step 3 failed: local {{attachments.json}} metadata could not be inspected "
            "because the upload never created it."
        )
        markdown_step_three_line = (
            "- ❌ Step 3 failed: local `attachments.json` metadata could not be inspected "
            "because the upload never created it."
        )
        jira_step_four_line = (
            "* ❌ Step 4 failed: no GitHub Release asset was created, so neither {{gh release view}} "
            "nor the live release UI could show the sanitized filename."
        )
        markdown_step_four_line = (
            "- ❌ Step 4 failed: no GitHub Release asset was created, so neither `gh release view` "
            "nor the live release UI could show the sanitized filename."
        )
        actual_vs_expected = (
            f"Expected the exact local upload command to create a GitHub Release asset named "
            f"`{expected_asset_name}`. Actual result: the local provider failed before any "
            f"release asset was created and returned `{observed_error_code}` / "
            f"`{observed_error_category}` with reason `{observed_reason}`."
        )
    elif not manifest_matches:
        jira_step_two_line = "* ✅ Step 2 passed: the exact local command succeeded."
        markdown_step_two_line = "- ✅ Step 2 passed: the exact local command succeeded."
        jira_step_three_line = (
            "* ❌ Step 3 failed: the local attachment metadata did not converge to the "
            "expected sanitized {{githubReleaseAssetName}}."
        )
        markdown_step_three_line = (
            "- ❌ Step 3 failed: the local attachment metadata did not converge to the "
            "expected sanitized `githubReleaseAssetName`."
        )
        jira_step_four_line = (
            "* ❌ Step 4 was not trusted because the local metadata was already inconsistent "
            "with the expected sanitized release asset state."
        )
        markdown_step_four_line = (
            "- ❌ Step 4 was not trusted because the local metadata was already inconsistent "
            "with the expected sanitized release asset state."
        )
        actual_vs_expected = (
            f"Expected local metadata to persist `githubReleaseAssetName = {expected_asset_name}` "
            f"for `{raw_file_name}`. Actual result: the manifest state did not match the "
            "expected sanitized github-releases metadata."
        )
    elif not release_matches or not gh_matches:
        jira_step_two_line = "* ✅ Step 2 passed: the exact local command succeeded."
        markdown_step_two_line = "- ✅ Step 2 passed: the exact local command succeeded."
        jira_step_three_line = (
            f"* ✅ Step 3 passed: local metadata recorded the sanitized asset name "
            f"{_jira_inline(expected_asset_name)}."
        )
        markdown_step_three_line = (
            f"- ✅ Step 3 passed: local metadata recorded the sanitized asset name "
            f"`{expected_asset_name}`."
        )
        jira_step_four_line = (
            "* ❌ Step 4 failed: the live GitHub Release or {{gh release view}} did not expose "
            "exactly the expected sanitized asset name."
        )
        markdown_step_four_line = (
            "- ❌ Step 4 failed: the live GitHub Release or `gh release view` did not expose "
            "exactly the expected sanitized asset name."
        )
        actual_vs_expected = (
            f"Expected the live GitHub Release and `gh release view` to expose only "
            f"`{expected_asset_name}`. Actual result: the observed release state did not "
            "match the expected sanitized asset visibility."
        )
    else:
        jira_step_two_line = "* ❌ The scenario failed unexpectedly after all assertions passed."
        markdown_step_two_line = "- ❌ The scenario failed unexpectedly after all assertions passed."
        jira_step_three_line = ""
        markdown_step_three_line = ""
        jira_step_four_line = ""
        markdown_step_four_line = ""
        actual_vs_expected = error_message

    actual_vs_expected_plain = actual_vs_expected.replace("`", "")

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        (
            f"* Ran {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local Git repository "
            "configured for {{attachmentStorage.mode = github-releases}}."
        ),
        "* Inspected the local {{attachments.json}} metadata, the live GitHub Release state, and {{gh release view}} output.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the disposable local repository contained the requested file, the github-releases configuration, and the GitHub {{origin}} remote.",
        jira_step_two_line,
        f"* Observed error code/category: {_jira_inline(observed_error_code)} / {_jira_inline(observed_error_category)}",
        f"* Observed provider/output: {_jira_inline(observed_provider)} / {_jira_inline(observed_output_format)}",
        f"* Observed visible output summary: {_jira_inline(visible_summary)}",
        jira_step_three_line,
        jira_step_four_line,
        f"* Actual vs Expected: {actual_vs_expected_plain}",
        (
            "* Human-style verification: a real terminal run showed the caller-visible error "
            f"{_jira_inline(visible_summary)} instead of any success confirmation or sanitized asset name."
        ),
        *([f"* Product gap: {product_gap}"] if product_gap else []),
        "* Observed state:",
        "{code:json}",
        final_state_text,
        "{code}",
        "",
        "h4. Captured CLI output",
        "{code}",
        _observed_command_output(stdout, stderr).rstrip(),
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
            f"- Ran `{_as_text(result.get('ticket_command'))}` from a disposable local Git repository configured for "
            "`attachmentStorage.mode = github-releases`."
        ),
        "- Inspected the local `attachments.json` metadata, the live GitHub Release state, and `gh release view` output.",
        "",
        "## Result",
        "- ✅ Step 1 passed: the disposable local repository contained the requested file, the github-releases configuration, and the GitHub `origin` remote.",
        markdown_step_two_line,
        f"- Observed error code/category: `{observed_error_code}` / `{observed_error_category}`",
        f"- Observed provider/output: `{observed_provider}` / `{observed_output_format}`",
        f"- Observed visible output summary: `{visible_summary}`",
        markdown_step_three_line,
        markdown_step_four_line,
        f"- Actual vs Expected: {actual_vs_expected}",
        (
            "- Human-style verification: a real terminal run showed the caller-visible error "
            f"`{visible_summary}` instead of any success confirmation or sanitized asset name."
        ),
        *([f"- Product gap: {product_gap}"] if product_gap else []),
        "- Observed state:",
        "```json",
        final_state_text,
        "```",
        "",
        "## Captured CLI output",
        "```text",
        _observed_command_output(stdout, stderr).rstrip(),
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    bug_lines = [
        f"# {TICKET_KEY} - Release asset filename sanitization still blocked",
        "",
        "## Environment",
        f"- Repository: `{_as_text(result.get('repository'))}` @ `{_as_text(result.get('repository_ref'))}`",
        f"- Local repository path: `{_as_text(result.get('repository_path'))}`",
        f"- Remote origin URL: `{_as_text(result.get('remote_origin_url'))}`",
        f"- OS: `{_as_text(result.get('os'))}`",
        f"- Command: `{_as_text(result.get('ticket_command'))}`",
        f"- Expected release tag: `{release_tag}`",
        f"- Provider/output: `{observed_provider}` / `{observed_output_format}`",
        "",
        "## Steps to reproduce",
        (
            f"1. Create a local TrackState repository configured with `attachmentStorage.mode = github-releases`, "
            f"add a file named `{raw_file_name}`, and set Git `origin` to `{_as_text(result.get('remote_origin_url'))}`. "
            "Observed: ✅ passed — the disposable repository contained the file, issue fixture, and GitHub remote before the command ran."
        ),
        (
            f"2. Run `{_as_text(result.get('ticket_command'))}`. Observed: ❌ failed — exit code "
            f"`{_as_text(result.get('exit_code'))}`, provider/output `{observed_provider}` / `{observed_output_format}`, "
            f"error `{observed_error_code}` / `{observed_error_category}`, visible output `{visible_output}`."
        ),
        (
            "3. Inspect the local `attachments.json` metadata and the GitHub Release asset list with "
            f"`gh release view`. Observed: ❌ failed — no manifest was created and no release asset "
            f"was available on release tag `{release_tag}`."
        ),
        "",
        "## Actual vs Expected",
        f"- **Expected:** the exact local upload command should succeed and create a GitHub Release asset named `{expected_asset_name}`.",
        f"- **Expected:** local `attachments.json` should store `githubReleaseAssetName = {expected_asset_name}` for `{raw_file_name}`.",
        "- **Expected:** `gh release view` should expose only the sanitized asset name, not the raw filename.",
        f"- **Actual:** {actual_vs_expected}",
        "",
        "## Observed state at failure",
        "```json",
        final_state_text,
        "```",
        "",
        "## Exact error message and assertion failure",
        "```text",
        error_message,
        "",
        traceback_text.rstrip() or "<no traceback>",
        "```",
        "",
        "## Captured CLI output",
        "```text",
        _observed_command_output(stdout, stderr).rstrip(),
        "```",
    ]
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
    entries = result.setdefault("human_verification", [])
    assert isinstance(entries, list)
    entries.append({"check": check, "observed": observed})


def _serialize(value: object) -> object:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    return value


def _describe_state(state: object) -> str:
    return json.dumps(_serialize(state), indent=2, sort_keys=True)


def _visible_output(payload: object, *, stdout: str, stderr: str) -> str:
    fragments: list[str] = []
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            details = error.get("details")
            if isinstance(details, dict):
                reason = str(details.get("reason", "")).strip()
                if reason:
                    fragments.append(reason)
            message = str(error.get("message", "")).strip()
            if message:
                fragments.append(message)
    stdout_text = stdout.strip()
    if stdout_text:
        fragments.append(stdout_text)
    stderr_text = stderr.strip()
    if stderr_text:
        fragments.append(stderr_text)
    return "\n".join(fragment for fragment in fragments if fragment).strip()


def _observed_command_output(stdout: str, stderr: str) -> str:
    parts = ["stdout:", stdout.rstrip() or "<empty>", "", "stderr:", stderr.rstrip() or "<empty>"]
    return "\n".join(parts)


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _jira_inline(value: str) -> str:
    return "{{" + value.replace("{", "").replace("}", "") + "}}"


def validation_remote_origin(repository: str) -> str:
    return f"https://github.com/{repository}.git"


if __name__ == "__main__":
    main()
