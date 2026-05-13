from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.trackstate_cli_release_replacement_delete_failure_scenario import (  # noqa: E402
    TrackStateCliReleaseReplacementDeleteFailureScenario,
    as_text,
    compact_text,
    json_text,
    observed_command_output,
)

TICKET_KEY = "TS-591"
TICKET_SUMMARY = (
    "API failure during asset replacement delete step returns an explicit error "
    "and preserves the manifest"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-591/test_ts_591.py"
RUN_COMMAND = "python testing/tests/TS-591/test_ts_591.py"


class Ts591ReleaseReplacementDeleteFailureScenario(
    TrackStateCliReleaseReplacementDeleteFailureScenario,
):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-591",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts591ReleaseReplacementDeleteFailureScenario()

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
            },
        )
        _write_failure_outputs(failure_result)
        raise


def _write_pass_outputs(result: dict[str, object]) -> None:
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)

    jira = _jira_comment(result, status="PASSED")
    markdown = _markdown_summary(result, status="PASSED")
    _write_text(JIRA_COMMENT_PATH, jira)
    _write_text(PR_BODY_PATH, markdown)
    _write_text(RESPONSE_PATH, markdown)


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
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    jira = _jira_comment(result, status="FAILED")
    markdown = _markdown_summary(result, status="FAILED")
    bug = _bug_description(result)
    _write_text(JIRA_COMMENT_PATH, jira)
    _write_text(PR_BODY_PATH, markdown)
    _write_text(RESPONSE_PATH, markdown)
    _write_text(BUG_DESCRIPTION_PATH, bug)


def _jira_comment(result: dict[str, object], *, status: str) -> str:
    visible_output = compact_text(as_text(result.get("visible_output")))
    manifest_entry = _manifest_entry(result)
    release_state = result.get("release_state")
    lines = [
        "h3. Test Automation Result",
        "",
        f"*Status:* {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"*Test Case:* {TICKET_KEY} — {TICKET_SUMMARY}",
        f"*Repository:* {as_text(result.get('repository'))}",
        f"*Branch:* {as_text(result.get('repository_ref'))}",
        f"*Release tag:* {as_text(result.get('release_tag'))}",
        f"*Requested command:* {{code}}{as_text(result.get('ticket_command'))}{{code}}",
        "",
        "h4. What was tested",
        (
            "* Executed the exact CLI upload command from a disposable local Git "
            "repository configured with {attachmentStorage.mode = github-releases}."
        ),
        (
            "* Seeded the live issue release with an existing {data.csv} asset and a "
            "matching {attachments.json} entry before the upload."
        ),
        (
            "* Forced only {DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}} "
            "to return HTTP 403 while leaving the rest of the GitHub Release flow live."
        ),
        (
            "* Verified the command failed visibly and that the manifest plus release "
            "asset id remained unchanged."
        ),
        "",
        "h4. Automation",
    ]
    lines.extend(_jira_step_lines(result.get("steps")))
    lines.extend(["", "h4. Human-style verification"])
    lines.extend(_jira_human_lines(result.get("human_verification")))
    lines.extend(["", "h4. Result"])
    if status == "PASSED":
        lines.extend(
            [
                (
                    f"* Observed failure message: "
                    f"{{noformat}}{visible_output or '<empty>'}{{noformat}}"
                ),
                (
                    f"* Observed manifest entry: "
                    f"{{noformat}}{compact_text(json_text(manifest_entry))}{{noformat}}"
                ),
                (
                    f"* Observed release state: "
                    f"{{noformat}}{compact_text(json_text(release_state))}{{noformat}}"
                ),
                (
                    "* The observed behavior matched the expected result: the replacement "
                    "upload failed explicitly during the asset delete step, the user-visible "
                    "error mentioned the replacement failure, and the existing attachment "
                    "metadata remained unchanged."
                ),
            ],
        )
    else:
        lines.extend(
            [
                f"* ❌ Failure: {{noformat}}{as_text(result.get('error'))}{{noformat}}",
                (
                    f"* Visible output at failure: "
                    f"{{noformat}}{visible_output or '<empty>'}{{noformat}}"
                ),
                (
                    f"* Observed manifest entry at failure: "
                    f"{{noformat}}{compact_text(json_text(manifest_entry))}{{noformat}}"
                ),
                (
                    f"* Observed release state at failure: "
                    f"{{noformat}}{compact_text(json_text(release_state))}{{noformat}}"
                ),
            ],
        )
    lines.extend(
        [
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
        ],
    )
    return "\n".join(lines) + "\n"


def _markdown_summary(result: dict[str, object], *, status: str) -> str:
    visible_output = compact_text(as_text(result.get("visible_output")))
    manifest_entry = _manifest_entry(result)
    release_state = result.get("release_state")
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            "- Executed the exact local CLI upload command from a disposable Git repository "
            "configured with `attachmentStorage.mode = github-releases`."
        ),
        (
            "- Seeded the live issue release with an existing `data.csv` asset and a "
            "matching `attachments.json` entry before the upload."
        ),
        (
            "- Forced only `DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}` to "
            "return HTTP 403 while keeping the rest of the GitHub Release flow live."
        ),
        (
            "- Verified the command failed explicitly and that the local manifest plus "
            "visible release asset stayed on the original seeded asset id."
        ),
        "",
        "## Automation details",
    ]
    lines.extend(_markdown_step_lines(result.get("steps")))
    lines.extend(["", "## Human-style verification"])
    lines.extend(_markdown_human_lines(result.get("human_verification")))
    lines.extend(["", "## Result"])
    if status == "PASSED":
        lines.extend(
            [
                f"- Observed failure message: `{visible_output or '<empty>'}`",
                f"- Observed manifest entry: `{compact_text(json_text(manifest_entry))}`",
                f"- Observed release state: `{compact_text(json_text(release_state))}`",
                (
                    "- The observed behavior matched the expected result: the upload failed "
                    "during the replacement delete step, the CLI surfaced an explicit "
                    "replace-asset error, and `attachments.json` still referenced the "
                    "original asset identifier."
                ),
            ],
        )
    else:
        lines.extend(
            [
                f"- Failure: `{as_text(result.get('error'))}`",
                f"- Visible output at failure: `{visible_output or '<empty>'}`",
                f"- Observed manifest entry at failure: `{compact_text(json_text(manifest_entry))}`",
                f"- Observed release state at failure: `{compact_text(json_text(release_state))}`",
            ],
        )
    lines.extend(["", "## How to run", "```bash", RUN_COMMAND, "```"])
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    manifest_entry = _manifest_entry(result)
    release_state = result.get("release_state")
    visible_output = compact_text(as_text(result.get("visible_output")))
    lines = [
        f"# {TICKET_KEY} - Delete failure during release-backed replacement is not handled correctly",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Configure a local TrackState repository with "
            "`attachmentStorage.mode = github-releases`, point `origin` at the live hosted "
            "repository, and ensure issue `TS-123` already has `data.csv` recorded in "
            "`attachments.json` and stored in its GitHub Release."
        ),
        (
            "2. ✅ Force `DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}` to return "
            "HTTP 403 while keeping the rest of the GitHub API live."
        ),
        (
            f"3. ❌ Execute the exact CLI command `{as_text(result.get('ticket_command'))}`."
        ),
        f"   - Actual behavior: {as_text(result.get('error'))}",
        f"   - Visible output: `{visible_output or '<empty>'}`",
        (
            "4. ❌ Inspect the local `attachments.json` entry and live release asset state "
            "for `data.csv`."
        ),
        f"   - Actual manifest state:\n\n```json\n{json_text(manifest_entry)}\n```",
        f"   - Actual release state:\n\n```json\n{json_text(release_state)}\n```",
        "",
        "## Expected vs Actual",
        (
            "- **Expected:** the command should fail explicitly because the existing release "
            "asset could not be deleted, and `attachments.json` should remain unchanged so it "
            "still references the original asset identifier."
        ),
        (
            f"- **Actual:** {as_text(result.get('error')) or 'The observed behavior did not match the expected delete-failure handling.'} "
            f"Visible output: `{visible_output or '<empty>'}`."
        ),
        "",
        "## Exact error / assertion",
        f"```text\n{as_text(result.get('traceback')).rstrip()}\n```",
        "",
        "## Command output",
        "```text",
        observed_command_output(
            as_text(result.get("stdout")),
            as_text(result.get("stderr")),
        ).rstrip(),
        "```",
        "",
        "## Environment",
        f"- Repository: `{as_text(result.get('repository'))}`",
        f"- Branch/ref: `{as_text(result.get('repository_ref'))}`",
        f"- Release tag: `{as_text(result.get('release_tag'))}`",
        f"- Remote origin URL: `{as_text(result.get('remote_origin_url'))}`",
        f"- Local repository path: `{as_text(result.get('repository_path'))}`",
        f"- OS: `{as_text(result.get('os'))}`",
        "",
        "## Logs",
        (
            "```json\n"
            f"{json_text({'payload_error': result.get('payload_error'), 'manifest_entry': manifest_entry, 'release_state': release_state})}\n```"
        ),
    ]
    return "\n".join(lines) + "\n"


def _jira_step_lines(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["* No step log was captured."]
    lines: list[str] = []
    for step in value:
        if isinstance(step, dict):
            lines.append(
                f"# [{step.get('status')}] {step.get('action')} -- {step.get('observed')}",
            )
    return lines or ["* No step log was captured."]


def _markdown_step_lines(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["1. No step log was captured."]
    lines: list[str] = []
    for step in value:
        if isinstance(step, dict):
            lines.append(
                f"1. **{step.get('status')}** {step.get('action')} — {step.get('observed')}",
            )
    return lines or ["1. No step log was captured."]


def _jira_human_lines(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["* No human-style verification notes were captured."]
    lines: list[str] = []
    for check in value:
        if isinstance(check, dict):
            lines.append(
                f"* {check.get('check')} Observed: {{noformat}}{check.get('observed')}{{noformat}}",
            )
    return lines or ["* No human-style verification notes were captured."]


def _markdown_human_lines(value: object) -> list[str]:
    if not isinstance(value, list):
        return ["1. No human-style verification notes were captured."]
    lines: list[str] = []
    for check in value:
        if isinstance(check, dict):
            lines.append(
                f"1. {check.get('check')} Observed: `{check.get('observed')}`",
            )
    return lines or ["1. No human-style verification notes were captured."]


def _manifest_entry(result: dict[str, object]) -> object:
    manifest_state = result.get("manifest_state")
    if isinstance(manifest_state, dict):
        return manifest_state.get("matching_entry")
    return None


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
