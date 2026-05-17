from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.tests.support.trackstate_cli_release_request_order_scenario import (  # noqa: E402
    TrackStateCliReleaseRequestOrderScenario,
    as_text,
    compact_text,
    json_text,
    observed_command_output,
)

TICKET_KEY = "TS-610"
TICKET_SUMMARY = (
    "Asset re-upload flow performs release lookup and deletion before upload"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-610/test_ts_610.py"
RUN_COMMAND = "python3 testing/tests/TS-610/test_ts_610.py"


class Ts610ReleaseRequestOrderScenario(TrackStateCliReleaseRequestOrderScenario):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-610",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts610ReleaseRequestOrderScenario()

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
    request_flow = _jira_inline(as_text(result.get("api_request_flow")) or "<none>")
    release_state = result.get("release_state")
    manifest_state = result.get("manifest_state")
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
            "* Executed the exact local CLI upload command from a disposable Git "
            "repository configured with {attachmentStorage.mode = github-releases}."
        ),
        (
            "* Seeded the live issue release with an existing {logic.drawio} asset and "
            "a matching {attachments.json} entry before the upload."
        ),
        (
            "* Captured the live GitHub REST API flow and verified the CLI looked up the "
            "release tag before deleting the colliding asset and only uploaded the new "
            "bytes afterward."
        ),
        (
            "* Verified the user-visible result still converged to one replacement "
            "{logic.drawio} asset with updated bytes."
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
                f"* Observed request flow: {request_flow}",
                (
                    f"* Observed release assets: "
                    f"{_jira_inline(_release_assets_text(release_state))}"
                ),
                (
                    f"* Observed manifest state: "
                    f"{_jira_inline(_manifest_text(manifest_state))}"
                ),
                (
                    "* The observed behavior matched the expected result: the CLI resolved "
                    "the release first, removed the colliding asset before upload, and the "
                    "final visible attachment state matched the replacement payload."
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
                f"* Observed request flow at failure: {request_flow}",
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
    visible_output = compact_text(as_text(result.get("visible_output")))
    request_flow = as_text(result.get("api_request_flow")) or "<none>"
    release_state = result.get("release_state")
    manifest_state = result.get("manifest_state")
    lines = [
        "## Test Automation Result",
        "",
        f"**Status:** {'✅ PASSED' if status == 'PASSED' else '❌ FAILED'}",
        f"**Test Case:** {TICKET_KEY} — {TICKET_SUMMARY}",
        "",
        "## What was automated",
        (
            "- Executed the exact local CLI upload command from a disposable Git "
            "repository configured with `attachmentStorage.mode = github-releases`."
        ),
        (
            "- Seeded the live issue release with an existing `logic.drawio` asset and a "
            "matching `attachments.json` entry before the upload."
        ),
        (
            "- Captured the live GitHub REST API flow and verified the CLI looked up the "
            "release tag before deleting the colliding asset and only uploaded the new "
            "bytes afterward."
        ),
        (
            "- Verified the final user-visible state still converged to one replacement "
            "`logic.drawio` asset with updated bytes."
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
                f"- Observed request flow:\n```text\n{request_flow}\n```",
                f"- Observed release assets: `{_release_assets_text(release_state)}`",
                f"- Observed manifest state: `{_manifest_text(manifest_state)}`",
                (
                    "- The observed behavior matched the expected result: the CLI resolved "
                    "the release first, removed the colliding asset before upload, and the "
                    "final visible attachment state matched the replacement payload."
                ),
            ],
        )
    else:
        lines.extend(
            [
                f"- Failure: `{as_text(result.get('error'))}`",
                f"- Visible output at failure: `{visible_output or '<empty>'}`",
                f"- Observed request flow at failure:\n```text\n{request_flow}\n```",
                f"- Observed release assets at failure: `{_release_assets_text(release_state)}`",
                f"- Observed manifest state at failure: `{_manifest_text(manifest_state)}`",
            ],
        )
    lines.extend(["", "## How to run", "```bash", RUN_COMMAND, "```"])
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    request_flow = as_text(result.get("api_request_flow")) or "<none>"
    manifest_state = result.get("manifest_state") or {}
    release_state = result.get("release_state") or {}
    final_state = {
        "final_state": result.get("final_state") or {},
        "manifest_state": manifest_state,
        "release_state": release_state,
        "api_requests": result.get("api_requests") or [],
        "cleanup": result.get("cleanup") or {},
    }
    final_state_text = json_text(final_state)
    return "\n".join(
        [
            f"# {TICKET_KEY} bug reproduction",
            "",
            "## Environment",
            f"- Repository: `{as_text(result.get('repository'))}` @ `{as_text(result.get('repository_ref'))}`",
            f"- Local repository path: `{as_text(result.get('repository_path'))}`",
            f"- Remote origin URL: `{as_text(result.get('remote_origin_url'))}`",
            f"- OS: `{as_text(result.get('os'))}`",
            f"- Command: `{as_text(result.get('ticket_command'))}`",
            f"- Release tag: `{as_text(result.get('release_tag'))}`",
            "",
            "## Steps to reproduce",
            "1. Configure a TrackState repository with `attachmentStorage.mode = github-releases` and seed the issue release with an existing `logic.drawio` asset plus a matching `attachments.json` entry. ✅",
            (
                "2. Upload a new version of `logic.drawio` to the same issue and monitor the "
                "GitHub REST API requests. "
                f"❌ Actual result: {as_text(result.get('error'))}"
            ),
            (
                "3. Expect the flow to perform release lookup first, delete the existing asset "
                "second, and upload the new bytes third. "
                f"❌ Actual observed request flow:\n```text\n{request_flow}\n```"
            ),
            (
                "4. Inspect the live release and `attachments.json`. "
                f"Observed state:\n```json\n{final_state_text}\n```"
            ),
            "",
            "## Actual vs Expected",
            "- Expected: `GET /repos/{owner}/{repo}/releases/tags/{tag}` occurs before `DELETE /repos/{owner}/{repo}/releases/assets/{asset_id}`, and `POST uploads.github.com/.../assets?name=logic.drawio` happens only after the delete step. The final release serves the replacement bytes.",
            (
                "- Actual: the captured request flow and/or final release state did not match "
                "that replacement order.\n"
                f"Observed request flow:\n```text\n{request_flow}\n```"
            ),
            "",
            "## Failing command output",
            "```text",
            observed_command_output(
                as_text(result.get("stdout")),
                as_text(result.get("stderr")),
            ).rstrip(),
            "```",
            "",
            "## Exact error / assertion",
            "```text",
            as_text(result.get("traceback")).rstrip(),
            "```",
        ],
    ) + "\n"


def _jira_step_lines(steps: object) -> list[str]:
    if not isinstance(steps, list) or not steps:
        return ["* No automation steps were recorded."]
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"* Step {step.get('step')}: *{str(step.get('status', '')).upper()}* — "
            f"{as_text(step.get('action'))}"
        )
        lines.append(
            f"** Observed: {_jira_inline(compact_text(as_text(step.get('observed'))))}"
        )
    return lines or ["* No automation steps were recorded."]


def _jira_human_lines(entries: object) -> list[str]:
    if not isinstance(entries, list) or not entries:
        return ["* No human-style checks were recorded."]
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lines.append(f"* {as_text(entry.get('check'))}")
        lines.append(
            f"** Observed: {_jira_inline(compact_text(as_text(entry.get('observed'))))}"
        )
    return lines or ["* No human-style checks were recorded."]


def _markdown_step_lines(steps: object) -> list[str]:
    if not isinstance(steps, list) or not steps:
        return ["- No automation steps were recorded."]
    lines: list[str] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        lines.append(
            f"- Step {step.get('step')}: **{str(step.get('status', '')).upper()}** — "
            f"{as_text(step.get('action'))}"
        )
        lines.append(f"  Observed: `{compact_text(as_text(step.get('observed')))}`")
    return lines or ["- No automation steps were recorded."]


def _markdown_human_lines(entries: object) -> list[str]:
    if not isinstance(entries, list) or not entries:
        return ["- No human-style checks were recorded."]
    lines: list[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        lines.append(f"- {as_text(entry.get('check'))}")
        lines.append(f"  Observed: `{compact_text(as_text(entry.get('observed')))}`")
    return lines or ["- No human-style checks were recorded."]


def _release_assets_text(release_state: object) -> str:
    if not isinstance(release_state, dict):
        return "<unknown>"
    names = release_state.get("asset_names")
    ids = release_state.get("asset_ids")
    return f"names={names}; ids={ids}; sha256={release_state.get('downloaded_asset_sha256')}"


def _manifest_text(manifest_state: object) -> str:
    if not isinstance(manifest_state, dict):
        return "<unknown>"
    return compact_text(json_text(manifest_state))


def _jira_inline(text: str) -> str:
    escaped = text.replace("{", "\\{").replace("}", "\\}")
    return f"{{noformat}}{escaped}{{noformat}}"


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
