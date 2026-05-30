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


class Ts545LocalGithubReleasesUploadScenario(
    TrackStateCliReleaseAssetFilenameSanitizationScenario,
):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-545",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )


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

    ticket_command = as_text(result.get("ticket_command"))
    source_file_name = as_text(result.get("source_file_name"))
    expected_asset_name = as_text(result.get("expected_sanitized_asset_name"))
    release_tag = as_text(result.get("release_tag"))
    remote_origin_url = as_text(result.get("remote_origin_url"))
    visible = as_text(result.get("visible_output")) or "<empty>"
    summary_visible_output = compact_text(visible)
    manifest_state = as_dict(result.get("manifest_state"))
    gh_release_view = as_dict(result.get("gh_release_view"))
    matching_entry = json_inline(manifest_state.get("matching_entry"))
    gh_assets = ", ".join(
        str(asset) for asset in gh_release_view.get("asset_names", []) if str(asset)
    )
    gh_stdout = as_text(gh_release_view.get("stdout")).strip() or "<empty>"
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
            f"* Verified the command returned a successful JSON envelope for "
            f"{jira_inline(as_text(result.get('issue_key')))} without surfacing "
            f"{jira_inline('REPOSITORY_OPEN_FAILED')}."
        ),
        (
            f"* Verified local {jira_inline('attachments.json')} stored a release-backed "
            f"entry for {jira_inline(source_file_name)}."
        ),
        (
            f"* Verified the uploaded asset was visible in GitHub Release tag "
            f"{jira_inline(release_tag)} via {jira_inline('gh release view')}."
        ),
        "",
        "h4. Human-style verification",
        f"* Terminal outcome observed by a user: {jira_inline(summary_visible_output)}",
        f"* Release asset list observed by a user in {jira_inline('gh release view')}: {jira_inline(summary_gh_stdout)}",
        "",
        "h4. Result",
        "* Step 1 passed: the disposable local repository was created with the expected GitHub remote and upload file.",
        "* Step 2 passed: the exact local upload command succeeded and did not fail through the repository capability gate.",
        (
            f"* Step 3 passed: local {jira_inline('attachments.json')} converged to the "
            f"expected release-backed metadata for {jira_inline(source_file_name)}."
        ),
        (
            f"* Step 4 passed: the live GitHub Release exposed "
            f"{jira_inline(gh_assets or expected_asset_name)}."
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
            f"configured for `attachmentStorage.mode = github-releases` with Git origin "
            f"`{remote_origin_url}`."
        ),
        (
            f"- Verified the command returned a successful JSON envelope for "
            f"`{as_text(result.get('issue_key'))}` without surfacing "
            "`REPOSITORY_OPEN_FAILED`."
        ),
        (
            f"- Verified local `attachments.json` stored a release-backed entry for "
            f"`{source_file_name}`."
        ),
        (
            f"- Verified the uploaded asset was visible in GitHub Release `{release_tag}` "
            "via `gh release view`."
        ),
        "",
        "## Result",
        "- Step 1 passed: the disposable local repository was created with the expected GitHub remote and upload file.",
        "- Step 2 passed: the exact local upload command succeeded and did not fail through the repository capability gate.",
        (
            f"- Step 3 passed: local `attachments.json` converged to the expected "
            f"release-backed metadata for `{source_file_name}`. Matching entry: "
            f"`{matching_entry}`"
        ),
        (
            f"- Step 4 passed: the live GitHub Release exposed "
            f"`{gh_assets or expected_asset_name}`."
        ),
        f"- Human-style verification: terminal output `{summary_visible_output}`.",
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
    release_matches = release_state.get("matches_expected") is True
    gh_matches = gh_release_view.get("matches_expected") is True

    if not command_succeeded:
        failed_step = 2
        actual_vs_expected = (
            f"Expected `{ticket_command}` to upload `{source_file_name}` successfully "
            "without failing the local-git capability gate. Actual result: the command "
            f"failed with `{observed_error_code}` / `{observed_error_category}` through "
            f"provider `{observed_provider}` before the release-backed upload could be "
            "confirmed."
        )
        missing_capability = (
            "The production local github-releases upload path still fails before it "
            "permits the release-backed attachment operation through the local-git "
            "capability gate."
        )
        step2 = (
            f"2. ❌ Execute `{ticket_command}`. Observed: exit code "
            f"`{as_text(result.get('exit_code'))}`, provider/output "
            f"`{observed_provider}` / `{observed_output_format}`, visible output "
            f"`{summary_visible_output}`."
        )
        step3 = (
            "3. ❌ Inspect the local manifest and GitHub Release asset list. Observed: the "
            "command failed before release-backed metadata or asset visibility could be "
            "confirmed."
        )
    elif not manifest_matches:
        failed_step = 3
        actual_vs_expected = (
            f"Expected local `attachments.json` to store the release-backed entry for "
            f"`{source_file_name}` after `{ticket_command}` succeeded. Actual result: "
            "the upload returned success but the persisted manifest state did not match "
            "the expected release-backed metadata."
        )
        missing_capability = (
            "The production upload flow reports success but does not persist the expected "
            "release-backed attachment metadata to the local manifest."
        )
        step2 = (
            f"2. ✅ Execute `{ticket_command}`. Observed: the CLI returned success with "
            f"visible output `{summary_visible_output}`."
        )
        step3 = (
            "3. ❌ Inspect the local manifest and GitHub Release asset list. Observed: "
            f"`attachments.json` did not converge to the expected entry. Manifest state: "
            f"`{json_text(manifest_state)}`."
        )
    else:
        failed_step = 4
        actual_vs_expected = (
            f"Expected the live GitHub Release `{release_tag}` and `gh release view` to "
            f"show `{expected_asset_name}` after `{ticket_command}` succeeded. Actual "
            "result: the local upload and manifest state succeeded, but the live "
            "release-visible asset state did not match."
        )
        missing_capability = (
            "The production upload flow creates local success state but does not expose "
            "the uploaded asset through the expected GitHub Release visibility path."
        )
        step2 = (
            f"2. ✅ Execute `{ticket_command}`. Observed: the CLI returned success with "
            f"visible output `{summary_visible_output}`."
        )
        step3 = (
            "3. ✅ Inspect the local manifest. Observed: the manifest matched the expected "
            "release-backed entry."
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
            "1. Create a local TrackState repository configured with "
            f"`attachmentStorage.mode = github-releases`, add `{source_file_name}`, and set "
            f"Git `origin` to `{remote_origin_url}`."
        ),
        step2,
        (
            "4. Inspect the local `attachments.json` metadata and the GitHub Release asset "
            "list with `gh release view`."
        ),
        step3,
        "",
        "## Expected result",
        (
            f"- `{ticket_command}` succeeds without surfacing "
            "`REPOSITORY_OPEN_FAILED` or another capability-gate failure."
        ),
        (
            f"- Local `attachments.json` stores a release-backed entry for "
            f"`{source_file_name}`."
        ),
        (
            f"- The live GitHub Release `{release_tag}` and `gh release view` expose "
            f"`{expected_asset_name}`."
        ),
        "",
        "## Actual result",
        f"- {actual_vs_expected}",
        f"- Missing/broken production capability: {missing_capability}",
        f"- Observed state:\n```json\n{final_state_text}\n```",
        "",
        "## Exact error message or assertion failure",
        "```text",
        error_message,
        "",
        traceback_text.rstrip(),
        "```",
        "",
        "## Failing command/output",
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
