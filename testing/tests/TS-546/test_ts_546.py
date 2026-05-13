from __future__ import annotations

import importlib.util
import json
import platform
import sys
import traceback
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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


def _load_ts_534_module() -> ModuleType:
    module_path = REPO_ROOT / "testing/tests/TS-534/test_ts_534.py"
    spec = importlib.util.spec_from_file_location(
        "testing.tests.ts_534_shared",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load TS-534 helper module from {module_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TS534 = _load_ts_534_module()
TS534.TICKET_KEY = TICKET_KEY
TS534.TICKET_SUMMARY = TICKET_SUMMARY
TS534.TEST_FILE_PATH = TEST_FILE_PATH
TS534.RUN_COMMAND = RUN_COMMAND


class Ts546ReleaseAssetFilenameSanitizationScenario(
    TS534.Ts534ReleaseAssetFilenameSanitizationScenario,
):
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-546/config.yaml"
        self.config = (
            TS534.TrackStateCliReleaseAssetFilenameSanitizationConfig.from_file(
                self.config_path,
            )
        )
        self.validator = TS534.TrackStateCliReleaseAssetFilenameSanitizationValidator(
            probe=TS534.create_trackstate_cli_release_asset_filename_sanitization_probe(
                self.repository_root,
            ),
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

    expected_asset_name = _as_text(result.get("expected_sanitized_asset_name"))
    ticket_command = _as_text(result.get("ticket_command"))
    source_file_name = _as_text(result.get("source_file_name"))
    release_tag = _as_text(result.get("release_tag"))
    remote_origin_url = _as_text(result.get("remote_origin_url"))
    manifest_state = _dict(result.get("manifest_state"))
    gh_release_view = _dict(result.get("gh_release_view"))
    matching_entry = _json_inline(manifest_state.get("matching_entry"))
    gh_assets = ", ".join(
        str(asset) for asset in gh_release_view.get("asset_names", []) if str(asset)
    )
    visible_output = _as_text(result.get("visible_output")) or "<empty>"
    gh_stdout = _as_text(gh_release_view.get("stdout")).strip() or "<empty>"
    summary_visible_output = _compact_text(visible_output)
    summary_gh_stdout = _compact_text(gh_stdout)

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {_jira_inline(ticket_command)} from a disposable local TrackState "
            f"repository configured for {_jira_inline('attachmentStorage.mode = github-releases')} "
            f"with Git origin {_jira_inline(remote_origin_url)}."
        ),
        (
            f"* Verified local {_jira_inline('attachments.json')} persisted "
            f"{_jira_inline('githubReleaseAssetName = ' + expected_asset_name)} for "
            f"{_jira_inline(source_file_name)}."
        ),
        (
            f"* Verified the live GitHub Release {_jira_inline(release_tag)} through "
            f"{_jira_inline('gh release view')} and checked the user-visible asset name."
        ),
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the disposable local-git repository was seeded with the requested special-character file and github-releases storage configuration.",
        f"* ✅ Step 2 passed: the CLI upload succeeded. Visible output: {_jira_inline(summary_visible_output)}",
        f"* ✅ Step 3 passed: local metadata stored the sanitized asset name. Matching entry: {_jira_inline(matching_entry)}",
        f"* ✅ Step 4 passed: {_jira_inline('gh release view')} showed only {_jira_inline(gh_assets or expected_asset_name)}.",
        (
            "* Human-style verification passed: from a user's perspective the CLI finished "
            "successfully, the uploaded attachment remained associated with the original "
            "file, and the visible release asset name was sanitized instead of showing raw "
            "special characters."
        ),
        "",
        "h4. Human-style verification",
        f"* CLI-visible output: {_jira_inline(summary_visible_output)}",
        f"* {_jira_inline('gh release view')} output: {_jira_inline(summary_gh_stdout)}",
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

    ticket_command = _as_text(result.get("ticket_command"))
    source_file_name = _as_text(result.get("source_file_name"))
    expected_asset_name = _as_text(result.get("expected_sanitized_asset_name"))
    remote_origin_url = _as_text(result.get("remote_origin_url"))
    release_tag = _as_text(result.get("release_tag"))
    observed_provider = _as_text(result.get("observed_provider")) or "local-git"
    observed_output_format = _as_text(result.get("observed_output_format")) or "json"
    observed_error_code = _as_text(result.get("observed_error_code"))
    observed_error_category = _as_text(result.get("observed_error_category"))
    observed_reason = _as_text(result.get("observed_error_reason")) or _as_text(
        result.get("observed_error_message"),
    )
    visible_output = _as_text(result.get("visible_output")) or observed_reason
    stdout = _as_text(result.get("stdout"))
    stderr = _as_text(result.get("stderr"))
    traceback_text = _as_text(result.get("traceback"))
    summary_visible_output = _compact_text(visible_output)
    manifest_state = _dict(result.get("manifest_state"))
    release_state = _dict(result.get("release_state"))
    gh_release_view = _dict(result.get("gh_release_view"))
    cleanup_state = _dict(result.get("cleanup"))
    final_state = {
        "final_state": result.get("final_state") or {},
        "manifest_state": manifest_state,
        "release_state": release_state,
        "gh_release_view": gh_release_view,
        "cleanup": cleanup_state,
    }
    final_state_text = _json_text(final_state)
    observed_output = TS534._observed_command_output(stdout, stderr)

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
            f"Expected `{ticket_command}` to upload `{source_file_name}` successfully and "
            f"create a GitHub Release asset named `{expected_asset_name}`. Actual result: "
            f"the command failed with `{observed_error_code}` / `{observed_error_category}` "
            f"through provider `{observed_provider}` before the sanitized release asset "
            "could be observed."
        )
        step2 = (
            f"2. ❌ Execute `{ticket_command}`. Observed: exit code "
            f"`{_as_text(result.get('exit_code'))}`, provider/output "
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
            f"Manifest state: `{_json_text(manifest_state)}`."
        )
    else:
        failed_step = 3
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
            f"`{_json_text(release_state)}` and `gh release view` was "
            f"`{_json_text(gh_release_view)}`."
        )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was tested",
        (
            f"* Executed {_jira_inline(ticket_command)} from a disposable local TrackState "
            f"repository configured for {_jira_inline('attachmentStorage.mode = github-releases')} "
            f"with Git origin {_jira_inline(remote_origin_url)}."
        ),
        "* Checked the caller-visible CLI output, local attachment metadata, and live GitHub Release asset visibility.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the disposable local-git repository was seeded correctly.",
        f"* ❌ Step {failed_step} failed: {_jira_inline(actual_vs_expected)}",
        f"* Observed error code/category: {_jira_inline(observed_error_code)} / {_jira_inline(observed_error_category)}",
        f"* Observed provider/output: {_jira_inline(observed_provider)} / {_jira_inline(observed_output_format)}",
        f"* Observed visible output: {_jira_inline(summary_visible_output)}",
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
        f"- Repository: `{_as_text(result.get('repository'))}` @ `{_as_text(result.get('repository_ref'))}`",
        f"- Local repository path: `{_as_text(result.get('repository_path'))}`",
        f"- Remote origin URL: `{remote_origin_url}`",
        f"- OS: `{platform.system()}`",
        f"- Command: `{ticket_command}`",
        f"- Expected release tag: `{release_tag}`",
        f"- Provider/output: `{observed_provider}` / `{observed_output_format}`",
        "",
        "## Steps to reproduce",
        (
            f"1. ✅ Create a local TrackState repository configured with "
            f"`attachmentStorage.mode = github-releases`, add `{source_file_name}`, and set "
            f"Git `origin` to `{remote_origin_url}`. Observed: the seeded fixture contained "
            f"`{_as_text(result.get('issue_key'))}`, the source file existed, and the remote "
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


def _dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _json_text(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def _json_inline(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


def _compact_text(value: str) -> str:
    return " ".join(value.split())


def _jira_inline(value: str) -> str:
    return "{{" + value.replace("{", "").replace("}", "") + "}}"


if __name__ == "__main__":
    main()
