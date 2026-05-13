from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.ts505_github_release_upload_failure_probe_factory import (  # noqa: E402
    create_ts505_github_release_upload_failure_probe,
)

TICKET_KEY = "TS-505"
ISSUE_KEY = "DEMO-2"
ISSUE_PATH = "DEMO/DEMO-1/DEMO-2"
MANIFEST_PATH = f"{ISSUE_PATH}/attachments.json"
FAILED_ATTACHMENT_NAME = "release-failure.pdf"
EXISTING_ATTACHMENT_NAME = "architecture-notes.txt"
EXPECTED_RELEASE_TAG = "ts505-DEMO-2"
EXPECTED_ERROR_FRAGMENTS = (
    "Could not upload GitHub release asset",
    FAILED_ATTACHMENT_NAME,
    EXPECTED_RELEASE_TAG,
    "(500)",
    "Internal Server Error",
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    probe = create_ts505_github_release_upload_failure_probe(REPO_ROOT)

    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "config_path": str(REPO_ROOT / "testing/tests/TS-505/config.yaml"),
        "os": platform.system(),
        "issue_key": ISSUE_KEY,
        "issue_path": ISSUE_PATH,
        "manifest_path": MANIFEST_PATH,
        "failed_attachment_name": FAILED_ATTACHMENT_NAME,
        "existing_attachment_name": EXISTING_ATTACHMENT_NAME,
        "expected_release_tag": EXPECTED_RELEASE_TAG,
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
            "Precondition failed: the TS-505 Dart probe did not analyze cleanly.\n"
            f"{execution.analyze_output}"
        )
        return failures

    if payload.get("status") != "passed":
        details = [str(payload.get("error") or "The TS-505 Dart probe reported a failure.")]
        stack_trace = payload.get("stackTrace")
        if stack_trace:
            details.append(str(stack_trace))
        failures.append("\n".join(details))
        return failures

    upload_outcome = _as_dict(payload.get("uploadOutcome"))
    manifest_before = _as_text(payload.get("manifestBefore"))
    manifest_after = _as_text(payload.get("manifestAfter"))
    release_write_calls = _as_list_of_dicts(payload.get("releaseWriteCalls"))
    metadata_write_calls = _as_list_of_dicts(payload.get("metadataWriteCalls"))
    release_delete_calls = _as_list_of_dicts(payload.get("releaseDeleteCalls"))
    release_read_calls = _as_list_of_dicts(payload.get("releaseReadCalls"))
    metadata_read_calls = _as_list_of_dicts(payload.get("metadataReadCalls"))

    result["manifest_before"] = manifest_before
    result["manifest_after"] = manifest_after
    result["release_write_calls"] = release_write_calls
    result["metadata_write_calls"] = metadata_write_calls
    result["release_delete_calls"] = release_delete_calls
    result["release_read_calls"] = release_read_calls
    result["metadata_read_calls"] = metadata_read_calls
    result["upload_outcome"] = upload_outcome

    if upload_outcome.get("status") != "error":
        failures.append(
            "Step 1 failed: starting the github-releases upload did not return a direct "
            "failure to the caller.\n"
            f"Observed upload outcome: {json.dumps(upload_outcome, indent=2, sort_keys=True)}"
        )
    else:
        message = _as_text(upload_outcome.get("message"))
        missing_fragments = [
            fragment for fragment in EXPECTED_ERROR_FRAGMENTS if fragment not in message
        ]
        if missing_fragments:
            failures.append(
                "Step 1 failed: the caller-visible upload failure did not expose the "
                "expected GitHub asset upload error details.\n"
                f"Missing message fragments: {missing_fragments}\n"
                f"Observed message: {message}"
            )
        else:
            _record_step(
                result,
                step=1,
                status="passed",
                action="Start a github-releases attachment upload for `release-failure.pdf`.",
                observed=message,
            )
            _record_human_verification(
                result,
                check=(
                    "Verified the caller-visible failure text immediately reported the "
                    "release asset upload failure with the expected 500 context, instead "
                    "of returning a success-shaped result."
                ),
                observed=message,
            )

    if len(release_write_calls) != 1:
        failures.append(
            "Step 2 failed: the scripted GitHub release asset POST was not exercised "
            "exactly once.\n"
            f"Observed release write calls: {json.dumps(release_write_calls, indent=2, sort_keys=True)}"
        )
    else:
        release_write = release_write_calls[0]
        if release_write.get("assetName") != FAILED_ATTACHMENT_NAME:
            failures.append(
                "Step 2 failed: the failed release upload did not target the expected "
                "attachment name.\n"
                f"Observed release write call: {json.dumps(release_write, indent=2, sort_keys=True)}"
            )
        if release_write.get("releaseTag") != EXPECTED_RELEASE_TAG:
            failures.append(
                "Step 2 failed: the failed release upload did not target the expected "
                "issue release tag.\n"
                f"Observed release write call: {json.dumps(release_write, indent=2, sort_keys=True)}"
            )
        if not failures:
            _record_step(
                result,
                step=2,
                status="passed",
                action=(
                    "Force the production upload transaction to hit a synthetic HTTP 500 "
                    "during the GitHub `POST .../releases/.../assets` mutation."
                ),
                observed=json.dumps(release_write, sort_keys=True),
            )

    if metadata_write_calls:
        failures.append(
            "Step 3 failed: `attachments.json` was written even though the remote asset "
            "upload failed before the metadata update should occur.\n"
            f"Observed metadata write calls: {json.dumps(metadata_write_calls, indent=2, sort_keys=True)}"
        )
    if manifest_after != manifest_before:
        failures.append(
            "Step 3 failed: `attachments.json` changed after the failed GitHub asset "
            "upload.\n"
            f"Manifest before:\n{manifest_before}\n"
            f"Manifest after:\n{manifest_after}"
        )

    manifest_entries = _parse_manifest_entries(manifest_after)
    failed_entries = [
        entry
        for entry in manifest_entries
        if str(entry.get("name", "")).strip() == FAILED_ATTACHMENT_NAME
    ]
    existing_entries = [
        entry
        for entry in manifest_entries
        if str(entry.get("name", "")).strip() == EXISTING_ATTACHMENT_NAME
    ]
    if failed_entries:
        failures.append(
            "Expected result failed: the failed attachment was still recorded in "
            "`attachments.json`.\n"
            f"Observed failed attachment entries: {json.dumps(failed_entries, indent=2, sort_keys=True)}"
        )
    if len(existing_entries) != 1:
        failures.append(
            "Expected result failed: the seeded manifest entry was not preserved after "
            "the failed upload.\n"
            f"Observed manifest entries: {json.dumps(manifest_entries, indent=2, sort_keys=True)}"
        )
    if release_delete_calls:
        failures.append(
            "Expected result failed: rollback delete calls were triggered even though the "
            "release asset write itself failed before any metadata mutation.\n"
            f"Observed release delete calls: {json.dumps(release_delete_calls, indent=2, sort_keys=True)}"
        )
    if release_read_calls:
        failures.append(
            "Expected result failed: rollback read calls were triggered even though there "
            "was no previous release-backed attachment to restore.\n"
            f"Observed release read calls: {json.dumps(release_read_calls, indent=2, sort_keys=True)}"
        )

    if not failures:
        _record_step(
            result,
            step=3,
            status="passed",
            action="Inspect `attachments.json` after the failed remote asset mutation.",
            observed=(
                "manifest_write_calls=0; "
                f"metadata_reads={len(metadata_read_calls)}; "
                f"manifest_preserved={manifest_after == manifest_before}; "
                f"failed_attachment_entries={len(failed_entries)}; "
                f"existing_attachment_entries={len(existing_entries)}"
            ),
        )
        _record_human_verification(
            result,
            check=(
                "Verified the observable manifest text stayed byte-for-byte unchanged "
                "after the failed upload and still showed only the original "
                f"`{EXISTING_ATTACHMENT_NAME}` entry."
            ),
            observed=manifest_after,
        )
    return failures


def _parse_manifest_entries(manifest_text: str) -> list[dict[str, object]]:
    stripped = manifest_text.strip()
    if not stripped:
        return []
    payload = json.loads(stripped)
    if not isinstance(payload, list):
        raise AssertionError(
            "`attachments.json` was not a JSON array after the TS-505 probe.\n"
            f"Observed payload: {payload}"
        )
    return [entry for entry in payload if isinstance(entry, dict)]


def _write_pass_outputs(result: dict[str, object]) -> None:
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()

    summary = "1 passed, 0 failed"
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": summary,
            }
        ),
        encoding="utf-8",
    )

    jira_lines = [
        f"h3. {TICKET_KEY} Passed",
        "",
        "*Automated coverage*",
        f"* Started the production github-releases upload transaction for {{{FAILED_ATTACHMENT_NAME}}}.",
        "* Forced a synthetic HTTP 500 during the GitHub release asset POST.",
        f"* Verified {{{MANIFEST_PATH}}} was not written, stayed byte-for-byte unchanged, and did not gain {{{FAILED_ATTACHMENT_NAME}}}.",
        "",
        "*Human-style verification*",
        "* Checked the caller-visible error text and confirmed it immediately reported the release asset upload failure with the expected 500 details.",
        f"* Read the observable manifest JSON after the failure and confirmed only the original {{{EXISTING_ATTACHMENT_NAME}}} entry remained.",
        "",
        "*Observed result*",
        f"* Caller-visible error: {{code}}{_as_text(_as_dict(result.get('upload_outcome')).get('message'))}{{code}}",
        f"* Manifest path: {{{MANIFEST_PATH}}}",
        "{code:json}",
        _as_text(result.get("manifest_after")).rstrip(),
        "{code}",
        "",
        "*Outcome*",
        "* Matched the expected result: the upload failed directly and TrackState did not record the failed release-backed attachment in attachments.json.",
    ]
    markdown_lines = [
        f"## {TICKET_KEY} Passed",
        "",
        "**Automated coverage**",
        f"- Started the production github-releases upload transaction for `{FAILED_ATTACHMENT_NAME}`.",
        "- Forced a synthetic HTTP 500 during the GitHub release asset POST.",
        f"- Verified `{MANIFEST_PATH}` was not written, stayed byte-for-byte unchanged, and did not gain `{FAILED_ATTACHMENT_NAME}`.",
        "",
        "**Human-style verification**",
        "- Checked the caller-visible error text and confirmed it immediately reported the release asset upload failure with the expected 500 details.",
        f"- Read the observable manifest JSON after the failure and confirmed only the original `{EXISTING_ATTACHMENT_NAME}` entry remained.",
        "",
        "**Observed result**",
        f"- Caller-visible error: `{_as_text(_as_dict(result.get('upload_outcome')).get('message'))}`",
        f"- Manifest path: `{MANIFEST_PATH}`",
        "```json",
        _as_text(result.get("manifest_after")).rstrip(),
        "```",
        "",
        "**Outcome**",
        "- Matched the expected result: the upload failed directly and TrackState did not record the failed release-backed attachment in `attachments.json`.",
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
        ),
        encoding="utf-8",
    )

    manifest_before = _as_text(result.get("manifest_before"))
    manifest_after = _as_text(result.get("manifest_after"))
    upload_outcome = _as_dict(result.get("upload_outcome"))
    payload = _as_dict(result.get("probe_payload"))
    trace = _as_text(result.get("traceback"))
    probe_run_output = _as_text(result.get("probe_run_output"))

    jira_lines = [
        f"h3. {TICKET_KEY} Failed",
        "",
        "*Failure summary*",
        f"* {error_message}",
        "",
        "*Step-by-step reproduction*",
        f"# Start an attachment upload for {{{FAILED_ATTACHMENT_NAME}}} while the project uses github-releases mode. "
        f"Observed: caller outcome = {json.dumps(upload_outcome, sort_keys=True)}",
        "# Mock a network failure or 500 error during the GitHub release asset POST. "
        f"Observed scripted release write calls: {json.dumps(result.get('release_write_calls', []), sort_keys=True)}",
        f"# Inspect {{{MANIFEST_PATH}}} for the target issue. "
        f"Observed before = {manifest_before!r}; after = {manifest_after!r}",
        "",
        "*Exact failure output*",
        "{code}",
        trace.rstrip(),
        "{code}",
        "",
        "*Actual vs Expected*",
        f"* Expected: the caller should receive a direct upload failure and {{{MANIFEST_PATH}}} should remain unchanged without a {{{FAILED_ATTACHMENT_NAME}}} entry.",
        f"* Actual: caller outcome = {json.dumps(upload_outcome, sort_keys=True)}; manifest before = {manifest_before!r}; manifest after = {manifest_after!r}.",
        "",
        "*Environment*",
        f"* OS: {platform.system()}",
        f"* Probe package: {{{REPO_ROOT / 'testing/tests/TS-505/dart_probe'}}}",
        "* Runtime: production ProviderBackedTrackStateRepository with a scripted release-asset 500",
        "",
        "*Relevant logs*",
        "{code}",
        probe_run_output.rstrip() or json.dumps(payload, indent=2, sort_keys=True),
        "{code}",
    ]
    markdown_lines = [
        f"## {TICKET_KEY} Failed",
        "",
        "**Failure summary**",
        f"- {error_message}",
        "",
        "**Step-by-step reproduction**",
        f"1. Start an attachment upload for `{FAILED_ATTACHMENT_NAME}` while the project uses github-releases mode. Observed: caller outcome = `{json.dumps(upload_outcome, sort_keys=True)}`",
        f"2. Mock a network failure or 500 error during the GitHub release asset POST. Observed scripted release write calls: `{json.dumps(result.get('release_write_calls', []), sort_keys=True)}`",
        f"3. Inspect `{MANIFEST_PATH}` for the target issue. Observed before = `{manifest_before!r}`; after = `{manifest_after!r}`",
        "",
        "**Exact failure output**",
        "```text",
        trace.rstrip(),
        "```",
        "",
        "**Actual vs Expected**",
        f"- Expected: the caller should receive a direct upload failure and `{MANIFEST_PATH}` should remain unchanged without a `{FAILED_ATTACHMENT_NAME}` entry.",
        f"- Actual: caller outcome = `{json.dumps(upload_outcome, sort_keys=True)}`; manifest before = `{manifest_before!r}`; manifest after = `{manifest_after!r}`.",
        "",
        "**Environment**",
        f"- OS: {platform.system()}",
        f"- Probe package: `{REPO_ROOT / 'testing/tests/TS-505/dart_probe'}`",
        "- Runtime: production `ProviderBackedTrackStateRepository` with a scripted release-asset 500",
        "",
        "**Relevant logs**",
        "```text",
        probe_run_output.rstrip() or json.dumps(payload, indent=2, sort_keys=True),
        "```",
    ]
    bug_lines = [
        f"# {TICKET_KEY} - GitHub release asset failure mutates attachments.json",
        "",
        "## Steps to reproduce",
        f"1. Start an attachment upload for `{FAILED_ATTACHMENT_NAME}` while the project uses `github-releases` mode. "
        f"Observed: caller outcome = `{json.dumps(upload_outcome, sort_keys=True)}`.",
        "2. Mock a network failure or HTTP 500 during the GitHub release asset POST. "
        f"Observed scripted release write calls = `{json.dumps(result.get('release_write_calls', []), sort_keys=True)}`.",
        f"3. Inspect `{MANIFEST_PATH}` for the target issue. "
        f"Observed before = `{manifest_before!r}`; after = `{manifest_after!r}`.",
        "",
        "## Exact error message or assertion failure",
        "```text",
        trace.rstrip(),
        "```",
        "",
        "## Actual vs Expected",
        f"- Expected: the caller should receive a direct upload failure and `{MANIFEST_PATH}` should remain unchanged without a `{FAILED_ATTACHMENT_NAME}` entry.",
        f"- Actual: caller outcome = `{json.dumps(upload_outcome, sort_keys=True)}`; manifest before = `{manifest_before!r}`; manifest after = `{manifest_after!r}`.",
        "",
        "## Environment details",
        f"- OS: {platform.system()}",
        f"- Probe package: `{REPO_ROOT / 'testing/tests/TS-505/dart_probe'}`",
        "- Runtime: production `ProviderBackedTrackStateRepository` with a scripted release-asset 500",
        "",
        "## Logs",
        "```text",
        probe_run_output.rstrip() or json.dumps(payload, indent=2, sort_keys=True),
        "```",
    ]
    JIRA_COMMENT_PATH.write_text("\n".join(jira_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
    RESPONSE_PATH.write_text("\n".join(markdown_lines) + "\n", encoding="utf-8")
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
    checks = result.setdefault("human_verification", [])
    assert isinstance(checks, list)
    checks.append({"check": check, "observed": observed})


def _as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list_of_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if isinstance(entry, dict)]


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value)


if __name__ == "__main__":
    main()
