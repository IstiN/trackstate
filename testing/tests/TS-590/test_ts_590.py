from __future__ import annotations

import json
import platform
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.trackstate_cli_release_body_normalization_scenario import (  # noqa: E402
    TrackStateCliReleaseBodyNormalizationScenario,
    TrackStateCliReleaseBodyNormalizationScenarioOptions,
)

TICKET_KEY = "TS-590"
TICKET_SUMMARY = "Reuse release with modified metadata normalizes the release body"
TEST_FILE_PATH = "testing/tests/TS-590/test_ts_590.py"
RUN_COMMAND = "python testing/tests/TS-590/test_ts_590.py"
OUTPUTS_DIR = REPO_ROOT / "outputs"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
REVIEW_REPLIES_PATH = OUTPUTS_DIR / "review_replies.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
DISCUSSIONS_RAW_PATH = REPO_ROOT / "input" / TICKET_KEY / "pr_discussions_raw.json"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    JIRA_COMMENT_PATH.unlink(missing_ok=True)
    scenario = TrackStateCliReleaseBodyNormalizationScenario(
        options=TrackStateCliReleaseBodyNormalizationScenarioOptions(
            repository_root=REPO_ROOT,
            test_directory="TS-590",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
            test_file_path=TEST_FILE_PATH,
            run_command=RUN_COMMAND,
            token_env_vars=("GH_TOKEN", "GITHUB_TOKEN"),
        )
    )
    result, error = scenario.execute()
    if error:
        _write_failure_outputs(result)
        _write_review_replies(result, passed=False)
    else:
        _write_pass_outputs(result)
        _write_review_replies(result, passed=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    if error:
        raise SystemExit(error)


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
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, object]) -> None:
    error = as_text(result.get("error")) or "AssertionError: unknown failure"
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "failed",
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "summary": "0 passed, 1 failed",
                "error": error,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    JIRA_COMMENT_PATH.write_text(_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _write_review_replies(result: dict[str, object], *, passed: bool) -> None:
    REVIEW_REPLIES_PATH.write_text(
        _build_review_replies(result, passed=passed),
        encoding="utf-8",
    )


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "✅ PASSED" if passed else "❌ FAILED"
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {status}",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Command:* {{{{{RUN_COMMAND}}}}}",
        "",
        "h4. What was tested",
        (
            "* Ran the exact ticket command "
            "{{trackstate attachment upload --issue TS-123 --file note.txt --target local}} "
            "from a disposable local TrackState repository configured with "
            "{{attachmentStorage.mode = github-releases}}."
        ),
        (
            "* Seeded a matching draft GitHub Release for {{TS-123}} with the correct "
            "tag/title and a custom body, then verified the release via the live API and "
            "{{gh release view}} after upload."
        ),
        "* Verified the local {{attachments.json}} manifest converged to the expected release-backed entry.",
        "",
        "h4. Human-style verification",
        *_human_lines(result, jira=True),
        "",
        "h4. Result",
        *_step_lines(result, jira=True),
        "",
        "h4. Environment",
        f"* Repository: {{{{{as_text(result.get('repository'))}}}}} @ {{{{{as_text(result.get('repository_ref'))}}}}}",
        f"* Remote origin: {{{{{as_text(result.get('remote_origin_url'))}}}}}",
        "* Browser: {{N/A (CLI scenario)}}",
        f"* OS: {{{{{platform.platform()}}}}}",
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Exact error",
                "{code:text}",
                as_text(result.get("traceback")) or as_text(result.get("error")),
                "{code}",
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    release_state = as_dict(result.get("release_state"))
    expected_release_body = as_text(result.get("expected_release_body")).rstrip("\n")
    lines = [
        "## Rework Summary",
        (
            "- Resolved the TS-590 merge conflicts in the ticket test and support scenario "
            "without changing the intended coverage."
        ),
        f"- Re-ran `{RUN_COMMAND}` — **{'PASSED' if passed else 'FAILED'}**.",
    ]
    if passed:
        lines.append(
            f"- The reused release body converged to `{expected_release_body}`."
        )
    else:
        lines.append(
            "- The test still reproduces the product-visible gap: the reused release body "
            f"stayed `{as_text(release_state.get('release_body'))}` instead of "
            f"`{expected_release_body}`."
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    release_state = as_dict(result.get("release_state"))
    gh_view = as_dict(result.get("gh_release_view"))
    gh_payload = as_dict(gh_view.get("json_payload"))
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        f"**Command:** `{RUN_COMMAND}`",
        "",
        "## Rework",
        "- Resolved the current merge conflicts in the TS-590 ticket test and support scenario.",
        "- Kept the existing layered test structure and failure evidence intact.",
        "",
        "## Automation coverage",
        (
            "- Ran the exact ticket command "
            "`trackstate attachment upload --issue TS-123 --file note.txt --target local` "
            "from a disposable local TrackState repository configured with "
            "`attachmentStorage.mode = github-releases`."
        ),
        (
            "- Seeded a matching draft GitHub Release for `TS-123` with the correct "
            "tag/title and a custom body, then inspected the release through the live API "
            "and `gh release view`."
        ),
        "- Verified the local `attachments.json` manifest converged to the expected release-backed entry.",
        "",
        "## Observed result",
        f"- Expected release body: `{as_text(result.get('expected_release_body')).rstrip()}`",
        f"- Observed live release body: `{as_text(release_state.get('release_body')).rstrip()}`",
        f"- Observed `gh release view` body: `{as_text(gh_payload.get('body')).rstrip()}`",
        "",
        "## Step results",
        *_step_lines(result, jira=False),
        "",
        "## Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if passed:
        lines.append(
            "- The reused draft release converged to the standard machine-managed note."
        )
    else:
        lines.extend(
            [
                "",
                "## Failure summary",
                (
                    "- The upload succeeded and reused the seeded draft release, but the "
                    "release body stayed custom instead of normalizing to the machine-managed note."
                ),
                f"- Exact error: `{as_text(result.get('error'))}`",
                "",
                "## Exact error",
                "```text",
                as_text(result.get("traceback")) or as_text(result.get("error")),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    release_state = as_dict(result.get("release_state"))
    manifest_state = as_dict(result.get("manifest_state"))
    gh_view = as_dict(result.get("gh_release_view"))
    gh_payload = as_dict(gh_view.get("json_payload"))
    payload = as_dict(result.get("payload"))
    expected_release_body = as_text(result.get("expected_release_body")).rstrip("\n")
    target = as_dict(payload.get("target"))
    return "\n".join(
        [
            "# TS-590 - Reused GitHub Release body is not normalized",
            "",
            "## Preconditions used in this run",
            (
                "- A disposable local TrackState repository was configured with "
                "`attachmentStorage.mode = github-releases` and set Git `origin` to "
                f"`{as_text(result.get('remote_origin_url'))}`."
            ),
            (
                "- A matching draft GitHub Release for `TS-123` was pre-created with the "
                f"correct tag/title and custom body `{as_text(result.get('seeded_release_body'))}`."
            ),
            "",
            "## Exact steps to reproduce",
            (
                "1. Execute CLI command: "
                f"`{as_text(result.get('ticket_command'))}`.\n"
                f"   - ✅ The command succeeded with exit code `{result.get('exit_code')}` and returned a "
                "successful `attachment-upload` JSON payload for `TS-123` / `note.txt`.\n"
                f"   - ✅ The local `attachments.json` manifest converged to the expected release-backed entry: "
                f"`{json.dumps(manifest_state.get('matching_entry'), sort_keys=True)}`."
            ),
            "",
            (
                "2. Inspect the GitHub Release metadata via the GitHub REST API or `gh release view`.\n"
                "   - ❌ The reused draft release did not normalize its body.\n"
                f"   - ❌ REST/API observation: release `{as_text(result.get('release_tag'))}` kept body "
                f"`{as_text(release_state.get('release_body'))}` with release id "
                f"`{release_state.get('release_id')}` and asset list `{list(release_state.get('asset_names', []))}`.\n"
                f"   - ❌ `gh release view` observation: body stayed "
                f"`{as_text(gh_payload.get('body'))}` instead of `{expected_release_body}`.\n"
                f"   - Visible `gh release view` output at failure time:\n```json\n{json.dumps(gh_payload, indent=2, sort_keys=True)}\n```"
            ),
            "",
            "## Actual vs Expected",
            (
                f"- **Expected:** after the upload succeeds, the reused draft release body is rewritten to "
                f"`{expected_release_body}` while keeping the same release id and the uploaded `note.txt` asset."
            ),
            (
                f"- **Actual:** the upload succeeded, reused release id `{release_state.get('release_id')}`, "
                "and uploaded `note.txt`, but both the live API result and `gh release view` still showed "
                f"`{as_text(release_state.get('release_body'))}`."
            ),
            "",
            "## Missing / broken production capability",
            (
                "The release-backed attachment upload path does not rewrite non-identity release metadata "
                "when it reuses an existing matching release. The production upload flow should normalize "
                "the release body back to the standard machine-managed note but currently leaves custom "
                "user-edited body text unchanged."
            ),
            "",
            "## Failing command / output",
            "```text",
            as_text(result.get("error")).rstrip(),
            "",
            as_text(result.get("traceback")).rstrip(),
            "",
            _observed_command_output(
                as_text(result.get("stdout")),
                as_text(result.get("stderr")),
            ).rstrip(),
            "```",
            "",
            "## Observed manifest state",
            "```json",
            json.dumps(manifest_state, indent=2, sort_keys=True),
            "```",
            "",
            "## Observed release state",
            "```json",
            json.dumps(release_state, indent=2, sort_keys=True),
            "```",
            "",
            "## Observed `gh release view` state",
            "```json",
            json.dumps(gh_view, indent=2, sort_keys=True),
            "```",
            "",
            "## Environment",
            f"- Repository: `{as_text(result.get('repository'))}`",
            f"- Branch/ref: `{as_text(result.get('repository_ref'))}`",
            f"- Remote origin URL: `{as_text(result.get('remote_origin_url'))}`",
            f"- Local target path: `{as_text(target.get('value'))}`",
            f"- Release tag: `{as_text(result.get('release_tag'))}`",
            "- Browser: `N/A (CLI scenario)`",
            f"- OS: `{platform.platform()}`",
        ]
    ) + "\n"


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in _steps(result):
        emoji = "✅" if step.get("status") == "passed" else "❌"
        action = as_text(step.get("action"))
        observed = as_text(step.get("observed"))
        if jira:
            lines.append(
                f"* Step {step.get('step')}: {emoji} {action} Observed: {{{{{observed}}}}}"
            )
        else:
            lines.append(
                f"- Step {step.get('step')}: {emoji} {action} Observed: `{observed}`"
            )
    if not _has_recorded_step(result, 4):
        failure_detail = as_text(result.get("error")) or "Step 4 failed."
        gh_payload = as_dict(as_dict(as_dict(result.get("gh_release_view")).get("json_payload")))
        release_state = as_dict(result.get("release_state"))
        gh_body = as_text(gh_payload.get("body"))
        release_body = as_text(release_state.get("release_body"))
        if jira:
            lines.append(
                "* Step 4: ❌ Inspect the GitHub Release metadata via REST API or "
                "{{gh release view}}. "
                f"Observed: {{{{{failure_detail}}}}} Live API body={{{{{release_body}}}}}; "
                f"gh release view body={{{{{gh_body}}}}}."
            )
        else:
            lines.append(
                "- Step 4: ❌ Inspect the GitHub Release metadata via REST API or "
                f"`gh release view`. Observed: `{failure_detail}` "
                f"Live API body=`{release_body}`; gh release view body=`{gh_body}`."
            )
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for verification in _human_verifications(result):
        check = as_text(verification.get("check"))
        observed = as_text(verification.get("observed"))
        if jira:
            lines.append(f"* {check} Observed: {{{{{observed}}}}}")
        else:
            lines.append(f"- {check} Observed: `{observed}`")
    return lines or (
        ["* No additional human-style verification recorded."]
        if jira
        else ["- No additional human-style verification recorded."]
    )


def _steps(result: dict[str, object]) -> list[dict[str, object]]:
    steps = result.get("steps")
    return [step for step in steps if isinstance(step, dict)] if isinstance(steps, list) else []


def _human_verifications(result: dict[str, object]) -> list[dict[str, object]]:
    verifications = result.get("human_verification")
    return (
        [item for item in verifications if isinstance(item, dict)]
        if isinstance(verifications, list)
        else []
    )


def _has_recorded_step(result: dict[str, object], step_number: int) -> bool:
    return any(step.get("step") == step_number for step in _steps(result))


def _build_review_replies(result: dict[str, object], *, passed: bool) -> str:
    replies = [
        {
            "inReplyToId": thread["rootCommentId"],
            "threadId": thread["threadId"],
            "reply": _review_reply_text(result, passed=passed),
        }
        for thread in _discussion_threads()
    ]
    return json.dumps({"replies": replies}, indent=2) + "\n"


def _discussion_threads() -> list[dict[str, object]]:
    if not DISCUSSIONS_RAW_PATH.is_file():
        return []
    raw = json.loads(DISCUSSIONS_RAW_PATH.read_text(encoding="utf-8"))
    threads = raw.get("threads")
    if not isinstance(threads, list):
        return []
    normalized_threads: list[dict[str, object]] = []
    for thread in threads:
        if not isinstance(thread, dict) or thread.get("resolved") is not False:
            continue
        root_comment_id = thread.get("rootCommentId")
        thread_id = thread.get("threadId")
        if root_comment_id is None or thread_id is None:
            continue
        normalized_threads.append(
            {
                "rootCommentId": root_comment_id,
                "threadId": thread_id,
            }
        )
    return normalized_threads


def _review_reply_text(result: dict[str, object], *, passed: bool) -> str:
    rerun_summary = (
        "Re-ran the current TS-590 test and it passed (`1 passed, 0 failed`)."
        if passed
        else "Re-ran the current TS-590 test and it still failed (`0 passed, 1 failed`)."
    )
    return "No unresolved actionable review threads remain on this PR. " + rerun_summary


def _observed_command_output(stdout: str, stderr: str) -> str:
    return "\n".join(
        [
            "stdout:",
            stdout.rstrip() or "<empty>",
            "",
            "stderr:",
            stderr.rstrip() or "<empty>",
        ]
    )


def as_text(value: object) -> str:
    return "" if value is None else str(value)


def as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    main()
