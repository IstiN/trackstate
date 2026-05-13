from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.live_setup_repository_service import (  # noqa: E402
    LiveSetupRepositoryService,
)
from testing.components.services.trackstate_cli_release_draft_creation_probe import (  # noqa: E402
    TrackStateCliReleaseDraftCreationProbe,
)
from testing.components.services.trackstate_cli_release_asset_filename_sanitization_validator import (  # noqa: E402
    TrackStateCliReleaseAssetFilenameSanitizationValidator,
)
from testing.core.models.trackstate_cli_release_asset_filename_sanitization_result import (  # noqa: E402
    TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
)
from testing.tests.support.trackstate_cli_release_asset_filename_sanitization_scenario import (  # noqa: E402
    TrackStateCliReleaseAssetFilenameSanitizationScenario,
    as_dict,
    as_text,
    compact_text,
    jira_inline,
    json_inline,
    json_text,
    observed_command_output,
    record_human_verification,
    record_step,
    serialize,
    validation_remote_origin,
)

TICKET_KEY = "TS-554"
TICKET_SUMMARY = (
    "Local github-releases upload creates the missing draft release and tag"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-554/test_ts_554.py"
RUN_COMMAND = "python testing/tests/TS-554/test_ts_554.py"


class Ts554DraftReleaseCreationScenario(
    TrackStateCliReleaseAssetFilenameSanitizationScenario,
):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-554",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )
        self.release_probe = TrackStateCliReleaseDraftCreationProbe(
            REPO_ROOT,
            LiveSetupRepositoryService(),
        )
        self.validator = TrackStateCliReleaseAssetFilenameSanitizationValidator(
            probe=self.release_probe,
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []

        failures.extend(self._assert_exact_command(validation.observation))
        fixture_failures = self._assert_initial_fixture(validation.initial_state)
        failures.extend(fixture_failures)
        if not fixture_failures:
            record_step(
                result,
                step=1,
                status="passed",
                action=(
                    "Create a disposable local TrackState repository configured for "
                    "`attachmentStorage.mode = github-releases` with tag prefix "
                    "`ts-att-` and the exact `image.png` upload file."
                ),
                observed=(
                    f"issue_main_exists={validation.initial_state.issue_main_exists}; "
                    f"source_file_exists={validation.initial_state.source_file_exists}; "
                    f"remote_origin_url={validation.initial_state.remote_origin_url}; "
                    f"manifest_exists={validation.initial_state.manifest_exists}; "
                    f"pre_run_cleanup={json.dumps(self.release_probe.pre_run_cleanup, sort_keys=True)}"
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
        result = super()._build_result(validation)
        result["expected_release_title"] = f"Attachments for {self.config.issue_key}"
        result["pre_run_cleanup"] = self.release_probe.pre_run_cleanup
        return result

    def _assert_initial_fixture(self, initial_state) -> list[str]:
        failures = super()._assert_initial_fixture(initial_state)
        pre_run_cleanup = self.release_probe.pre_run_cleanup
        if pre_run_cleanup.get("release_present_after_cleanup") is True:
            failures.append(
                "Precondition failed: the remote release still existed after the pre-run "
                "cleanup step.\n"
                f"Observed cleanup: {json.dumps(pre_run_cleanup, indent=2, sort_keys=True)}"
            )
        if pre_run_cleanup.get("tag_refs_after_cleanup"):
            failures.append(
                "Precondition failed: the remote tag still existed after the pre-run "
                "cleanup step.\n"
                f"Observed cleanup: {json.dumps(pre_run_cleanup, indent=2, sort_keys=True)}"
            )
        return failures

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
                "expected release-backed entry for `image.png`.\n"
                f"Observed manifest state:\n{json.dumps(serialize(manifest), indent=2, sort_keys=True)}"
            )
            return failures

        record_step(
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
        expected_release_tag = validation.expected_release_tag
        expected_release_title = f"Attachments for {self.config.issue_key}"
        expected_asset_name = self.config.expected_sanitized_asset_name

        if release is None or not release.matches_expected:
            failures.append(
                "Step 4 failed: the remote GitHub Release did not expose the expected "
                "draft release container after upload.\n"
                f"Observed release state:\n{json.dumps(serialize(release), indent=2, sort_keys=True)}"
            )
            return failures

        gh_payload = gh_view.json_payload if gh_view is not None else None
        gh_name = (
            str(gh_payload.get("name", "")).strip()
            if isinstance(gh_payload, dict)
            else ""
        )
        gh_tag = (
            str(gh_payload.get("tagName", "")).strip()
            if isinstance(gh_payload, dict)
            else ""
        )
        gh_is_draft = (
            gh_payload.get("isDraft")
            if isinstance(gh_payload, dict)
            else None
        )
        if (
            gh_view is None
            or gh_view.exit_code != 0
            or gh_tag != expected_release_tag
            or gh_name != expected_release_title
            or gh_is_draft is not True
            or gh_view.asset_names != (expected_asset_name,)
        ):
            failures.append(
                "Step 4 failed: `gh release view` did not expose the expected draft release "
                "title, tag, and uploaded asset.\n"
                f"Observed gh release view:\n{json.dumps(serialize(gh_view), indent=2, sort_keys=True)}"
            )
            return failures

        record_step(
            result,
            step=4,
            status="passed",
            action="Verify the remote repository state via `gh release view ts-att-TS-456`.",
            observed=(
                f"release_tag={expected_release_tag}; "
                f"release_name={release.release_name}; "
                f"release_draft={release.release_draft}; "
                f"asset_names={list(release.asset_names)}; "
                f"gh_release_assets={list(gh_view.asset_names)}"
            ),
        )
        record_human_verification(
            result,
            check=(
                "Verified the user-visible `gh release view` output showed a draft release "
                "titled `Attachments for TS-456` containing the uploaded `image.png` asset."
            ),
            observed=gh_view.stdout.strip() or "<empty>",
        )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts554DraftReleaseCreationScenario()

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

    ticket_command = as_text(result.get("ticket_command"))
    issue_key = as_text(result.get("issue_key"))
    source_file_name = as_text(result.get("source_file_name"))
    release_tag = as_text(result.get("release_tag"))
    release_title = as_text(result.get("expected_release_title"))
    remote_origin_url = as_text(result.get("remote_origin_url"))
    payload = as_dict(result.get("payload"))
    manifest_state = as_dict(result.get("manifest_state"))
    gh_release_view = as_dict(result.get("gh_release_view"))
    gh_payload = as_dict(gh_release_view.get("json_payload"))
    pre_run_cleanup = as_dict(result.get("pre_run_cleanup"))
    matching_entry = json_inline(manifest_state.get("matching_entry"))
    gh_assets = ", ".join(
        str(asset) for asset in gh_release_view.get("asset_names", []) if str(asset)
    )
    payload_data = as_dict(payload.get("data"))
    payload_attachment = as_dict(payload_data.get("attachment"))
    summary_visible_output = (
        f"ok={payload.get('ok')}; issue={payload_data.get('issue')}; "
        f"attachment={payload_attachment.get('name')}; "
        f"mediaType={payload_attachment.get('mediaType')}; "
        f"sizeBytes={payload_attachment.get('sizeBytes')}"
    )
    summary_gh_stdout = (
        f"tag={gh_payload.get('tagName')}; name={gh_payload.get('name')}; "
        f"isDraft={gh_payload.get('isDraft')}; assets={gh_assets or source_file_name}"
    )
    pre_run_cleanup_summary = (
        f"release_before={pre_run_cleanup.get('release_present_before_cleanup')}; "
        f"tag_refs_before={len(pre_run_cleanup.get('tag_refs_before_cleanup', []))}; "
        f"release_after={pre_run_cleanup.get('release_present_after_cleanup')}; "
        f"tag_refs_after={len(pre_run_cleanup.get('tag_refs_after_cleanup', []))}"
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {jira_inline(ticket_command)} from a disposable local TrackState "
            f"repository configured for {jira_inline('attachmentStorage.mode = github-releases')} "
            f"with tag prefix {jira_inline('ts-att-')} and Git origin "
            f"{jira_inline(remote_origin_url)}."
        ),
        (
            f"* Verified the command returned a successful JSON envelope for "
            f"{jira_inline(issue_key)} and persisted a release-backed "
            f"{jira_inline('attachments.json')} entry for {jira_inline(source_file_name)}."
        ),
        (
            f"* Verified {jira_inline('gh release view ts-att-TS-456')} exposed a draft "
            f"release titled {jira_inline(release_title)} with uploaded asset "
            f"{jira_inline(source_file_name)}."
        ),
        "",
        "h4. Human-style verification",
        f"* Terminal outcome observed by a user: {jira_inline(summary_visible_output)}",
        (
            f"* Draft release output observed by a user in {jira_inline('gh release view')}: "
            f"{jira_inline(summary_gh_stdout)}"
        ),
        "",
        "h4. Result",
        (
            f"* Step 1 passed: the disposable local repository and remote release slot were "
            f"prepared for {jira_inline(release_tag)}. Pre-run cleanup: "
            f"{jira_inline(pre_run_cleanup_summary)}"
        ),
        "* Step 2 passed: the exact local upload command succeeded.",
        (
            f"* Step 3 passed: local {jira_inline('attachments.json')} converged to the "
            f"expected release-backed metadata. Matching entry: {jira_inline(matching_entry)}"
        ),
        (
            f"* Step 4 passed: the remote repository exposed draft release "
            f"{jira_inline(release_tag)} / {jira_inline(release_title)} with asset "
            f"{jira_inline(gh_assets or source_file_name)}."
        ),
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
        (
            f"- Executed `{ticket_command}` from a disposable local TrackState repository "
            f"configured for `attachmentStorage.mode = github-releases`, fixed tag prefix "
            f"`ts-att-`, and Git origin `{remote_origin_url}`."
        ),
        (
            f"- Verified the command returned a successful JSON envelope for `{issue_key}` "
            f"and persisted the release-backed `attachments.json` entry for `{source_file_name}`."
        ),
        (
            f"- Verified `gh release view ts-att-TS-456` exposed the draft release "
            f"`{release_title}` with asset `{source_file_name}`."
        ),
        "",
        "## Result",
        f"- Step 1 passed: the disposable local repository and remote release slot were prepared for `{release_tag}`.",
        "- Step 2 passed: the exact local upload command succeeded.",
        (
            f"- Step 3 passed: local `attachments.json` converged to the expected "
            f"release-backed metadata. Matching entry: `{matching_entry}`"
        ),
        (
            f"- Step 4 passed: the remote repository exposed draft release "
            f"`{release_tag}` / `{release_title}` with asset `{gh_assets or source_file_name}`."
        ),
        (
            f"- Human-style verification: terminal output `{summary_visible_output}` and "
            f"`gh release view` output `{summary_gh_stdout}`."
        ),
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
    error_message = as_text(result.get("error")) or "AssertionError: unknown failure"
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

    ticket_command = as_text(result.get("ticket_command"))
    issue_key = as_text(result.get("issue_key")) or "TS-456"
    source_file_name = as_text(result.get("source_file_name")) or "image.png"
    remote_origin_url = as_text(result.get("remote_origin_url"))
    release_tag = as_text(result.get("release_tag")) or "ts-att-TS-456"
    release_title = as_text(result.get("expected_release_title")) or "Attachments for TS-456"
    observed_provider = as_text(result.get("observed_provider")) or "local-git"
    observed_output_format = as_text(result.get("observed_output_format")) or "json"
    observed_error_code = as_text(result.get("observed_error_code"))
    observed_error_category = as_text(result.get("observed_error_category"))
    visible = as_text(result.get("visible_output")) or as_text(result.get("observed_error_message"))
    stdout = as_text(result.get("stdout"))
    stderr = as_text(result.get("stderr"))
    traceback_text = as_text(result.get("traceback"))
    summary_visible_output = compact_text(visible or "<empty>")
    manifest_state = as_dict(result.get("manifest_state"))
    release_state = as_dict(result.get("release_state"))
    gh_release_view = as_dict(result.get("gh_release_view"))
    pre_run_cleanup = result.get("pre_run_cleanup") or {}
    cleanup_state = as_dict(result.get("cleanup"))
    final_state = {
        "pre_run_cleanup": pre_run_cleanup,
        "final_state": result.get("final_state") or {},
        "manifest_state": manifest_state,
        "release_state": release_state,
        "gh_release_view": gh_release_view,
        "cleanup": cleanup_state,
    }
    final_state_text = json_text(final_state)
    observed_output = observed_command_output(stdout, stderr)

    command_succeeded = bool(
        result.get("exit_code") == 0
        and isinstance(result.get("payload"), dict)
        and (result.get("payload") or {}).get("ok") is True
    )
    manifest_matches = manifest_state.get("matches_expected") is True
    release_matches = release_state.get("matches_expected") is True
    gh_matches = (
        gh_release_view.get("exit_code") == 0
        and tuple(gh_release_view.get("asset_names", [])) == (source_file_name,)
        and as_dict(gh_release_view.get("json_payload")).get("tagName") == release_tag
        and as_dict(gh_release_view.get("json_payload")).get("name") == release_title
        and as_dict(gh_release_view.get("json_payload")).get("isDraft") is True
    )

    if not command_succeeded:
        failed_step = 1
        actual_vs_expected = (
            f"Expected `{ticket_command}` to succeed and create the missing draft release "
            f"`{release_tag}`. Actual result: the command failed with "
            f"`{observed_error_code}` / `{observed_error_category}` before release creation "
            "could be confirmed."
        )
        request_steps = [
            "1. ❌ Execute `trackstate attachment upload --issue TS-456 --file image.png --target local`. "
            f"Observed: exit code `{as_text(result.get('exit_code'))}`, provider/output "
            f"`{observed_provider}` / `{observed_output_format}`, visible output "
            f"`{summary_visible_output}`.",
            "2. ❌ Verify the remote repository state via `gh release view ts-att-TS-456`. "
            "Observed: the command failed before a release could be confirmed.",
        ]
    elif not manifest_matches:
        failed_step = 1
        actual_vs_expected = (
            f"Expected `{ticket_command}` to persist release-backed metadata for "
            f"`{source_file_name}` after succeeding. Actual result: the command reported "
            "success, but local `attachments.json` did not converge to the expected entry."
        )
        request_steps = [
            "1. ❌ Execute `trackstate attachment upload --issue TS-456 --file image.png --target local`. "
            "Observed: the CLI returned success, but local `attachments.json` did not match "
            f"the expected release-backed entry. Manifest state: `{json_text(manifest_state)}`.",
            "2. ❌ Verify the remote repository state via `gh release view ts-att-TS-456`. "
            "Observed: the local metadata mismatch blocked confirmation that the release "
            "container was created correctly.",
        ]
    elif not release_matches or not gh_matches:
        failed_step = 2
        actual_vs_expected = (
            f"Expected `gh release view {release_tag}` to show a draft release titled "
            f"`{release_title}` with asset `{source_file_name}` after `{ticket_command}` "
            "succeeded. Actual result: the remote release state did not match the expected "
            "tag/title/draft/asset contract."
        )
        request_steps = [
            "1. ✅ Execute `trackstate attachment upload --issue TS-456 --file image.png --target local`. "
            f"Observed: the CLI returned success with visible output `{summary_visible_output}`.",
            "2. ❌ Verify the remote repository state via `gh release view ts-att-TS-456`. "
            f"Observed release state: `{json_text({'release_state': release_state, 'gh_release_view': gh_release_view})}`.",
        ]
    else:
        failed_step = 1
        actual_vs_expected = error_message
        request_steps = [
            "1. ❌ Execute `trackstate attachment upload --issue TS-456 --file image.png --target local`. "
            f"Observed: `{summary_visible_output}`.",
            "2. ❌ Verify the remote repository state via `gh release view ts-att-TS-456`. "
            "Observed: could not complete verification because the scenario aborted.",
        ]

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {jira_inline(ticket_command)} from a disposable local TrackState "
            f"repository configured for {jira_inline('attachmentStorage.mode = github-releases')} "
            f"with tag prefix {jira_inline('ts-att-')} and Git origin "
            f"{jira_inline(remote_origin_url)}."
        ),
        "* Checked the caller-visible CLI output, local attachment metadata, and remote release state via `gh release view`.",
        "",
        "h4. Result",
        f"* ❌ Step {failed_step} failed: {jira_inline(actual_vs_expected)}",
        f"* Observed error code/category: {jira_inline(observed_error_code)} / {jira_inline(observed_error_category)}",
        f"* Observed provider/output: {jira_inline(observed_provider)} / {jira_inline(observed_output_format)}",
        f"* Observed visible output: {jira_inline(summary_visible_output)}",
        "",
        "h4. Ticket steps with observations",
        *request_steps,
        "",
        "h4. Observed state",
        "{code:json}",
        final_state_text,
        "{code}",
        "",
        "h4. Command output",
        "{code}",
        observed_output,
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
            f"- Executed `{ticket_command}` from a disposable local TrackState repository "
            f"configured for `attachmentStorage.mode = github-releases`, fixed tag prefix "
            f"`ts-att-`, and Git origin `{remote_origin_url}`."
        ),
        "- Checked the caller-visible CLI output, local attachment metadata, and remote release state via `gh release view`.",
        "",
        "## Result",
        f"- Failed at request step {failed_step}: {actual_vs_expected}",
        f"- Observed error code/category: `{observed_error_code}` / `{observed_error_category}`",
        f"- Observed provider/output: `{observed_provider}` / `{observed_output_format}`",
        f"- Observed visible output: `{summary_visible_output}`",
        "",
        "## Ticket steps with observations",
        *[f"- {step}" for step in request_steps],
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    bug_lines = [
        f"# Bug Report — {TICKET_KEY}",
        "",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        f"**Environment:** repository `{as_text(result.get('repository'))}`, ref `{as_text(result.get('repository_ref'))}`, remote origin `{remote_origin_url}`, OS `{as_text(result.get('os'))}`",
        "",
        "## Steps to reproduce",
        *request_steps,
        "",
        "## Actual vs Expected",
        f"- **Expected:** `{ticket_command}` succeeds, creates draft release `{release_tag}` titled `{release_title}`, and uploads `{source_file_name}`.",
        f"- **Actual:** {actual_vs_expected}",
        "",
        "## Exact error message / assertion failure",
        "```",
        error_message,
        "```",
        "",
        "## Stack trace",
        "```",
        traceback_text.strip() or "<empty>",
        "```",
        "",
        "## Relevant logs",
        "```",
        observed_output,
        "```",
        "",
        "## Observed state",
        "```json",
        final_state_text,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")
if __name__ == "__main__":
    main()
