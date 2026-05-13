from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.trackstate_cli_release_draft_creation_scenario import (  # noqa: E402
    TrackStateCliReleaseDraftCreationScenario,
    as_dict,
    as_text,
    compact_text,
    jira_inline,
    json_inline,
    json_text,
    observed_command_output,
)

TICKET_KEY = "TS-559"
TICKET_SUMMARY = (
    "Release resolution creates a machine-managed draft release for a new issue container"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-559/test_ts_559.py"
RUN_COMMAND = "python testing/tests/TS-559/test_ts_559.py"


class Ts559DraftReleaseCreationScenario(TrackStateCliReleaseDraftCreationScenario):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-559",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts559DraftReleaseCreationScenario()

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
            f"with tag prefix {jira_inline('ts559-assets-')} and Git origin "
            f"{jira_inline(remote_origin_url)}."
        ),
        (
            f"* Verified the command returned a successful JSON envelope for "
            f"{jira_inline(issue_key)} and persisted a release-backed "
            f"{jira_inline('attachments.json')} entry for {jira_inline(source_file_name)}."
        ),
        (
            f"* Verified {jira_inline('gh release view ts559-assets-TS-999')} exposed a "
            f"draft release titled {jira_inline(release_title)} with uploaded asset "
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
            f"configured for `attachmentStorage.mode = github-releases`, tag prefix "
            f"`ts559-assets-`, and Git origin `{remote_origin_url}`."
        ),
        (
            f"- Verified the command returned a successful JSON envelope for `{issue_key}` "
            f"and persisted the release-backed `attachments.json` entry for `{source_file_name}`."
        ),
        (
            f"- Verified `gh release view ts559-assets-TS-999` exposed the draft release "
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
    issue_key = as_text(result.get("issue_key")) or "TS-999"
    source_file_name = as_text(result.get("source_file_name")) or "setup.log"
    remote_origin_url = as_text(result.get("remote_origin_url"))
    release_tag = as_text(result.get("release_tag")) or "ts559-assets-TS-999"
    release_title = as_text(result.get("expected_release_title")) or "Attachments for TS-999"
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
            "1. ✅ Create a disposable local repository configured with `attachmentStorage.mode = github-releases`, a valid GitHub remote, and no existing release for `TS-999`. Observed: setup completed and the release slot was cleared before execution.",
            "2. ❌ Execute `trackstate attachment upload --issue TS-999 --file setup.log --target local`. "
            f"Observed: exit code `{as_text(result.get('exit_code'))}`, provider/output "
            f"`{observed_provider}` / `{observed_output_format}`, visible output "
            f"`{summary_visible_output}`.",
            "3. ❌ Inspect the GitHub repository releases. Observed: the command failed before a draft release could be confirmed.",
        ]
    elif not manifest_matches:
        failed_step = 2
        actual_vs_expected = (
            f"Expected `{ticket_command}` to persist release-backed metadata for "
            f"`{source_file_name}` after succeeding. Actual result: the command reported "
            "success, but local `attachments.json` did not converge to the expected entry."
        )
        request_steps = [
            "1. ✅ Create a disposable local repository configured with `attachmentStorage.mode = github-releases`, a valid GitHub remote, and no existing release for `TS-999`. Observed: setup completed and the release slot was cleared before execution.",
            "2. ✅ Execute `trackstate attachment upload --issue TS-999 --file setup.log --target local`. "
            f"Observed: the CLI returned success with visible output `{summary_visible_output}`.",
            "3. ❌ Inspect the GitHub repository releases and local attachment metadata. "
            "Observed: the draft release verification could not be trusted because local "
            f"`attachments.json` did not match the expected release-backed entry. Manifest state: `{json_text(manifest_state)}`.",
        ]
    elif not release_matches or not gh_matches:
        failed_step = 3
        actual_vs_expected = (
            f"Expected `gh release view {release_tag}` to show a draft release titled "
            f"`{release_title}` with asset `{source_file_name}` after `{ticket_command}` "
            "succeeded. Actual result: the remote release state did not match the expected "
            "tag/title/draft/asset contract."
        )
        request_steps = [
            "1. ✅ Create a disposable local repository configured with `attachmentStorage.mode = github-releases`, a valid GitHub remote, and no existing release for `TS-999`. Observed: setup completed and the release slot was cleared before execution.",
            "2. ✅ Execute `trackstate attachment upload --issue TS-999 --file setup.log --target local`. "
            f"Observed: the CLI returned success with visible output `{summary_visible_output}`.",
            "3. ❌ Inspect the GitHub repository releases. "
            f"Observed release state: `{json_text({'release_state': release_state, 'gh_release_view': gh_release_view})}`.",
        ]
    else:
        failed_step = 2
        actual_vs_expected = error_message
        request_steps = [
            "1. ✅ Create a disposable local repository configured with `attachmentStorage.mode = github-releases`, a valid GitHub remote, and no existing release for `TS-999`. Observed: setup completed and the release slot was cleared before execution.",
            "2. ❌ Execute `trackstate attachment upload --issue TS-999 --file setup.log --target local`. "
            f"Observed: `{summary_visible_output}`.",
            "3. ❌ Inspect the GitHub repository releases. Observed: could not complete verification because the scenario aborted.",
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
            f"with tag prefix {jira_inline('ts559-assets-')} and Git origin "
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
            f"configured for `attachmentStorage.mode = github-releases`, tag prefix "
            f"`ts559-assets-`, and Git origin `{remote_origin_url}`."
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
