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
TEST_FILE_PATH = "testing/tests/TS-684/test_ts_684.py"
RUN_COMMAND = "python testing/tests/TS-684/test_ts_684.py"
REQUEST_STEPS = [
    "Mock the GitHub API to return an HTTP 409 Conflict response for the release creation endpoint.",
    "Execute CLI command: `trackstate attachment upload --issue TS-101 --file test.pdf --target local`.",
    "Inspect the CLI error output.",
]
EXPECTED_ERROR_FRAGMENTS = (
    "Could not create GitHub release",
    "ts684-TS-101",
    "(409)",
    "Conflict",
    "tag already exists",
)
PROHIBITED_ERROR_FRAGMENTS = (
    "Validation Failed",
    "target_commitish",
    "422",
    "REPOSITORY_OPEN_FAILED",
)
EXPECTED_SEQUENCE = (
    "GET https://api.github.com/repos/IstiN/trackstate -> 200",
    "GET https://api.github.com/user -> 200",
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
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _build_failures(
    *,
    execution,
    payload: dict[str, object],
    result: dict[str, object],
) -> list[str]:
    failures: list[str] = []
    if not execution.succeeded:
        failures.append(
            "Step 1 failed: the TS-684 Dart probe did not analyze cleanly.\n"
            f"{execution.analyze_output}"
        )
        return failures

    if payload.get("status") != "passed":
        details = [str(payload.get("error") or "The TS-684 Dart probe reported a failure.")]
        stack_trace = payload.get("stackTrace")
        if stack_trace:
            details.append(str(stack_trace))
        failures.append("\n".join(details))
        return failures

    upload_outcome = _as_dict(payload.get("uploadOutcome"))
    request_sequence = _as_list_of_strings(payload.get("requestSequence"))
    release_create = _as_dict(payload.get("releaseCreate"))
    release_lookup = _as_dict(payload.get("releaseLookup"))
    release_asset_upload = _as_dict(payload.get("releaseAssetUpload"))
    metadata_write = _as_dict(payload.get("metadataWrite"))
    cached_attachment_count = int(payload.get("cachedAttachmentCount") or 0)
    cached_attachment_names = _as_list_of_strings(payload.get("cachedAttachmentNames"))

    result["upload_outcome"] = upload_outcome
    result["request_sequence"] = request_sequence
    result["release_create"] = release_create
    result["release_lookup"] = release_lookup
    result["release_asset_upload"] = release_asset_upload
    result["metadata_write"] = metadata_write
    result["cached_attachment_count"] = cached_attachment_count
    result["cached_attachment_names"] = cached_attachment_names

    if upload_outcome.get("status") != "error":
        failures.append(
            "Step 2 failed: the production attachment upload flow did not return a direct "
            "caller-visible failure after the mocked GitHub 409 release-creation response.\n"
            f"Observed upload outcome: {json.dumps(upload_outcome, indent=2, sort_keys=True)}"
        )
    else:
        message = _as_text(upload_outcome.get("message"))
        missing_fragments = [
            fragment for fragment in EXPECTED_ERROR_FRAGMENTS if fragment not in message
        ]
        present_prohibited = [
            fragment for fragment in PROHIBITED_ERROR_FRAGMENTS if fragment in message
        ]
        if missing_fragments:
            failures.append(
                "Step 3 failed: the caller-visible upload failure did not expose the "
                "expected release-creation conflict details.\n"
                f"Missing fragments: {missing_fragments}\n"
                f"Observed message: {message}"
            )
        if present_prohibited:
            failures.append(
                "Expected result failed: the release-creation conflict was misidentified "
                "as a validation/generic failure.\n"
                f"Unexpected fragments: {present_prohibited}\n"
                f"Observed message: {message}"
            )
        if not missing_fragments and not present_prohibited:
            _record_step(
                result,
                step=1,
                status="passed",
                action=REQUEST_STEPS[0],
                observed="Mocked release lookup returned 404 and release creation returned 409 Conflict.",
            )
            _record_step(
                result,
                step=2,
                status="passed",
                action=(
                    "Execute the production release-backed attachment upload flow for "
                    "`TS-101` with `test.pdf` using the same provider/repository path "
                    "the local CLI depends on."
                ),
                observed=message,
            )
            _record_human_verification(
                result,
                check=(
                    "Observed the caller-visible failure text a user/integrated client "
                    "would receive and confirmed it explicitly showed the 409 conflict "
                    "and `tag already exists` guidance."
                ),
                observed=message,
            )

    if not _contains_ordered_sequence(request_sequence, EXPECTED_SEQUENCE):
        failures.append(
            "Step 1 failed: the mocked GitHub request sequence did not exercise the "
            "expected release-creation conflict path.\n"
            f"Observed sequence: {request_sequence}"
        )
    else:
        _record_step(
            result,
            step=3,
            status="passed",
            action=(
                "Inspect the GitHub API traffic to confirm the provider reached the "
                "release creation endpoint and received the mocked 409 response."
            ),
            observed=" | ".join(request_sequence),
        )

    release_create_json = _as_dict(release_create.get("jsonBody"))
    if release_create_json.get("tag_name") != "ts684-TS-101":
        failures.append(
            "Expected result failed: the release-creation request targeted the wrong tag.\n"
            f"Observed request body: {json.dumps(release_create_json, indent=2, sort_keys=True)}"
        )
    if release_create_json.get("target_commitish") != "main":
        failures.append(
            "Expected result failed: the release-creation request targeted the wrong branch.\n"
            f"Observed request body: {json.dumps(release_create_json, indent=2, sort_keys=True)}"
        )
    if release_create_json.get("name") != "Attachments for TS-101":
        failures.append(
            "Expected result failed: the release-creation request used the wrong title.\n"
            f"Observed request body: {json.dumps(release_create_json, indent=2, sort_keys=True)}"
        )
    if release_create_json.get("draft") is not True:
        failures.append(
            "Expected result failed: the release-creation request should create a draft release.\n"
            f"Observed request body: {json.dumps(release_create_json, indent=2, sort_keys=True)}"
        )
    if release_create_json.get("prerelease") is not False:
        failures.append(
            "Expected result failed: the release-creation request should not mark the release as prerelease.\n"
            f"Observed request body: {json.dumps(release_create_json, indent=2, sort_keys=True)}"
        )

    if release_asset_upload:
        failures.append(
            "Expected result failed: the upload attempted a GitHub release asset POST even "
            "though release creation already failed with 409 Conflict.\n"
            f"Observed asset upload: {json.dumps(release_asset_upload, indent=2, sort_keys=True)}"
        )
    if metadata_write:
        failures.append(
            "Expected result failed: `attachments.json` was written even though release "
            "creation failed before any asset upload could succeed.\n"
            f"Observed metadata write: {json.dumps(metadata_write, indent=2, sort_keys=True)}"
        )
    if cached_attachment_count != 0 or cached_attachment_names:
        failures.append(
            "Expected result failed: the cached issue state mutated after the failed "
            "release-creation conflict.\n"
            f"Observed cached_attachment_count={cached_attachment_count}; "
            f"cached_attachment_names={cached_attachment_names}"
        )

    if not any(step.get("status") == "failed" for step in _as_list_of_dicts(result.get("steps"))):
        _record_human_verification(
            result,
            check=(
                "Verified the user-observable issue state stayed unchanged after the "
                "failure: no attachment appeared and no metadata write or asset upload "
                "was attempted."
            ),
            observed=(
                f"cached_attachment_count={cached_attachment_count}; "
                f"release_asset_upload_present={bool(release_asset_upload)}; "
                f"metadata_write_present={bool(metadata_write)}"
            ),
        )

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

    visible_error = _as_text(_as_dict(result.get("upload_outcome")).get("message"))
    request_sequence = _as_list_of_strings(result.get("request_sequence"))
    release_create_json = _as_dict(_as_dict(result.get("release_create")).get("jsonBody"))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ✅ PASSED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. What was automated",
        (
            "* Step 1: Mocked the GitHub release lookup/create API so "
            "{{GET /releases/tags/ts684-TS-101}} returned {{404}} and "
            "{{POST /releases}} returned {{409 Conflict}} with {{tag already exists}}."
        ),
        (
            "* Step 2: Ran the production release-backed attachment upload transaction "
            "for {{TS-101}} / {{test.pdf}} through the same provider-repository path "
            "used by clients when the local CLI triggers a github-releases upload."
        ),
        (
            "* Step 3: Verified the caller-visible failure text surfaced the conflict "
            "details instead of a {{422}} validation failure or generic repository error."
        ),
        "",
        "h4. Human-style verification",
        (
            f"* Observed the visible failure text exactly where the caller receives it: "
            f"{{code}}{visible_error}{{code}}"
        ),
        (
            "* Observed the issue state stayed unchanged after the failure: no attachment "
            "appeared, no release asset upload was attempted, and no {{attachments.json}} "
            "write occurred."
        ),
        "",
        "h4. Result",
        "* Step 1 passed: the mocked GitHub API returned the required 409 release-creation conflict.",
        "* Step 2 passed: the production upload flow attempted release creation with {{target_commitish = main}} for {{ts684-TS-101}}.",
        "* Step 3 passed: the visible failure contained {{409}}, {{Conflict}}, and {{tag already exists}} and did not contain {{422}}, {{Validation Failed}}, {{target_commitish}}, or {{REPOSITORY_OPEN_FAILED}}.",
        "* The observed behavior matched the expected result.",
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
        "- Mocked the GitHub release lookup/create API so `GET /releases/tags/ts684-TS-101` returned `404` and `POST /releases` returned `409 Conflict` with `tag already exists`.",
        "- Ran the production release-backed attachment upload transaction for `TS-101` / `test.pdf` through the same provider-repository path used by clients when the local CLI triggers a `github-releases` upload.",
        "- Verified the caller-visible failure text surfaced the conflict details instead of a `422` validation failure or generic repository error.",
        "",
        "## Human-style verification",
        f"- Observed the visible failure text a caller receives: `{visible_error}`.",
        "- Observed the issue state stayed unchanged after the failure: no attachment appeared, no release asset upload was attempted, and no `attachments.json` write occurred.",
        "",
        "## Result",
        "- Step 1 passed: the mocked GitHub API returned the required 409 release-creation conflict.",
        "- Step 2 passed: the production upload flow attempted release creation with `target_commitish = main` for `ts684-TS-101`.",
        "- Step 3 passed: the visible failure contained `409`, `Conflict`, and `tag already exists` and did not contain `422`, `Validation Failed`, `target_commitish`, or `REPOSITORY_OPEN_FAILED`.",
        "- The observed behavior matched the expected result.",
        "",
        "## Observed request sequence",
        "```text",
        "\n".join(request_sequence),
        "```",
        "",
        "## Release creation request body",
        "```json",
        json.dumps(release_create_json, indent=2, sort_keys=True),
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
        )
        + "\n",
        encoding="utf-8",
    )

    failure_summary = error_message or "The TS-684 automation failed."
    probe_run_output = _as_text(result.get("probe_run_output"))
    request_sequence = _as_list_of_strings(result.get("request_sequence"))
    visible_error = _as_text(_as_dict(result.get("upload_outcome")).get("message"))
    traceback_text = _as_text(result.get("traceback"))

    jira_lines = [
        "h3. Test Automation Result",
        "",
        "*Status:* ❌ FAILED",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "h4. Failure summary",
        f"* {failure_summary}",
        "",
        "h4. What was automated",
        "* Mocked the GitHub release-creation endpoint to return HTTP 409 Conflict.",
        "* Ran the production release-backed attachment upload transaction for TS-101 / test.pdf.",
        "* Inspected the caller-visible failure text and post-failure attachment state.",
        "",
        "h4. Observed output",
        "{code}",
        visible_error or probe_run_output or traceback_text,
        "{code}",
    ]
    if request_sequence:
        jira_lines.extend(
            [
                "",
                "h4. Observed request sequence",
                "{code}",
                "\n".join(request_sequence),
                "{code}",
            ]
        )

    markdown_lines = [
        "## Test Automation Result",
        "",
        "**Status:** ❌ FAILED",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## Failure summary",
        f"- {failure_summary}",
        "",
        "## What was automated",
        "- Mocked the GitHub release-creation endpoint to return HTTP 409 Conflict.",
        "- Ran the production release-backed attachment upload transaction for `TS-101` / `test.pdf`.",
        "- Inspected the caller-visible failure text and post-failure attachment state.",
        "",
        "## Observed output",
        "```text",
        visible_error or probe_run_output or traceback_text,
        "```",
    ]
    if request_sequence:
        markdown_lines.extend(
            [
                "",
                "## Observed request sequence",
                "```text",
                "\n".join(request_sequence),
                "```",
            ]
        )

    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")


def _build_bug_description(result: dict[str, object]) -> str:
    visible_error = _as_text(_as_dict(result.get("upload_outcome")).get("message"))
    request_sequence = _as_list_of_strings(result.get("request_sequence"))
    probe_run_output = _as_text(result.get("probe_run_output"))
    traceback_text = _as_text(result.get("traceback"))

    lines = [
        f"# {TICKET_KEY} - Release creation 409 conflict is not surfaced as the expected resource conflict",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Mock the GitHub API to return an HTTP 409 Conflict response for the release "
            "creation endpoint. "
            "Observed: the automated probe returned `404` for the release lookup and `409` for "
            "the release creation request."
        ),
        (
            "2. ❌ Execute CLI command: `trackstate attachment upload --issue TS-101 --file "
            "test.pdf --target local`. Observed: the automation reproduced the same production "
            "release-backed upload path through `ProviderBackedTrackStateRepository` with "
            "`GitHubTrackStateProvider`; the caller outcome was:\n"
            f"   `{visible_error or '<no visible error text captured>'}`"
        ),
        (
            "3. ❌ Inspect the CLI error output. Observed: the failure did not match the expected "
            "resource-conflict contract enforced by the automated assertions."
        ),
        "",
        "## Actual result",
        visible_error or probe_run_output or "<no run output captured>",
        "",
        "## Expected result",
        (
            "The error should explicitly indicate a resource conflict such as `tag already exists`, "
            "be visibly identifiable as `409 Conflict`, and must not be misidentified as a `422` "
            "validation failure or a generic `REPOSITORY_OPEN_FAILED` error."
        ),
        "",
        "## Exact assertion failure / stack trace",
        "```text",
        traceback_text or _as_text(result.get("error")),
        "```",
        "",
        "## Environment",
        f"- Repository: IstiN/trackstate",
        f"- Branch: main",
        f"- Issue: TS-101",
        f"- Attachment: test.pdf",
        f"- Release tag: ts684-TS-101",
        f"- OS: {result.get('os')}",
        f"- Test file: {TEST_FILE_PATH}",
        f"- Probe package: {REPO_ROOT / 'testing/tests/TS-684/dart_probe'}",
        "",
    ]

    if request_sequence:
        lines.extend(
            [
                "## Relevant logs",
                "```text",
                "\n".join(request_sequence),
                "```",
                "",
            ]
        )
    if probe_run_output:
        lines.extend(
            [
                "## Probe output",
                "```text",
                probe_run_output,
                "```",
            ]
        )

    return "\n".join(lines) + "\n"


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


def _as_list_of_dicts(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        return [_as_dict(item) for item in value]
    return []


def _as_text(value: object) -> str:
    return "" if value is None else str(value)


if __name__ == "__main__":
    main()
