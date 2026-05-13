from __future__ import annotations

import json
import platform
import sys
import traceback
from dataclasses import asdict, is_dataclass
import hashlib
from pathlib import Path

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

TICKET_KEY = "TS-545"
TICKET_SUMMARY = (
    "Local github-releases upload succeeds when the local-git capability gate "
    "permits release-backed attachment operations"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-545/test_ts_545.py"
RUN_COMMAND = "python testing/tests/TS-545/test_ts_545.py"


class Ts545LocalGithubReleasesUploadScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-545/config.yaml"
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
                    "`attachmentStorage.mode = github-releases` with a valid GitHub "
                    "origin and a local `test-upload.txt` file."
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
            "expected_asset_name": self.config.expected_sanitized_asset_name,
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
                "Precondition failed: TS-545 did not execute the exact ticket command.\n"
                f"Expected command: {' '.join(self.config.requested_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-545 must run a repository-local compiled binary "
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
                "running TS-545.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if not initial_state.source_file_exists:
            failures.append(
                "Precondition failed: the seeded repository did not contain test-upload.txt "
                "before running TS-545.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.manifest_exists:
            failures.append(
                "Precondition failed: the seeded repository already contained attachments.json "
                "before the upload ran.\n"
                f"Observed state:\n{_describe_state(initial_state)}"
            )
        if initial_state.remote_origin_url != _expected_remote_origin(self.config.repository):
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
            observed_error_code = _as_text(result.get("observed_error_code"))
            if observed_error_code == "REPOSITORY_OPEN_FAILED":
                result["failure_mode"] = "capability_gate_still_closed"
                result["product_gap"] = (
                    "The production local-git github-releases upload path still fails at "
                    "the repository capability gate instead of delegating to GitHub "
                    "Releases and creating the remote asset."
                )
            else:
                result["failure_mode"] = "upload_failed"
                result["product_gap"] = (
                    "The production local-git github-releases upload command did not "
                    "complete successfully, so the release-backed upload contract is not "
                    "observable through the real CLI flow."
                )
            failures.append(
                "Step 2 failed: the exact local upload command returned a non-zero exit code.\n"
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

        if _as_text(result.get("observed_error_code")) == "REPOSITORY_OPEN_FAILED":
            failures.append(
                "Step 2 failed: the local upload command still surfaced "
                "`REPOSITORY_OPEN_FAILED` even though it exited successfully.\n"
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

        if attachment.get("name") != self.config.source_file_name:
            failures.append(
                "Step 2 failed: the success payload did not preserve the uploaded file name.\n"
                f"Observed payload:\n{json.dumps(payload, indent=2, sort_keys=True)}"
            )
            return failures, False

        result["failure_mode"] = "none"
        _record_step(
            result,
            step=2,
            status="passed",
            action=self.config.ticket_command,
            observed=(
                f"exit_code={observation.result.exit_code}; "
                f"provider={result.get('observed_provider')}; "
                f"issue={data.get('issue')}; "
                f"attachment_name={attachment.get('name')}; "
                f"attachment_revision_or_oid={attachment.get('revisionOrOid')}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified from a user-visible CLI perspective that the exact upload "
                "command completed successfully without surfacing "
                "`REPOSITORY_OPEN_FAILED`."
            ),
            observed=visible_output or "<empty>",
        )
        return failures, True

    def _validate_manifest(
        self,
        validation: TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        manifest = validation.manifest_observation
        matching_entry = manifest.matching_entry if manifest is not None else None
        if manifest is None or not manifest.manifest_exists or not isinstance(matching_entry, dict):
            failures.append(
                "Step 3 failed: the local attachments.json metadata did not converge to the "
                "expected release-backed upload entry for test-upload.txt.\n"
                f"Observed manifest state:\n{json.dumps(_serialize(manifest), indent=2, sort_keys=True)}"
            )
            return failures
        if str(matching_entry.get("storageBackend", "")) != "github-releases":
            failures.append(
                "Step 3 failed: the manifest entry did not preserve the "
                "`github-releases` storage backend.\n"
                f"Observed manifest state:\n{json.dumps(_serialize(manifest), indent=2, sort_keys=True)}"
            )
            return failures
        if str(matching_entry.get("githubReleaseTag", "")) != validation.expected_release_tag:
            failures.append(
                "Step 3 failed: the manifest entry did not point at the expected release tag.\n"
                f"Observed manifest state:\n{json.dumps(_serialize(manifest), indent=2, sort_keys=True)}"
            )
            return failures
        if str(matching_entry.get("githubReleaseAssetName", "")) != self.config.expected_sanitized_asset_name:
            failures.append(
                "Step 3 failed: the manifest entry did not record the uploaded asset name.\n"
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
                f"matching_entry={json.dumps(matching_entry, sort_keys=True)}"
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
        expected_sha256 = hashlib.sha256(self.config.source_file_bytes).hexdigest()
        if release is None or not release.release_present:
            failures.append(
                "Step 4 failed: the live GitHub Release did not expose the uploaded "
                "test-upload.txt asset as expected.\n"
                f"Observed release state:\n{json.dumps(_serialize(release), indent=2, sort_keys=True)}"
            )
            return failures
        if release.release_tag != validation.expected_release_tag:
            failures.append(
                "Step 4 failed: the observed GitHub Release tag did not match the upload fixture.\n"
                f"Observed release state:\n{json.dumps(_serialize(release), indent=2, sort_keys=True)}"
            )
            return failures
        if tuple(release.asset_names) != (self.config.expected_sanitized_asset_name,):
            failures.append(
                "Step 4 failed: the live GitHub Release did not expose exactly the expected uploaded asset name.\n"
                f"Observed release state:\n{json.dumps(_serialize(release), indent=2, sort_keys=True)}"
            )
            return failures
        if release.download_error:
            failures.append(
                "Step 4 failed: downloading the uploaded release asset for verification returned an error.\n"
                f"Observed release state:\n{json.dumps(_serialize(release), indent=2, sort_keys=True)}"
            )
            return failures
        if release.downloaded_asset_sha256 != expected_sha256:
            failures.append(
                "Step 4 failed: the uploaded release asset bytes did not match the local source file.\n"
                f"Observed release state:\n{json.dumps(_serialize(release), indent=2, sort_keys=True)}"
            )
            return failures
        if release.downloaded_asset_size_bytes != len(self.config.source_file_bytes):
            failures.append(
                "Step 4 failed: the uploaded release asset size did not match the local source file.\n"
                f"Observed release state:\n{json.dumps(_serialize(release), indent=2, sort_keys=True)}"
            )
            return failures
        if gh_view is None or gh_view.exit_code != 0:
            failures.append(
                "Step 4 failed: `gh release view` did not expose the uploaded asset "
                "test-upload.txt.\n"
                f"Observed gh release view:\n{json.dumps(_serialize(gh_view), indent=2, sort_keys=True)}"
            )
            return failures
        if tuple(gh_view.asset_names) != (self.config.expected_sanitized_asset_name,):
            failures.append(
                "Step 4 failed: `gh release view` did not list exactly the uploaded asset name.\n"
                f"Observed gh release view:\n{json.dumps(_serialize(gh_view), indent=2, sort_keys=True)}"
            )
            return failures

        _record_step(
            result,
            step=4,
            status="passed",
            action="Inspect the uploaded asset in the GitHub Release via `gh release view`.",
            observed=(
                f"release_tag={validation.expected_release_tag}; "
                f"asset_names={list(release.asset_names)}; "
                f"gh_release_assets={list(gh_view.asset_names)}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the uploaded asset was visible in the live GitHub Release "
                "listing exactly as a user would see it through `gh release view`."
            ),
            observed=gh_view.stdout.strip() or "<empty>",
        )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts545LocalGithubReleasesUploadScenario()

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

    visible_output = _as_text(result.get("visible_output"))
    asset_name = _as_text(result.get("expected_asset_name"))
    release_tag = _as_text(result.get("release_tag"))
    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured for {_jira_inline('attachmentStorage.mode = github-releases')} with Git origin {_jira_inline(_as_text(result.get('remote_origin_url')))}.",
        f"* Verified the command returned a successful JSON envelope for {_jira_inline(_as_text(result.get('issue_key')))} without surfacing {_jira_inline('REPOSITORY_OPEN_FAILED')}.",
        f"* Verified local {_jira_inline('attachments.json')} stored a release-backed entry for {_jira_inline(asset_name)}.",
        f"* Verified the uploaded asset was visible in GitHub Release tag {_jira_inline(release_tag)} via {_jira_inline('gh release view')}.",
        "",
        "h4. Human-style verification",
        "* Terminal outcome observed by a user:",
        "{code:json}",
        visible_output or "<empty>",
        "{code}",
        f"* Release asset list observed by a user in {_jira_inline('gh release view')}: {_jira_inline(_gh_assets_summary(result))}",
        "",
        "h4. Result",
        "* Step 1 passed: the disposable local repository was created with the expected GitHub remote and upload file.",
        "* Step 2 passed: the exact local upload command succeeded and did not fail through the repository capability gate.",
        f"* Step 3 passed: local {_jira_inline('attachments.json')} converged to the expected release-backed metadata for {_jira_inline(asset_name)}.",
        f"* Step 4 passed: the live GitHub Release exposed {_jira_inline(asset_name)} in {_jira_inline('gh release view')}.",
        "* The observed behavior matched the expected result.",
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
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured for `attachmentStorage.mode = github-releases` with Git origin `{_as_text(result.get('remote_origin_url'))}`.",
        f"- Verified the command returned a successful JSON envelope for `{_as_text(result.get('issue_key'))}` without surfacing `REPOSITORY_OPEN_FAILED`.",
        f"- Verified local `attachments.json` stored a release-backed entry for `{asset_name}`.",
        f"- Verified the uploaded asset was visible in GitHub Release tag `{release_tag}` via `gh release view`.",
        "",
        "## Human-style verification",
        "- Terminal outcome observed by a user:",
        "```json",
        visible_output or "<empty>",
        "```",
        f"- Release asset list observed by a user in `gh release view`: `{_gh_assets_summary(result)}`",
        "",
        "## Result",
        "- Step 1 passed: the disposable local repository was created with the expected GitHub remote and upload file.",
        "- Step 2 passed: the exact local upload command succeeded and did not fail through the repository capability gate.",
        f"- Step 3 passed: local `attachments.json` converged to the expected release-backed metadata for `{asset_name}`.",
        f"- Step 4 passed: the live GitHub Release exposed `{asset_name}` in `gh release view`.",
        "- The observed behavior matched the expected result.",
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

    asset_name = _as_text(result.get("expected_asset_name"))
    visible_output = _as_text(result.get("visible_output"))
    stdout = _as_text(result.get("stdout"))
    stderr = _as_text(result.get("stderr"))
    observed_provider = _as_text(result.get("observed_provider")) or "local-git"
    observed_output_format = _as_text(result.get("observed_output_format")) or "json"
    observed_error_code = _as_text(result.get("observed_error_code"))
    observed_error_category = _as_text(result.get("observed_error_category"))
    observed_reason = _as_text(result.get("observed_error_reason")) or _as_text(
        result.get("observed_error_message"),
    )
    manifest_state = result.get("manifest_state") or {}
    release_state = result.get("release_state") or {}
    gh_release_view = result.get("gh_release_view") or {}
    final_state = {
        "final_state": result.get("final_state") or {},
        "manifest_state": manifest_state,
        "release_state": release_state,
        "gh_release_view": gh_release_view,
        "cleanup": result.get("cleanup") or {},
    }
    final_state_text = json.dumps(final_state, indent=2, sort_keys=True)
    traceback_text = _as_text(result.get("traceback"))
    failure_mode = _as_text(result.get("failure_mode"))
    capability_gate_failed = failure_mode == "capability_gate_still_closed"

    step_one_observed = (
        "Disposable repository created with `attachmentStorage.mode = github-releases`, "
        f"local file `{_as_text(result.get('source_file_name'))}`, and Git origin "
        f"`{_as_text(result.get('remote_origin_url'))}`."
    )
    if _as_text(result.get("exit_code")):
        step_two_observed = (
            f"Command exited with `{_as_text(result.get('exit_code'))}`. "
            f"Provider/output: `{observed_provider}` / `{observed_output_format}`. "
            f"Visible output: `{visible_output or observed_reason or '<empty>'}`"
        )
    else:
        step_two_observed = (
            f"Command did not complete cleanly. Visible output: "
            f"`{visible_output or observed_reason or '<empty>'}`"
        )
    manifest_summary = json.dumps(manifest_state, indent=2, sort_keys=True)
    gh_summary = json.dumps(gh_release_view, indent=2, sort_keys=True)

    if capability_gate_failed:
        actual_vs_expected = (
            "Expected the local-git provider to permit the upload and create the remote "
            f"GitHub Release asset `{asset_name}`. Actual result: the command failed with "
            f"`{observed_error_code}` / `{observed_error_category}` and stopped at the "
            "repository capability gate before the release-backed upload completed."
        )
    else:
        actual_vs_expected = (
            "Expected the local-git provider to permit the upload and create the remote "
            f"GitHub Release asset `{asset_name}`. Actual result: the command did not "
            "produce the expected successful payload and observable release asset state."
        )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        f"* Executed {_jira_inline(_as_text(result.get('ticket_command')))} from a disposable local TrackState repository configured for {_jira_inline('attachmentStorage.mode = github-releases')} with Git origin {_jira_inline(_as_text(result.get('remote_origin_url')))}.",
        "* Inspected the caller-visible CLI output, local attachment metadata, and GitHub Release asset visibility.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the disposable repository and local upload file were created.",
        f"* ❌ Step 2 failed: the exact upload command did not complete as expected. Observed: {_jira_inline(step_two_observed)}",
        f"* {'❌' if manifest_state else '⚠️'} Step 3 {'failed' if manifest_state else 'could not be trusted'}: local {_jira_inline('attachments.json')} state = {_jira_inline(manifest_summary)}",
        f"* {'❌' if gh_release_view else '⚠️'} Step 4 {'failed' if gh_release_view else 'could not be trusted'}: {_jira_inline('gh release view')} state = {_jira_inline(gh_summary)}",
        f"* Actual vs Expected: {_jira_inline(actual_vs_expected)}",
        f"* Human-style verification observed terminal output {_jira_inline(visible_output or observed_reason or '<empty>')} and release asset summary {_jira_inline(_gh_assets_summary(result))}.",
        "",
        "h4. Error output",
        "{code}",
        _observed_command_output(stdout, stderr).rstrip(),
        "{code}",
    ]
    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        f"- Executed `{_as_text(result.get('ticket_command'))}` from a disposable local TrackState repository configured for `attachmentStorage.mode = github-releases` with Git origin `{_as_text(result.get('remote_origin_url'))}`.",
        "- Inspected the caller-visible CLI output, local attachment metadata, and GitHub Release asset visibility.",
        "",
        "## Result",
        "- Step 1 passed: the disposable repository and local upload file were created.",
        f"- Step 2 failed: the exact upload command did not complete as expected. Observed: `{step_two_observed}`",
        f"- Step 3 state: `{manifest_summary}`",
        f"- Step 4 state: `{gh_summary}`",
        f"- Actual vs Expected: `{actual_vs_expected}`",
        f"- Human-style verification observed terminal output `{visible_output or observed_reason or '<empty>'}` and release asset summary `{_gh_assets_summary(result)}`.",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")

    bug_lines = [
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository: `{_as_text(result.get('repository'))}` @ `{_as_text(result.get('repository_ref'))}`",
        f"- Local repository path: `{_as_text(result.get('repository_path'))}`",
        f"- Remote origin URL: `{_as_text(result.get('remote_origin_url'))}`",
        f"- OS: `{_as_text(result.get('os'))}`",
        f"- Command: `{_as_text(result.get('ticket_command'))}`",
        f"- Expected release tag: `{_as_text(result.get('release_tag'))}`",
        f"- Provider/output: `{observed_provider}` / `{observed_output_format}`",
        "",
        "## Steps to reproduce",
        (
            "1. Create a dummy local file named `test-upload.txt` in a local TrackState "
            "repository configured for `attachmentStorage.mode = github-releases` with a "
            f"valid GitHub `origin`. Observed: ✅ Passed. {step_one_observed}"
        ),
        (
            "2. Execute CLI command: "
            f"`{_as_text(result.get('ticket_command'))}`. Observed: ❌ Failed. "
            f"{step_two_observed}"
        ),
        (
            "3. Inspect the command output and exit code. Observed: ❌ Failed. "
            f"`{visible_output or observed_reason or '<empty>'}`"
        ),
        (
            "4. Verify the asset existence in the remote GitHub Release using `gh release view`. "
            f"Observed: {'✅ Passed.' if _gh_assets_summary(result) != '<unavailable>' else '❌ Failed.'} "
            f"`{_gh_assets_summary(result)}`"
        ),
        "",
        "## Actual vs Expected",
        f"- Expected: the command completes successfully without `REPOSITORY_OPEN_FAILED` and the asset `{asset_name}` is visible in the GitHub Release.",
        f"- Actual: {actual_vs_expected}",
        "",
        "## Exact error message / assertion failure",
        "```text",
        traceback_text.rstrip() or error_message,
        "```",
        "",
        "## Supporting state",
        "```json",
        final_state_text,
        "```",
        "",
        "## Command output",
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


def _expected_remote_origin(repository: str) -> str:
    return f"https://github.com/{repository}.git"


def _gh_assets_summary(result: dict[str, object]) -> str:
    gh_release_view = result.get("gh_release_view")
    if not isinstance(gh_release_view, dict):
        return "<unavailable>"
    asset_names = gh_release_view.get("asset_names")
    if not isinstance(asset_names, (list, tuple)):
        return "<unavailable>"
    if not asset_names:
        return "<none>"
    return ", ".join(str(name) for name in asset_names)


if __name__ == "__main__":
    main()
