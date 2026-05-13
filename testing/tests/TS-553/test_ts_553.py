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

TICKET_KEY = "TS-553"
TICKET_SUMMARY = (
    "Upload attachment with existing filename replaces the release asset deterministically"
)
OUTPUTS_DIR = REPO_ROOT / "outputs"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-553/test_ts_553.py"
RUN_COMMAND = "python testing/tests/TS-553/test_ts_553.py"


class Ts553ReleaseReplacementScenario(TrackStateCliReleaseReplacementScenario):
    def __init__(self) -> None:
        super().__init__(
            repository_root=REPO_ROOT,
            test_directory="TS-553",
            ticket_key=TICKET_KEY,
            ticket_summary=TICKET_SUMMARY,
        )


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts553ReleaseReplacementScenario()

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
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    RESULT_PATH.write_text(
        json.dumps(
            {
                "status": "passed",
                "passed": 1,
                "failed": 0,
                "skipped": 0,
                "summary": "1 passed, 0 failed",
            },
        )
        + "\n",
        encoding="utf-8",
    )

    response_lines = [
        f"* Refactored `{TEST_FILE_PATH}` to use a dedicated probe, framework, validator, and support scenario.",
        (
            "* Test result: passed — the exact local upload command replaced the seeded "
            "release asset and updated `attachments.json` to the new asset id."
        ),
    ]
    pr_lines = [
        "## TS-553 rework",
        "",
        "- Moved TS-553 execution behind a dedicated `core/interfaces` probe with framework, validator, and support-scenario wiring.",
        "- Removed raw CLI compilation, git setup, live release seeding, polling, and cleanup from the test entrypoint.",
        (
            f"- Result: ✅ passed — `{as_text(result.get('ticket_command'))}` replaced the "
            "existing release asset deterministically and updated local metadata."
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
            },
        )
        + "\n",
        encoding="utf-8",
    )

    response_lines = [
        f"* Refactored `{TEST_FILE_PATH}` to use a dedicated probe, framework, validator, and support scenario.",
        (
            f"* Test result: failed — `{as_text(result.get('ticket_command'))}` did not "
            "leave the expected single replacement release asset and updated manifest entry."
        ),
    ]
    pr_lines = [
        "## TS-553 rework",
        "",
        "- Moved TS-553 execution behind a dedicated `core/interfaces` probe with framework, validator, and support-scenario wiring.",
        "- Removed raw CLI compilation, git setup, live release seeding, polling, and cleanup from the test entrypoint.",
        (
            f"- Result: ❌ failed — `{as_text(result.get('ticket_command'))}` still does not "
            "produce the expected deterministic replacement state."
        ),
    ]
    RESPONSE_PATH.write_text("\n".join(response_lines) + "\n", encoding="utf-8")
    PR_BODY_PATH.write_text("\n".join(pr_lines) + "\n", encoding="utf-8")

    payload_attachment = result.get("payload_attachment") or {}
    manifest_state = result.get("manifest_state") or {}
    release_state = result.get("release_state") or {}
    final_state = {
        "final_state": result.get("final_state") or {},
        "manifest_state": manifest_state,
        "release_state": release_state,
        "cleanup": result.get("cleanup") or {},
    }
    final_state_text = json_text(final_state)
    visible_output = compact_text(as_text(result.get("visible_output")))
    actual_result = (
        "The exact local upload command did not converge to a single replacement release "
        "asset with matching local metadata."
    )
    if visible_output:
        actual_result += f" Visible output: `{visible_output}`."

    bug_lines = [
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
        "1. Create a local TrackState repository configured with `attachmentStorage.mode = github-releases` and seed `attachments.json` plus the issue release container with an existing `doc.pdf` asset.",
        f"2. Run `{as_text(result.get('ticket_command'))}`.",
        "3. Inspect the live release asset list and the local `attachments.json` entry for `doc.pdf`.",
        "",
        "## Expected result",
        "- The system deletes the prior asset and uploads the new version.",
        "- The GitHub Release contains only one asset named `doc.pdf`.",
        "- `attachments.json` is updated with the new asset identifier.",
        "",
        "## Actual result",
        f"- {actual_result}",
        "- Missing/broken production capability: the observable release-backed replacement flow does not converge to the expected single-asset state.",
        f"- Observed state:\n```json\n{final_state_text}\n```",
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
        "",
        "## Observed attachment payload",
        "```json",
        json_text(payload_attachment),
        "```",
    ]
    BUG_DESCRIPTION_PATH.write_text("\n".join(bug_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
