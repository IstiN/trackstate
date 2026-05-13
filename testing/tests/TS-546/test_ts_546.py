from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.trackstate_cli_release_asset_filename_sanitization_scenario import (  # noqa: E402
    TrackStateCliReleaseAssetFilenameSanitizationScenario,
    as_dict,
    as_text,
    compact_text,
    jira_inline,
    json_inline,
    json_text,
    observed_command_output,
)

TICKET_KEY = "TS-546"
TICKET_SUMMARY = "Local upload sanitizes special-character filenames before creating GitHub Release assets"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-546/test_ts_546.py"
RUN_COMMAND = "python testing/tests/TS-546/test_ts_546.py"


class Ts546ReleaseAssetFilenameSanitizationScenario(
    TrackStateCliReleaseAssetFilenameSanitizationScenario,
):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-546",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts546ReleaseAssetFilenameSanitizationScenario()

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

    expected_asset_name = as_text(result.get("expected_sanitized_asset_name"))
    ticket_command = as_text(result.get("ticket_command"))
    source_file_name = as_text(result.get("source_file_name"))
    release_tag = as_text(result.get("release_tag"))
    remote_origin_url = as_text(result.get("remote_origin_url"))
    manifest_state = as_dict(result.get("manifest_state"))
    gh_release_view = as_dict(result.get("gh_release_view"))
    matching_entry = json_inline(manifest_state.get("matching_entry"))
    gh_assets = ", ".join(
        str(asset) for asset in gh_release_view.get("asset_names", []) if str(asset)
    )
    visible = as_text(result.get("visible_output")) or "<empty>"
    gh_stdout = as_text(gh_release_view.get("stdout")).strip() or "<empty>"
    summary_visible_output = compact_text(visible)
    summary_gh_stdout = compact_text(gh_stdout)

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
            f"with Git origin {jira_inline(remote_origin_url)}."
        ),
        (
            f"* Verified local {jira_inline('attachments.json')} persisted "
            f"{jira_inline('githubReleaseAssetName = ' + expected_asset_name)} for "
            f"{jira_inline(source_file_name)}."
        ),
        (
            f"* Verified the live GitHub Release {jira_inline(release_tag)} through "
            f"{jira_inline('gh release view')} and checked the user-visible asset name."
        ),
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the disposable local-git repository was seeded with the requested special-character file and github-releases storage configuration.",
        f"* ✅ Step 2 passed: the CLI upload succeeded. Visible output: {jira_inline(summary_visible_output)}",
        f"* ✅ Step 3 passed: local metadata stored the sanitized asset name. Matching entry: {jira_inline(matching_entry)}",
        f"* ✅ Step 4 passed: {jira_inline('gh release view')} showed only {jira_inline(gh_assets or expected_asset_name)}.",
        (
            "* Human-style verification passed: from a user's perspective the CLI finished "
            "successfully, the uploaded attachment remained associated with the original "
            "file, and the visible release asset name was sanitized instead of showing raw "
            "special characters."
        ),
        "",
        "h4. Human-style verification",
        f"* CLI-visible output: {jira_inline(summary_visible_output)}",
        f"* {jira_inline('gh release view')} output: {jira_inline(summary_gh_stdout)}",
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
            f"configured for `attachmentStorage.mode = github-releases` with Git origin "
            f"`{remote_origin_url}`."
        ),
        (
            f"- Verified local `attachments.json` persisted "
            f"`githubReleaseAssetName = {expected_asset_name}` for `{source_file_name}`."
        ),
        (
            f"- Verified the live GitHub Release `{release_tag}` via `gh release view` and "
            "checked the user-visible asset name."
        ),
        "",
        "## Result",
        "- ✅ Step 1 passed: the disposable local-git repository was seeded with the requested special-character file and github-releases storage configuration.",
        f"- ✅ Step 2 passed: the CLI upload succeeded. Visible output: `{summary_visible_output}`",
        f"- ✅ Step 3 passed: local metadata stored the sanitized asset name. Matching entry: `{matching_entry}`",
        f"- ✅ Step 4 passed: `gh release view` showed only `{gh_assets or expected_asset_name}`.",
        (
            "- Human-style verification passed: from a user's perspective the CLI finished "
            "successfully, the uploaded attachment remained associated with the original "
            "file, and the visible release asset name was sanitized instead of showing raw "
            "special characters."
        ),
        "",
        "## Human-style verification",
        f"- CLI-visible output: `{summary_visible_output}`",
        f"- `gh release view` output: `{summary_gh_stdout}`",
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
    source_file_name = as_text(result.get("source_file_name"))
    expected_asset_name = as_text(result.get("expected_sanitized_asset_name"))
    remote_origin_url = as_text(result.get("remote_origin_url"))
    release_tag = as_text(result.get("release_tag"))
    observed_provider = as_text(result.get("observed_provider")) or "local-git"
    observed_output_format = as_text(result.get("observed_output_format")) or "json"
    observed_error_code = as_text(result.get("observed_error_code"))
    observed_error_category = as_text(result.get("observed_error_category"))
    observed_reason = as_text(result.get("observed_error_reason")) or as_text(
        result.get("observed_error_message"),
    )
    visible = as_text(result.get("visible_output")) or observed_reason
    stdout = as_text(result.get("stdout"))
    stderr = as_text(result.get("stderr"))
    traceback_text = as_text(result.get("traceback"))
    summary_visible_output = compact_text(visible)
    manifest_state = as_dict(result.get("manifest_state"))
    release_state = as_dict(result.get("release_state"))
    gh_release_view = as_dict(result.get("gh_release_view"))
    cleanup_state = as_dict(result.get("cleanup"))
    final_state = {
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

    if not command_succeeded:
        failed_step = 2
        actual_vs_expected = (
            f"Expected `{ticket_command}` to upload `{source_file_name}` successfully and "
            f"create a GitHub Release asset named `{expected_asset_name}`. Actual result: "
            f"the command failed with `{observed_error_code}` / `{observed_error_category}` "
            f"through provider `{observed_provider}` before the sanitized release asset "
            "could be observed."
        )
        step2 = (
            f"2. ❌ Execute `{ticket_command}`. Observed: exit code "
            f"`{as_text(result.get('exit_code'))}`, provider/output "
            f"`{observed_provider}` / `{observed_output_format}`, visible output "
            f"`{summary_visible_output}`."
        )
        step3 = (
            "3. ❌ Inspect the local manifest and GitHub Release asset list. Observed: the "
            "command failed before the expected sanitized asset state could be confirmed."
        )
    elif not manifest_matches:
        failed_step = 3
        actual_vs_expected = (
            f"Expected local `attachments.json` to store "
            f"`githubReleaseAssetName = {expected_asset_name}` for `{source_file_name}`. "
            "Actual result: the upload returned success but the persisted manifest entry did "
            "not match the expected sanitized asset metadata."
        )
        step2 = (
            f"2. ✅ Execute `{ticket_command}`. Observed: the CLI returned success with visible "
            f"output `{summary_visible_output}`."
        )
        step3 = (
            "3. ❌ Inspect the local manifest and GitHub Release asset list. Observed: "
            f"`attachments.json` did not converge to the expected sanitized entry. "
            f"Manifest state: `{json_text(manifest_state)}`."
        )
    else:
        failed_step = 4
        actual_vs_expected = (
            f"Expected the live GitHub Release `{release_tag}` and `gh release view` to show "
            f"only `{expected_asset_name}`. Actual result: the local upload and manifest "
            "state succeeded, but the live release-visible asset state did not match."
        )
        step2 = (
            f"2. ✅ Execute `{ticket_command}`. Observed: the CLI returned success with visible "
            f"output `{summary_visible_output}`."
        )
        step3 = (
            "3. ❌ Inspect the local manifest and GitHub Release asset list. Observed: "
            f"manifest matched expected state, but release observation was "
            f"`{json_text(release_state)}` and `gh release view` was "
            f"`{json_text(gh_release_view)}`."
        )

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
            f"with Git origin {jira_inline(remote_origin_url)}."
        ),
        "* Checked the caller-visible CLI output, local attachment metadata, and live GitHub Release asset visibility.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the disposable local-git repository was seeded correctly.",
        f"* ❌ Step {failed_step} failed: {jira_inline(actual_vs_expected)}",
        f"* Observed error code/category: {jira_inline(observed_error_code)} / {jira_inline(observed_error_category)}",
        f"* Observed provider/output: {jira_inline(observed_provider)} / {jira_inline(observed_output_format)}",
        f"* Observed visible output: {jira_inline(summary_visible_output)}",
        (
            "* Human-style verification failed: from a user's perspective the release-backed "
            "upload flow did not expose the expected sanitized asset name in the final visible "
            "state."
        ),
        "",
        "h4. Observed state",
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
            f"- Executed `{ticket_command}` from a disposable local TrackState repository "
            f"configured for `attachmentStorage.mode = github-releases` with Git origin "
            f"`{remote_origin_url}`."
        ),
        "- Checked the caller-visible CLI output, local attachment metadata, and live GitHub Release asset visibility.",
        "",
        "## Result",
        "- ✅ Step 1 passed: the disposable local-git repository was seeded correctly.",
        f"- ❌ Step {failed_step} failed: {actual_vs_expected}",
        f"- Observed error code/category: `{observed_error_code}` / `{observed_error_category}`",
        f"- Observed provider/output: `{observed_provider}` / `{observed_output_format}`",
        f"- Observed visible output: `{summary_visible_output}`",
        (
            "- Human-style verification failed: from a user's perspective the release-backed "
            "upload flow did not expose the expected sanitized asset name in the final visible "
            "state."
        ),
        "",
        "## Observed state",
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
        f"- Repository: `{as_text(result.get('repository'))}` @ `{as_text(result.get('repository_ref'))}`",
        f"- Local repository path: `{as_text(result.get('repository_path'))}`",
        f"- Remote origin URL: `{remote_origin_url}`",
        f"- OS: `{as_text(result.get('os'))}`",
        f"- Command: `{ticket_command}`",
        f"- Expected release tag: `{release_tag}`",
        f"- Provider/output: `{observed_provider}` / `{observed_output_format}`",
        "",
        "## Steps to reproduce",
        (
            f"1. ✅ Create a local TrackState repository configured with "
            f"`attachmentStorage.mode = github-releases`, add `{source_file_name}`, and set "
            f"Git `origin` to `{remote_origin_url}`. Observed: the seeded fixture contained "
            f"`{as_text(result.get('issue_key'))}`, the source file existed, and the remote "
            "origin matched the hosted repository."
        ),
        step2,
        step3,
        "",
        "## Expected result",
        f"- The upload succeeds for `{source_file_name}`.",
        f"- Local `attachments.json` stores `githubReleaseAssetName = {expected_asset_name}`.",
        f"- The live GitHub Release `{release_tag}` and `gh release view` show the sanitized asset name `{expected_asset_name}`.",
        "",
        "## Actual result",
        f"- {actual_vs_expected}",
        f"- Visible output: `{summary_visible_output}`",
        f"- Observed state:\n```json\n{final_state_text}\n```",
        "",
        "## Exact error message or assertion failure",
        "```text",
        error_message,
        "",
        traceback_text.rstrip(),
        "```",
        "",
        "## Logs",
        "```text",
        observed_output,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
