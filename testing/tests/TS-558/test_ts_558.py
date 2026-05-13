from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.trackstate_cli_release_replacement_scenario import (  # noqa: E402
    TrackStateCliReleaseReplacementScenario,
    as_text,
    compact_text,
    json_text,
    observed_command_output,
)

TICKET_KEY = "TS-558"
TICKET_SUMMARY = (
    "Upload attachment with existing filename replaces the release asset deterministically"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-558/test_ts_558.py"
RUN_COMMAND = "python testing/tests/TS-558/test_ts_558.py"


class Ts558ReleaseReplacementScenario(TrackStateCliReleaseReplacementScenario):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-558",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts558ReleaseReplacementScenario()

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
    filename = _attachment_name(result)
    release_state = result.get("release_state")
    manifest_state = result.get("manifest_state")
    visible_output = compact_text(as_text(result.get("visible_output")))
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
            f"* Executed the exact CLI upload command from a disposable local Git repository "
            f"configured with {{attachmentStorage.mode = github-releases}} and pointing "
            f"{{origin}} at {_jira_inline(as_text(result.get('remote_origin_url')))}."
        ),
        (
            f"* Seeded the live issue release with an existing {{{{{filename}}}}} asset and a "
            f"matching {{attachments.json}} entry before the upload."
        ),
        (
            f"* Verified the live GitHub Release and local {{attachments.json}} converged to "
            f"a single replacement {{{{{filename}}}}} asset after the command."
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
                    f"* Observed release assets: {_jira_inline(_release_assets_text(release_state))}"
                ),
                (
                    f"* Observed manifest state: {_jira_inline(_manifest_text(manifest_state))}"
                ),
                (
                    "* The observed behavior matched the expected result: the previous asset "
                    "was replaced, only one visible asset remained in the release, and the "
                    "manifest pointed at the new asset identifier."
                ),
            ],
        )
    else:
        lines.extend(
            [
                f"* ❌ Failure: {{noformat}}{as_text(result.get('error'))}{{noformat}}",
                (
                    f"* Visible output at failure: "
                    f"{_jira_inline(visible_output or '<empty>')}"
                ),
                (
                    f"* Observed release assets at failure: "
                    f"{_jira_inline(_release_assets_text(release_state))}"
                ),
                (
                    f"* Observed manifest state at failure: "
                    f"{_jira_inline(_manifest_text(manifest_state))}"
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
    filename = _attachment_name(result)
    release_state = result.get("release_state")
    manifest_state = result.get("manifest_state")
    visible_output = compact_text(as_text(result.get("visible_output")))
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            f"- Executed the exact CLI upload command from a disposable local Git repository "
            f"configured with `attachmentStorage.mode = github-releases` and `origin` set "
            f"to `{as_text(result.get('remote_origin_url'))}`."
        ),
        (
            f"- Seeded the live issue release with an existing `{filename}` asset and a "
            "matching `attachments.json` entry before the upload."
        ),
        (
            f"- Verified the live GitHub Release and local `attachments.json` converged to "
            f"a single replacement `{filename}` asset after the command."
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
                f"- Observed release assets: `{_release_assets_text(release_state)}`",
                f"- Observed manifest state: `{_manifest_text(manifest_state)}`",
                (
                    "- The observed behavior matched the expected result: the previous asset "
                    "was replaced, only one visible asset remained in the release, and the "
                    "manifest pointed at the new asset identifier."
                ),
            ],
        )
    else:
        lines.extend(
            [
                f"- Failure: `{as_text(result.get('error'))}`",
                f"- Visible output at failure: `{visible_output or '<empty>'}`",
                f"- Observed release assets at failure: `{_release_assets_text(release_state)}`",
                f"- Observed manifest state at failure: `{_manifest_text(manifest_state)}`",
            ],
        )
    lines.extend(["", "## How to run", "```bash", RUN_COMMAND, "```"])
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    filename = _attachment_name(result)
    command = as_text(result.get("ticket_command"))
    release_state = result.get("release_state")
    manifest_state = result.get("manifest_state")
    final_state = result.get("final_state")
    visible_output = compact_text(as_text(result.get("visible_output")))
    lines = [
        f"# {TICKET_KEY} - Existing release asset is not replaced deterministically",
        "",
        "## Steps to reproduce",
        (
            "1. ✅ Configure a local TrackState repository with "
            "`attachmentStorage.mode = github-releases`, a valid GitHub remote, and live "
            f"authentication; ensure issue `{as_text(result.get('issue_key'))}` already has "
            f"`{filename}` stored in its GitHub Release."
        ),
        (
            f"2. ❌ Execute the exact CLI command `{command}` from that repository."
        ),
        f"   - Actual behavior: {as_text(result.get('error'))}",
        f"   - Visible output: `{visible_output or '<empty>'}`",
        "3. ❌ Verify the GitHub Release asset list and local `attachments.json` entry.",
        (
            "   - Actual live release state:\n\n```json\n"
            f"{json_text(release_state)}\n```"
        ),
        (
            "   - Actual manifest state:\n\n```json\n"
            f"{json_text(manifest_state)}\n```"
        ),
        (
            "   - Actual local repository state:\n\n```json\n"
            f"{json_text(final_state)}\n```"
        ),
        "",
        "## Expected vs Actual",
        (
            f"- **Expected:** the command should delete the old `{filename}` release asset, "
            "upload the new version, leave exactly one asset with that filename in the "
            "release, and update `attachments.json` to the new asset identifier."
        ),
        (
            f"- **Actual:** {as_text(result.get('error')) or 'The replacement flow did not converge.'} "
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
            f"{json_text({'payload_attachment': result.get('payload_attachment'), 'seeded_release': result.get('seeded_release')})}\n```"
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


def _release_assets_text(value: object) -> str:
    if not isinstance(value, dict):
        return "unavailable"
    asset_names = value.get("asset_names")
    asset_ids = value.get("asset_ids")
    return f"names={asset_names}, ids={asset_ids}"


def _manifest_text(value: object) -> str:
    if not isinstance(value, dict):
        return "unavailable"
    entry = value.get("matching_entry")
    return (
        f"entry_count={value.get('entry_count')}, "
        f"matches_expected={value.get('matches_expected')}, "
        f"matching_entry={entry}"
    )


def _attachment_name(result: dict[str, object]) -> str:
    name = as_text(result.get("expected_attachment_name"))
    return name or "attachment"


def _jira_inline(value: str) -> str:
    return "{{" + value.replace("{", "").replace("}", "") + "}}"


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
