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
    _write_review_replies()
    if error:
        _write_failure_outputs(result)
    else:
        _write_pass_outputs(result)
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
    RESPONSE_PATH.write_text(_response_summary(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=True), encoding="utf-8")


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
    RESPONSE_PATH.write_text(_response_summary(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(result, passed=False), encoding="utf-8")
    BUG_DESCRIPTION_PATH.write_text(_bug_description(result), encoding="utf-8")


def _write_review_replies() -> None:
    REVIEW_REPLIES_PATH.write_text(
        json.dumps(
            {
                "replies": [
                    {
                        "inReplyToId": 3234613444,
                        "threadId": "PRRT_kwDOSU6Gf86BxGZs",
                        "reply": (
                            "Fixed: moved the TS-590 runtime orchestration out of the ticket "
                            "file into the layered support flow (`tests/support` scenario -> "
                            "validator component -> Python framework probe). "
                            "`testing/tests/TS-590/test_ts_590.py` now stays focused on the "
                            "ticket result and required output files."
                        ),
                    },
                    {
                        "inReplyToId": 3234613609,
                        "threadId": "PRRT_kwDOSU6Gf86BxGbu",
                        "reply": (
                            "Fixed: config parsing is now pure. "
                            "`TrackStateCliReleaseBodyNormalizationConfig.from_file()` only "
                            "deserializes YAML, and the live repository service plus repository/ref "
                            "metadata are injected from the scenario layer before probe execution."
                        ),
                    },
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    release_state = as_dict(result.get("release_state"))
    expected_release_body = as_text(result.get("expected_release_body")).rstrip("\n")
    lines = [
        "## Rework Summary",
        (
            "- Fixed both PR review findings by moving TS-590 runtime orchestration into "
            "`testing/tests/support/trackstate_cli_release_body_normalization_scenario.py`, "
            "a validator component, and a Python probe framework, and by making config "
            "loading pure YAML deserialization with live repository metadata injected later."
        ),
        (
            f"- Re-ran `{RUN_COMMAND}` — "
            f"**{'PASSED' if passed else 'FAILED'}**."
        ),
    ]
    if passed:
        lines.append(
            f"- The reused release converged to `{expected_release_body}`."
        )
    else:
        lines.append(
            "- The test still fails on the product-visible gap: the reused release body "
            f"stayed `{as_text(release_state.get('release_body'))}` instead of "
            f"`{expected_release_body}`."
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    release_state = as_dict(result.get("release_state"))
    gh_view = as_dict(result.get("gh_release_view"))
    gh_payload = as_dict(gh_view.get("json_payload"))
    lines = [
        "## Rework Summary",
        (
            "- Addressed the layering review by moving the TS-590 runtime orchestration behind "
            "a `tests/support` scenario, validator component, probe interface, and Python framework."
        ),
        (
            "- Addressed the config DI review by moving static YAML parsing into "
            "`TrackStateCliReleaseBodyNormalizationConfig` and injecting live repository state "
            "from the scenario layer."
        ),
        "",
        "## Test Result",
        f"- **Status:** {'✅ PASSED' if passed else '❌ FAILED'}",
        f"- **Command:** `{RUN_COMMAND}`",
        f"- **Observed release body:** `{as_text(release_state.get('release_body'))}`",
        f"- **Observed `gh release view` body:** `{as_text(gh_payload.get('body'))}`",
    ]
    if passed:
        lines.append("- The reused draft release converged to the standard machine-managed note.")
    else:
        lines.extend(
            [
                "- The test still reproduces the real product defect: the reused release body did not normalize.",
                f"- **Exact error:** `{as_text(result.get('error'))}`",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    release_state = as_dict(result.get("release_state"))
    manifest_state = as_dict(result.get("manifest_state"))
    gh_view = as_dict(result.get("gh_release_view"))
    expected_release_body = as_text(result.get("expected_release_body")).rstrip("\n")
    return "\n".join(
        [
            "# TS-590 - Reused GitHub Release body is not normalized",
            "",
            "## Steps to reproduce",
            (
                "1. Create a disposable local TrackState repository configured with "
                "`attachmentStorage.mode = github-releases` and set Git `origin` to "
                f"`{as_text(result.get('remote_origin_url'))}`."
            ),
            (
                "2. Pre-create a draft GitHub Release with the matching tag/title for `TS-123`, "
                f"but set its body to `{as_text(result.get('seeded_release_body'))}`."
            ),
            f"3. Run `{as_text(result.get('ticket_command'))}`.",
            "4. Inspect the local `attachments.json` manifest and the reused GitHub Release via API or `gh release view`.",
            "",
            "## Expected result",
            (
                "The upload succeeds, reuses the seeded draft release, and normalizes the body to "
                f"`{expected_release_body}`."
            ),
            "",
            "## Actual result",
            (
                "The upload succeeds and the local manifest converges, but the reused GitHub Release "
                f"body remains `{as_text(release_state.get('release_body'))}`."
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
            f"- Release tag: `{as_text(result.get('release_tag'))}`",
            f"- OS: `{platform.system()}`",
        ]
    ) + "\n"


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
