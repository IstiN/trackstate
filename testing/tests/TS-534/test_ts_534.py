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
    as_text,
    jira_inline,
    observed_command_output,
)

TICKET_KEY = "TS-534"
TICKET_SUMMARY = "Release asset filename sanitization for local github-releases upload"
OUTPUTS_DIR = REPO_ROOT / "outputs"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-534/test_ts_534.py"
RUN_COMMAND = "python testing/tests/TS-534/test_ts_534.py"


class Ts534ReleaseAssetFilenameSanitizationScenario(
    TrackStateCliReleaseAssetFilenameSanitizationScenario,
):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-534",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )


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

    response_lines = [
        f"* Refactored `{TEST_FILE_PATH}` to use a dedicated probe, framework, validator, and support factory.",
        (
            f"* Test result: passed — the exact local upload command created the sanitized "
            f"release asset name `{as_text(result.get('expected_sanitized_asset_name'))}`."
        ),
    ]
    pr_lines = [
        "## TS-534 rework",
        "",
        "- Moved TS-534 execution behind a dedicated `core/interfaces` probe with framework and support-factory wiring.",
        "- Removed raw CLI/git/gh orchestration from the test entrypoint and kept the test focused on ticket assertions and reporting.",
        (
            f"- Result: ✅ passed — `{as_text(result.get('ticket_command'))}` produced the "
            f"sanitized release asset name `{as_text(result.get('expected_sanitized_asset_name'))}`."
        ),
    ]
    RESPONSE_PATH.write_text("\n".join(response_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(pr_lines) + "\n", encoding="utf-8")


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

    expected_asset_name = as_text(result.get("expected_sanitized_asset_name"))
    raw_file_name = as_text(result.get("source_file_name"))
    observed_provider = as_text(result.get("observed_provider")) or "local-git"
    observed_output_format = as_text(result.get("observed_output_format")) or "json"
    observed_error_code = as_text(result.get("observed_error_code"))
    observed_error_category = as_text(result.get("observed_error_category"))
    observed_reason = as_text(result.get("observed_error_reason")) or as_text(
        result.get("observed_error_message"),
    )
    stdout = as_text(result.get("stdout"))
    stderr = as_text(result.get("stderr"))
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

    if not step_two_succeeded:
        actual_vs_expected = (
            f"Expected the exact local upload command to create a GitHub Release asset named "
            f"`{expected_asset_name}`. Actual result: the local provider failed before any "
            f"release asset was created and returned `{observed_error_code}` / "
            f"`{observed_error_category}` with reason `{observed_reason}`."
        )
    elif not manifest_matches:
        actual_vs_expected = (
            f"Expected local metadata to persist `githubReleaseAssetName = {expected_asset_name}` "
            f"for `{raw_file_name}`. Actual result: the manifest state did not match the "
            "expected sanitized github-releases metadata."
        )
    elif not release_matches or not gh_matches:
        actual_vs_expected = (
            f"Expected the live GitHub Release and `gh release view` to expose only "
            f"`{expected_asset_name}`. Actual result: the observed release state did not "
            "match the expected sanitized asset visibility."
        )
    else:
        actual_vs_expected = error_message

    response_lines = [
        f"* Refactored `{TEST_FILE_PATH}` to use a dedicated probe, framework, validator, and support factory.",
        (
            f"* Test result: failed — `{as_text(result.get('ticket_command'))}` still does not "
            f"produce an observable sanitized release asset name for `{raw_file_name}`."
        ),
    ]
    pr_lines = [
        "## TS-534 rework",
        "",
        "- Moved TS-534 execution behind a dedicated `core/interfaces` probe with framework and support-factory wiring.",
        "- Extracted CLI compilation, local repo seeding, upload execution, manifest polling, release inspection, and `gh release view` calls out of the test entrypoint.",
        (
            f"- Result: ❌ failed — `{as_text(result.get('ticket_command'))}` still does not "
            f"create an observable sanitized release asset name `{expected_asset_name}`."
        ),
    ]
    RESPONSE_PATH.write_text("\n".join(response_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(pr_lines) + "\n", encoding="utf-8")

    bug_lines = [
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository: `{as_text(result.get('repository'))}` @ `{as_text(result.get('repository_ref'))}`",
        f"- Local repository path: `{as_text(result.get('repository_path'))}`",
        f"- Remote origin URL: `{as_text(result.get('remote_origin_url'))}`",
        f"- OS: `{as_text(result.get('os'))}`",
        f"- Command: `{as_text(result.get('ticket_command'))}`",
        f"- Expected release tag: `{as_text(result.get('release_tag'))}`",
        f"- Provider/output: `{observed_provider}` / `{observed_output_format}`",
        "",
        "## Steps to reproduce",
        (
            f"1. Create a local TrackState repository configured with "
            f"`attachmentStorage.mode = github-releases`, add a file named "
            f"`{raw_file_name}`, and set Git `origin` to `{as_text(result.get('remote_origin_url'))}`."
        ),
        f"2. Run `{as_text(result.get('ticket_command'))}`.",
        "3. Inspect the local `attachments.json` metadata and the GitHub Release asset list with `gh release view`.",
        "",
        "## Expected result",
        (
            f"- The exact local upload command should succeed and create a GitHub Release asset "
            f"named `{expected_asset_name}`."
        ),
        (
            f"- Local `attachments.json` should store `githubReleaseAssetName = {expected_asset_name}` "
            f"for `{raw_file_name}`."
        ),
        "- `gh release view` should expose only the sanitized asset name, not the raw filename.",
        "",
        "## Actual result",
        f"- {actual_vs_expected}",
        f"- Missing/broken production capability: {as_text(result.get('product_gap')) or actual_vs_expected}",
        f"- Observed state:\n```json\n{final_state_text}\n```",
        "",
        "## Failing command output",
        "```text",
        observed_command_output(stdout, stderr).rstrip(),
        "```",
    ]
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
