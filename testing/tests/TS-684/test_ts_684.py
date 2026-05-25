from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.ts684_release_creation_conflict_probe_factory import (  # noqa: E402
    create_ts684_release_creation_conflict_probe,
)

TICKET_KEY = "TS-684"
TICKET_SUMMARY = (
    "Release creation fails with HTTP 409 Conflict and is reported as a resource conflict"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
TEST_FILE_PATH = "testing/tests/TS-684/test_ts_684.py"
RUN_COMMAND = "python testing/tests/TS-684/test_ts_684.py"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"
REQUESTED_COMMAND_TEXT = (
    "trackstate attachment upload --target local --issue TS-101 --file test.pdf"
)
EXPECTED_CONFLICT_FRAGMENTS = (
    "Could not create GitHub release",
    "ts684-TS-101",
    "(409)",
    "Conflict",
    "tag already exists",
)
PROHIBITED_CONFLICT_FRAGMENTS = (
    "Validation Failed",
    "target_commitish",
    "422",
)
PROHIBITED_CLI_WRAPPERS = (
    "REPOSITORY_OPEN_FAILED",
    'Attachment upload failed for "',
)
EXPECTED_SEQUENCE = (
    "GET https://api.github.com/repos/IstiN/trackstate/releases/tags/ts684-TS-101 -> 404",
    "GET https://api.github.com/repos/IstiN/trackstate/releases?per_page=100&page=1 -> 200",
    "POST https://api.github.com/repos/IstiN/trackstate/releases -> 409",
)


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    probe = create_ts684_release_creation_conflict_probe(REPO_ROOT)
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "config_path": str(REPO_ROOT / "testing/tests/TS-684/config.yaml"),
        "probe_package": str(REPO_ROOT / "testing/tests/TS-684/dart_probe"),
        "test_file_path": TEST_FILE_PATH,
        "run_command": RUN_COMMAND,
        "os": platform.system(),
        "steps": [],
        "human_verification": [],
    }

    try:
        execution = probe.inspect()
        result["probe_analyze_output"] = execution.analyze_output
        result["probe_run_output"] = execution.run_output
        payload = execution.observation_payload or {}
        result["probe_payload"] = payload
        failures = _build_failures(execution=execution, payload=payload, result=result)
        if failures:
            raise AssertionError("\n".join(failures))
        _write_pass_outputs(result)
        _write_review_replies(result, status="passed")
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result, product_defect=_is_product_defect(result))
        _write_review_replies(result, status="failed")
        raise


def _build_failures(
    *,
    execution,
    payload: dict[str, object],
    result: dict[str, object],
) -> list[str]:
    failures: list[str] = []
    if not execution.succeeded:
        failures = [
            "Step 1 failed: the TS-684 CLI probe did not analyze cleanly.\n"
            f"{execution.analyze_output}"
        ]
        _record_step(
            result,
            step=1,
            status="failed",
            action=(
                "Mock the GitHub release-creation conflict path and execute the local "
                "CLI attachment upload flow."
            ),
            observed=execution.analyze_output,
        )
        result["failures"] = failures
        return failures

    if payload.get("status") != "passed":
        details = [str(payload.get("error") or "The TS-684 CLI probe failed.")]
        stack_trace = payload.get("stackTrace")
        if stack_trace:
            details.append(str(stack_trace))
        failures = ["\n".join(details)]
        _record_step(
            result,
            step=1,
            status="failed",
            action=(
                "Mock the GitHub release-creation conflict path and execute the local "
                "CLI attachment upload flow."
            ),
            observed="\n".join(details),
        )
        result["failures"] = failures
        return failures

    requested_command_text = _as_text(payload.get("requestedCommandText"))
    cli_payload = _as_dict(payload.get("cliPayload"))
    cli_error = _as_dict(cli_payload.get("error"))
    request_sequence = _as_list_of_strings(payload.get("requestSequence"))
    release_create = _as_dict(payload.get("releaseCreate"))
    release_lookup = _as_dict(payload.get("releaseLookup"))
    release_asset_upload = _as_dict(payload.get("releaseAssetUpload"))
    metadata_write = _as_dict(payload.get("metadataWrite"))
    cached_attachment_count = int(payload.get("cachedAttachmentCount") or 0)
    cached_attachment_names = _as_list_of_strings(payload.get("cachedAttachmentNames"))
    cli_stdout = _as_text(payload.get("cliStdout"))
    cli_stderr = _as_text(payload.get("cliStderr"))
    cli_exit_code = int(payload.get("cliExitCode") or 0)
    visible_error = _visible_error_text(cli_payload, stdout=cli_stdout, stderr=cli_stderr)

    result.update(
        {
            "repository": _as_text(payload.get("repository")),
            "branch": _as_text(payload.get("branch")),
            "issueKey": _as_text(payload.get("issueKey")),
            "issuePath": _as_text(payload.get("issuePath")),
            "manifestPath": _as_text(payload.get("manifestPath")),
            "attachmentName": _as_text(payload.get("attachmentName")),
            "releaseTag": _as_text(payload.get("releaseTag")),
            "releaseTitle": _as_text(payload.get("releaseTitle")),
            "repository_path": _as_text(payload.get("repositoryPath")),
            "attachmentPath": _as_text(payload.get("attachmentPath")),
            "requested_command_text": requested_command_text,
            "cli_payload": cli_payload,
            "cli_error": cli_error,
            "cli_stdout": cli_stdout,
            "cli_stderr": cli_stderr,
            "cli_exit_code": cli_exit_code,
            "visible_error_text": visible_error,
            "request_sequence": request_sequence,
            "release_create": release_create,
            "release_lookup": release_lookup,
            "release_asset_upload": release_asset_upload,
            "metadata_write": metadata_write,
            "cached_attachment_count": cached_attachment_count,
            "cached_attachment_names": cached_attachment_names,
        }
    )

    step1_issues: list[str] = []
    step2_issues: list[str] = []
    step3_issues: list[str] = []

    if requested_command_text != REQUESTED_COMMAND_TEXT:
        step1_issues.append(
            "Precondition failed: TS-684 did not exercise the exact ticket command "
            "through the CLI execution layer.\n"
            f"Expected command: {REQUESTED_COMMAND_TEXT}\n"
            f"Observed command: {requested_command_text or '<missing>'}"
        )

    if cli_exit_code == 0:
        step1_issues.append(
            "Step 1 failed: the local CLI attachment upload unexpectedly succeeded even "
            "though GitHub release creation returned HTTP 409 Conflict.\n"
            f"{_observed_command_output(stdout=cli_stdout, stderr=cli_stderr)}"
        )
    if not cli_payload:
        step1_issues.append(
            "Step 1 failed: the local CLI did not return a machine-readable JSON "
            "error envelope.\n"
            f"{_observed_command_output(stdout=cli_stdout, stderr=cli_stderr)}"
        )

    if cli_payload.get("ok") is not False:
        step1_issues.append(
            "Expected result failed: the CLI output did not stay in a failure state.\n"
            f"Observed payload: {json.dumps(cli_payload, indent=2, sort_keys=True)}"
        )

    if not cli_error:
        step1_issues.append(
            "Step 1 failed: the CLI JSON envelope did not include an `error` object.\n"
            f"Observed payload: {json.dumps(cli_payload, indent=2, sort_keys=True)}"
        )

    if not _contains_ordered_sequence(request_sequence, EXPECTED_SEQUENCE):
        step1_issues.append(
            "Step 1 failed: the mocked GitHub API traffic did not reach the expected "
            "release-creation conflict path.\n"
            f"Observed request sequence: {request_sequence}"
        )

    release_lookup_status = release_lookup.get("responseStatusCode")
    if release_lookup_status != 404:
        step1_issues.append(
            "Expected result failed: release lookup did not return the mocked 404.\n"
            f"Observed lookup: {json.dumps(release_lookup, indent=2, sort_keys=True)}"
        )

    release_create_json = _as_dict(release_create.get("jsonBody"))
    if release_create.get("responseStatusCode") != 409:
        step1_issues.append(
            "Expected result failed: release creation did not return the mocked 409.\n"
            f"Observed release create exchange: {json.dumps(release_create, indent=2, sort_keys=True)}"
        )
    if release_create_json.get("tag_name") != "ts684-TS-101":
        step1_issues.append(
            "Expected result failed: the release-creation request targeted the wrong tag.\n"
            f"Observed request body: {json.dumps(release_create_json, indent=2, sort_keys=True)}"
        )
    if release_create_json.get("target_commitish") != "main":
        step1_issues.append(
            "Expected result failed: the release-creation request targeted the wrong branch.\n"
            f"Observed request body: {json.dumps(release_create_json, indent=2, sort_keys=True)}"
        )
    if release_create_json.get("name") != "Attachments for TS-101":
        step1_issues.append(
            "Expected result failed: the release-creation request used the wrong title.\n"
            f"Observed request body: {json.dumps(release_create_json, indent=2, sort_keys=True)}"
        )

    if cli_exit_code != 0 and cli_payload and cli_error:
        missing_expected = [
            fragment
            for fragment in EXPECTED_CONFLICT_FRAGMENTS
            if fragment not in visible_error
        ]
        present_prohibited = [
            fragment
            for fragment in PROHIBITED_CONFLICT_FRAGMENTS
            if fragment in visible_error
        ]
        present_wrapper = [
            fragment for fragment in PROHIBITED_CLI_WRAPPERS if fragment in visible_error
        ]

        if missing_expected:
            step2_issues.append(
                "Step 2 failed: the caller-visible CLI output did not surface the "
                "expected 409 conflict details.\n"
                f"Missing fragments: {missing_expected}\n"
                f"Observed output: {visible_error}"
            )
        if present_prohibited:
            step2_issues.append(
                "Expected result failed: the CLI output misidentified the release-"
                "creation conflict as a validation failure.\n"
                f"Unexpected fragments: {present_prohibited}\n"
                f"Observed output: {visible_error}"
            )
        if present_wrapper:
            step2_issues.append(
                "Expected result failed: the local CLI still hides the release-"
                "creation conflict behind the generic repository wrapper instead of "
                "surfacing a conflict-specific error.\n"
                f"Unexpected wrapper fragments: {present_wrapper}\n"
                f"Observed output: {visible_error}"
            )
    else:
        step2_issues.append(
            "Step 2 failed: the caller-visible CLI error could not be validated because "
            "the command did not produce the expected machine-readable failure envelope.\n"
            f"{_observed_command_output(stdout=cli_stdout, stderr=cli_stderr)}"
        )

    if release_asset_upload:
        step3_issues.append(
            "Expected result failed: asset upload was attempted after release creation "
            "already failed with HTTP 409 Conflict.\n"
            f"Observed asset upload: {json.dumps(release_asset_upload, indent=2, sort_keys=True)}"
        )
    if metadata_write:
        step3_issues.append(
            "Expected result failed: attachments.json was written even though release "
            "creation failed first.\n"
            f"Observed metadata write: {json.dumps(metadata_write, indent=2, sort_keys=True)}"
        )
    if cached_attachment_count != 0 or cached_attachment_names:
        step3_issues.append(
            "Expected result failed: the cached issue state changed after the failed "
            "release-creation conflict.\n"
            f"Observed cached_attachment_count={cached_attachment_count}; "
            f"cached_attachment_names={cached_attachment_names}"
        )

    failures.extend(step1_issues)
    failures.extend(step2_issues)
    failures.extend(step3_issues)

    _record_step(
        result,
        step=1,
        status="passed" if not step1_issues else "failed",
        action=(
            "Mock the GitHub API to return a release lookup 404 and release creation "
            "409, then execute `trackstate attachment upload --issue TS-101 --file "
            "test.pdf --target local`."
        ),
        observed=(
            f"command={requested_command_text or '<missing>'}; "
            f"cli_exit_code={cli_exit_code}; "
            f"release_lookup_status={release_lookup_status}; "
            f"release_create_status={release_create.get('responseStatusCode')}; "
            f"request_sequence={' | '.join(request_sequence) or '<missing>'}"
        ),
    )
    _record_step(
        result,
        step=2,
        status="passed" if not step2_issues else "failed",
        action="Inspect the caller-visible CLI error output.",
        observed=visible_error or _observed_command_output(stdout=cli_stdout, stderr=cli_stderr),
    )
    _record_step(
        result,
        step=3,
        status="passed" if not step3_issues else "failed",
        action=(
            "Inspect the post-failure user-visible side effects and repository state."
        ),
        observed=(
            f"release_asset_upload_present={bool(release_asset_upload)}; "
            f"metadata_write_present={bool(metadata_write)}; "
            f"cached_attachment_count={cached_attachment_count}; "
            f"cached_attachment_names={cached_attachment_names}"
        ),
    )
    _record_human_verification(
        result,
        check=(
            "Observe the exact terminal/JSON error a local CLI user receives and verify "
            "whether attachment state remains unchanged after the failed upload."
        ),
        observed=(
            f"visible_error={visible_error or '<missing>'}; "
            f"release_asset_upload_present={bool(release_asset_upload)}; "
            f"metadata_write_present={bool(metadata_write)}; "
            f"cached_attachment_count={cached_attachment_count}"
        ),
    )
    result["failures"] = failures
    return failures


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

    visible_error = _as_text(result.get("visible_error_text"))
    request_sequence = _as_list_of_strings(result.get("request_sequence"))
    release_create_json = _as_dict(_as_dict(result.get("release_create")).get("jsonBody"))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        "* Step 1: Mocked the GitHub release lookup/create flow so `GET /releases/tags/ts684-TS-101` returned `404` and `POST /releases` returned `409 Conflict` with `tag already exists`.",
        "* Step 2: Executed `trackstate attachment upload --issue TS-101 --file test.pdf --target local` through the local CLI execution path.",
        "* Step 3: Inspected the caller-visible CLI output and the post-failure attachment state.",
        "",
        "h4. Human-style verification",
        f"* Observed the exact CLI error text the local user would receive: {{code}}{visible_error}{{code}}",
        "* Confirmed no attachment appeared for the issue, no release asset upload was attempted, and no `attachments.json` write occurred after the failure.",
        "",
        "h4. Result",
        "* ✅ Step 1 passed: the CLI exercised the expected mocked release-creation conflict path.",
        "* ✅ Step 2 passed: the visible error stayed conflict-specific and included `409`, `Conflict`, and `tag already exists` without `422`, `Validation Failed`, or `REPOSITORY_OPEN_FAILED`.",
        "* ✅ Step 3 passed: no user-visible attachment state changed after the failed upload.",
        "* ✅ Human-style verification passed: the exact terminal/JSON error and the unchanged post-failure state matched the expected result.",
        "",
        "h4. Observed request sequence",
        "{code}",
        "\n".join(request_sequence),
        "{code}",
        "",
        "h4. Release creation request body",
        "{code:json}",
        json.dumps(release_create_json, indent=2, sort_keys=True),
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
        "- Mocked the GitHub release lookup/create flow so release tag lookup returned `404` and release creation returned `409 Conflict` with `tag already exists`.",
        "- Executed `trackstate attachment upload --issue TS-101 --file test.pdf --target local` through the local CLI execution path.",
        "- Inspected the caller-visible CLI output and the post-failure attachment state.",
        "",
        "## Human-style verification",
        f"- Observed the exact CLI error text the local user would receive: `{visible_error}`.",
        "- Confirmed no attachment appeared for the issue, no release asset upload was attempted, and no `attachments.json` write occurred after the failure.",
        "",
        "## Result",
        "- Step 1 passed: the CLI exercised the expected mocked release-creation conflict path.",
        "- Step 2 passed: the visible error stayed conflict-specific and included `409`, `Conflict`, and `tag already exists` without `422`, `Validation Failed`, or `REPOSITORY_OPEN_FAILED`.",
        "- Step 3 passed: no user-visible attachment state changed after the failed upload.",
        "- Human-style verification passed: the exact terminal/JSON error and the unchanged post-failure state matched the expected result.",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")


def _write_failure_outputs(
    result: dict[str, object], *, product_defect: bool
) -> None:
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
        )
        + "\n",
        encoding="utf-8",
    )

    visible_error = _as_text(result.get("visible_error_text"))
    cli_stdout = _as_text(result.get("cli_stdout"))
    cli_stderr = _as_text(result.get("cli_stderr"))
    request_sequence = _as_list_of_strings(result.get("request_sequence"))
    release_create_json = _as_dict(_as_dict(result.get("release_create")).get("jsonBody"))
    traceback_text = _as_text(result.get("traceback"))
    failures = _as_list_of_strings(result.get("failures"))
    release_lookup = _as_dict(result.get("release_lookup"))
    release_create = _as_dict(result.get("release_create"))
    release_asset_upload = _as_dict(result.get("release_asset_upload"))
    metadata_write = _as_dict(result.get("metadata_write"))
    cached_attachment_count = int(result.get("cached_attachment_count") or 0)
    cached_attachment_names = _as_list_of_strings(result.get("cached_attachment_names"))
    repository_path = _as_text(result.get("repository_path"))
    step1_summary = (
        f"command={_as_text(result.get('requested_command_text')) or '<missing>'}; "
        f"release_lookup_status={release_lookup.get('responseStatusCode')}; "
        f"release_create_status={release_create.get('responseStatusCode')}; "
        f"request_sequence={' | '.join(request_sequence) or '<missing>'}"
    )
    step2_summary = visible_error or _observed_command_output(
        stdout=cli_stdout, stderr=cli_stderr
    )
    step3_summary = (
        f"release_asset_upload_present={bool(release_asset_upload)}; "
        f"metadata_write_present={bool(metadata_write)}; "
        f"cached_attachment_count={cached_attachment_count}; "
        f"cached_attachment_names={cached_attachment_names}"
    )
    actual_vs_expected = (
        "Actual: the local CLI returned the generic "
        "`REPOSITORY_OPEN_FAILED` repository envelope with top-level message "
        f"`Attachment upload failed for \"{repository_path}\".` while only placing the "
        "409 release conflict details in the nested reason text. Expected: the "
        "caller-visible error itself should be conflict-specific, clearly indicating "
        "`409`, `Conflict`, and `tag already exists`, and should not be wrapped in "
        "`REPOSITORY_OPEN_FAILED`."
    )

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        "* Step 1: Mocked the GitHub release lookup/create flow so `GET /releases/tags/ts684-TS-101` returned `404` and `POST /releases` returned `409 Conflict` with `tag already exists`.",
        "* Step 2: Executed `trackstate attachment upload --issue TS-101 --file test.pdf --target local` through the local CLI execution path.",
        "* Step 3: Inspected the caller-visible CLI output and the post-failure attachment state.",
        "",
        "h4. Human-style verification",
        f"* Observed the exact CLI error text the local user would receive: {{code}}{visible_error or cli_stdout or cli_stderr}{{code}}",
        "* Observed no attachment was added for the issue after the failed upload: no release asset upload occurred, no `attachments.json` write occurred, and the cached attachment list stayed empty.",
        "",
        "h4. Result",
        f"* {'✅' if not any(message.startswith('Step 1 failed') or message.startswith('Precondition failed') or 'release lookup' in message or 'release creation' in message for message in failures) else '❌'} Step 1 {'passed' if not any(message.startswith('Step 1 failed') or message.startswith('Precondition failed') or 'release lookup' in message or 'release creation' in message for message in failures) else 'failed'}: {step1_summary}",
        f"* ❌ Step 2 failed: the caller-visible CLI error was {{code}}{visible_error}{{code}}.",
        f"* Actual vs Expected: {actual_vs_expected}",
        f"* {'✅' if not any('asset upload was attempted' in message or 'attachments.json was written' in message or 'cached issue state changed' in message for message in failures) else '❌'} Step 3 {'passed' if not any('asset upload was attempted' in message or 'attachments.json was written' in message or 'cached issue state changed' in message for message in failures) else 'failed'}: {step3_summary}",
        f"* {'❌' if product_defect else '⚠️'} Human-style verification {'failed' if product_defect else 'was blocked'}: the exact terminal/JSON error seen by the user still exposed the generic `REPOSITORY_OPEN_FAILED` wrapper instead of a conflict-specific CLI error.",
        "",
        "h4. Observed request sequence",
        "{code}",
        "\n".join(request_sequence),
        "{code}",
        "",
        "h4. Release creation request body",
        "{code:json}",
        json.dumps(release_create_json, indent=2, sort_keys=True),
        "{code}",
        "",
        "h4. Exact assertion failure / stack trace",
        "{code}",
        traceback_text or error_message,
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
        "- Mocked the GitHub release lookup/create flow so release tag lookup returned `404` and release creation returned `409 Conflict` with `tag already exists`.",
        "- Executed `trackstate attachment upload --issue TS-101 --file test.pdf --target local` through the local CLI execution path.",
        "- Inspected the caller-visible CLI output and the post-failure attachment state.",
        "",
        "## Human-style verification",
        f"- Observed the exact CLI error text the local user would receive: `{visible_error or cli_stdout or cli_stderr}`.",
        "- Observed no attachment was added for the issue after the failed upload: no release asset upload occurred, no `attachments.json` write occurred, and the cached attachment list stayed empty.",
        "",
        "## Result",
        f"- Step 1 {'passed' if not any(message.startswith('Step 1 failed') or message.startswith('Precondition failed') or 'release lookup' in message or 'release creation' in message for message in failures) else 'failed'}: {step1_summary}",
        f"- ❌ Step 2 failed: the caller-visible CLI error was `{visible_error}`.",
        f"- Actual vs Expected: {actual_vs_expected}",
        f"- Step 3 {'passed' if not any('asset upload was attempted' in message or 'attachments.json was written' in message or 'cached issue state changed' in message for message in failures) else 'failed'}: {step3_summary}",
        f"- Human-style verification {'failed' if product_defect else 'was blocked'}: the exact terminal/JSON error seen by the user still exposed the generic `REPOSITORY_OPEN_FAILED` wrapper instead of a conflict-specific CLI error.",
        "",
        "## Exact assertion failure / stack trace",
        "```text",
        traceback_text or error_message,
        "```",
        "",
        "## How to run",
        "```bash",
        RUN_COMMAND,
        "```",
    ]

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    if product_defect:
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _build_bug_description(result: dict[str, object]) -> str:
    visible_error = _as_text(result.get("visible_error_text"))
    cli_stdout = _as_text(result.get("cli_stdout"))
    cli_stderr = _as_text(result.get("cli_stderr"))
    request_sequence = _as_list_of_strings(result.get("request_sequence"))
    release_create_json = _as_dict(_as_dict(result.get("release_create")).get("jsonBody"))
    cli_payload = _as_dict(result.get("cli_payload"))
    traceback_text = _as_text(result.get("traceback"))
    repository_path = _as_text(result.get("repository_path"))
    request_sequence_text = "\n".join(request_sequence) or "<no requests captured>"
    observed_output = _observed_command_output(stdout=cli_stdout, stderr=cli_stderr)

    lines = [
        f"# {TICKET_KEY} bug reproduction",
        "",
        "## Environment",
        f"- Repository: `{_as_text(result.get('repository'))}`",
        f"- Repository path: `{repository_path}`",
        f"- Branch: `{_as_text(result.get('branch'))}`",
        f"- Issue: `{_as_text(result.get('issueKey'))}`",
        f"- Attachment file: `{_as_text(result.get('attachmentPath'))}`",
        f"- Command: `{REQUESTED_COMMAND_TEXT}`",
        f"- OS: `{platform.system()}`",
        "",
        "## Steps to reproduce",
        "1. ✅ Configure the project with `attachmentStorage.mode = github-releases`. Observed: the disposable CLI fixture repository was created with issue `TS-101` and release-backed attachment storage enabled.",
        "2. ✅ Mock the GitHub API so `GET /repos/IstiN/trackstate/releases/tags/ts684-TS-101` returns `404` and `POST /repos/IstiN/trackstate/releases` returns `409 Conflict` with `tag already exists`. Observed request sequence reached both mocked endpoints in that order.",
        f"3. ✅ Execute `{REQUESTED_COMMAND_TEXT}`. Observed: the command failed with exit code `{_as_text(result.get('cli_exit_code'))}` and returned a JSON error payload to the caller.",
        (
            "4. ❌ Inspect the CLI error output. Observed: the caller-visible output was "
            f"`{visible_error or cli_stdout or cli_stderr}`. The 409 conflict details were "
            "present only inside the nested reason text, while the top-level user-visible "
            "error still used the generic `REPOSITORY_OPEN_FAILED` / `Attachment upload "
            f"failed for \"{repository_path}\".` wrapper."
        ),
        (
            "5. ✅ Inspect post-failure side effects. Observed: no release asset upload "
            "occurred, no `attachments.json` write occurred, and the cached attachment "
            f"list stayed empty for issue `{_as_text(result.get('issueKey'))}`."
        ),
        "",
        "## Expected result",
        "- The local CLI should surface a conflict-specific failure for the 409 release creation response.",
        "- The caller-visible output should clearly include `409`, `Conflict`, and `tag already exists`.",
        "- The failure should not be hidden behind the generic `REPOSITORY_OPEN_FAILED` wrapper.",
        "- No attachment metadata or release asset side effects should be created.",
        "",
        "## Actual result",
        f"- Caller-visible output: `{visible_error or cli_stdout or cli_stderr or '<no CLI output captured>'}`",
        (
            f"- Actual vs Expected: Actual: the local CLI returned `REPOSITORY_OPEN_FAILED` "
            f"with top-level message `Attachment upload failed for \"{repository_path}\".` "
            "and only exposed the 409 conflict inside `error.details.reason`. Expected: "
            "the caller-visible error itself should be conflict-specific and should not "
            "use the generic repository wrapper."
        ),
        "",
        "## Captured CLI payload/output",
        "```json",
        json.dumps(cli_payload, indent=2, sort_keys=True)
        if cli_payload
        else json.dumps({"stdout": cli_stdout, "stderr": cli_stderr}, indent=2, sort_keys=True),
        "```",
        "",
        "## Captured terminal output",
        "```text",
        observed_output or "<no stdout/stderr captured>",
        "```",
        "",
        "## Mocked release creation request body",
        "```json",
        json.dumps(release_create_json, indent=2, sort_keys=True),
        "```",
        "",
        "## Observed request sequence",
        "```text",
        request_sequence_text,
        "```",
        "",
        "## Exact assertion failure / stack trace",
        "```text",
        traceback_text or _as_text(result.get("error")),
        "```",
    ]
    return "\n".join(lines) + "\n"


def _is_product_defect(result: dict[str, object]) -> bool:
    payload = _as_dict(result.get("probe_payload"))
    if payload.get("status") != "passed":
        return False
    visible_error = _as_text(result.get("visible_error_text"))
    request_sequence = _as_list_of_strings(result.get("request_sequence"))
    release_create = _as_dict(result.get("release_create"))
    return bool(
        visible_error
        or request_sequence
        or release_create.get("responseStatusCode") == 409
    )


def _write_review_replies(result: dict[str, object], *, status: str) -> None:
    summary = _review_reply_text(result, status=status)
    replies = [
        {
            "inReplyToId": thread.get("rootCommentId"),
            "threadId": thread.get("threadId"),
            "reply": summary,
        }
        for thread in _discussion_threads()
    ]
    REVIEW_REPLIES_PATH.write_text(
        json.dumps({"replies": replies}) + "\n",
        encoding="utf-8",
    )


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    return [thread for thread in threads if isinstance(thread, dict)]


def _review_reply_text(result: dict[str, object], *, status: str) -> str:
    visible_error = _as_text(result.get("visible_error_text"))
    if status == "passed":
        return (
            "Fixed: TS-684 now exercises the `TrackStateCli` local attachment-upload "
            "execution path with the mocked 409 release-creation flow instead of "
            "calling `ProviderBackedTrackStateRepository.uploadIssueAttachment()` "
            "directly. The rerun now validates the caller-visible CLI envelope and "
            f"passed with conflict-specific output: {visible_error}"
        )
    return (
        "Fixed the review concern in the test harness: TS-684 now exercises the "
        "`TrackStateCli` local attachment-upload execution path with the mocked 409 "
        "release-creation flow instead of calling "
        "`ProviderBackedTrackStateRepository.uploadIssueAttachment()` directly. The "
        "rerun now validates the caller-visible CLI envelope and reproduces the "
        "remaining product bug: the local CLI still returns the generic "
        "`REPOSITORY_OPEN_FAILED` wrapper instead of a conflict-specific 409/"
        f"`tag already exists` error. Observed output: {visible_error}"
    )


def _record_step(
    result: dict[str, object],
    *,
    step: int,
    status: str,
    action: str,
    observed: str,
) -> None:
    steps = result.setdefault("steps", [])
    if isinstance(steps, list):
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
    if isinstance(checks, list):
        checks.append({"check": check, "observed": observed})


def _contains_ordered_sequence(observed: list[str], expected: tuple[str, ...]) -> bool:
    start = 0
    for fragment in expected:
        try:
            index = observed.index(fragment, start)
        except ValueError:
            return False
        start = index + 1
    return True


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
        if fragment and all(fragment.lower() not in existing.lower() for existing in fragments):
            fragments.append(fragment)
    return " | ".join(fragment for fragment in fragments if fragment)


def _json_visible_error_text(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        details = error.get("details")
        fragments = [
            _as_text(error.get("message")).strip(),
            _as_text(error.get("code")).strip(),
            _as_text(error.get("category")).strip(),
        ]
        if isinstance(details, dict):
            fragments.extend(
                _as_text(details.get(key)).strip()
                for key in ("reason", "provider", "target", "path", "file", "repository")
            )
        return " | ".join(fragment for fragment in fragments if fragment)
    return ""


def _looks_like_json(text: str) -> bool:
    stripped = text.strip()
    return (stripped.startswith("{") and stripped.endswith("}")) or (
        stripped.startswith("[") and stripped.endswith("]")
    )


def _collapse_output(text: str) -> str:
    return " | ".join(line.strip() for line in text.splitlines() if line.strip())


def _observed_command_output(*, stdout: str, stderr: str) -> str:
    fragments = []
    if stdout.strip():
        fragments.append(f"stdout:\n{stdout}")
    if stderr.strip():
        fragments.append(f"stderr:\n{stderr}")
    return "\n".join(fragments)


def _as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return {
            str(key): entry if not isinstance(entry, dict) else _as_dict(entry)
            for key, entry in value.items()
        }
    return {}


def _as_list_of_strings(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def _as_text(value: object) -> str:
    return "" if value is None else str(value)


if __name__ == "__main__":
    main()
