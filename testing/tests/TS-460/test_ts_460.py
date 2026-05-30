from __future__ import annotations

from dataclasses import dataclass
import json
import platform
from pathlib import Path
import sys
import traceback
import unittest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_multi_field_update_validator import (
    TrackStateCliMultiFieldUpdateValidator,
)
from testing.core.config.trackstate_cli_multi_field_update_config import (
    TrackStateCliMultiFieldUpdateConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.core.models.trackstate_cli_multi_field_update_result import (
    TrackStateCliMultiFieldUpdateObservation,
)
from testing.tests.support.trackstate_cli_multi_field_update_probe_factory import (
    create_trackstate_cli_multi_field_update_probe,
)

TICKET_KEY = "TS-460"
TEST_CASE_TITLE = "CLI Multi-field Update - Atomic bulk mutation through canonical envelope"
TEST_FILE_PATH = "testing/tests/TS-460/test_ts_460.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-460/test_ts_460.py"
DISCOVER_COMMAND = "python3 -m unittest discover -s testing/tests/TS-460 -p 'test_*.py' -v"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"

REQUEST_STEPS = (
    "Execute the public multi-field update command for TS-1.",
    "Inspect the CLI JSON response and the issue's TS/TS-1/main.md file.",
)
EXPECTED_RESULT = (
    "The command returns a single success envelope, TS/TS-1/main.md reflects all "
    "updated fields, and the mutation persists as exactly one Git commit."
)


@dataclass(frozen=True)
class Ts460Evaluation:
    config: TrackStateCliMultiFieldUpdateConfig
    observation: TrackStateCliMultiFieldUpdateObservation
    failures: tuple[str, ...]


class TrackStateCliMultiFieldUpdateTest(unittest.TestCase):
    def test_multi_field_update_uses_one_success_envelope_and_one_commit(self) -> None:
        evaluation = evaluate_ts_460(REPO_ROOT)
        if evaluation.failures:
            self.fail("\n\n".join(evaluation.failures))


def evaluate_ts_460(repository_root: Path) -> Ts460Evaluation:
    config = TrackStateCliMultiFieldUpdateConfig.from_env()
    validator = TrackStateCliMultiFieldUpdateValidator(
        probe=create_trackstate_cli_multi_field_update_probe(repository_root)
    )
    observation = validator.validate(config=config).observation
    failures: list[str] = []

    _check_equal(
        failures=failures,
        actual=observation.requested_command,
        expected=(
            *config.requested_command_prefix,
            "--path",
            observation.repository_path,
            "--key",
            config.issue_key,
            "--field",
            config.field_assignments[0],
            "--field",
            config.field_assignments[1],
            "--field",
            config.field_assignments[2],
            "--field",
            config.field_assignments[3],
        ),
        message=(
            "Precondition failed: TS-460 did not execute the expected public "
            "multi-field update command against the disposable Local Git "
            "repository.\n"
            f"Requested command: {observation.requested_command_text}"
        ),
    )

    payload = _successful_envelope_or_failures(
        result=observation.result,
        failure_prefix="Step 1 failed",
        failures=failures,
        config=config,
    )
    data = payload.get("data") if payload is not None else None
    issue = data.get("issue") if isinstance(data, dict) else None

    if isinstance(data, dict):
        _check_equal(
            failures=failures,
            actual=data.get("command"),
            expected=config.expected_command_name,
            message=(
                "Step 1 failed: the success envelope did not identify the "
                "canonical public multi-field update command.\n"
                f"Observed payload: {payload}"
            ),
        )
        _check_equal(
            failures=failures,
            actual=data.get("operation"),
            expected="update-fields",
            message=(
                "Expected result failed: the update did not report the shared "
                "field mutation operation.\n"
                f"Observed payload: {payload}"
            ),
        )
        _check_equal(
            failures=failures,
            actual=data.get("revision"),
            expected=observation.final_head_revision,
            message=(
                "Expected result failed: the reported revision did not match "
                "the final repository HEAD after the multi-field update.\n"
                f"Envelope revision: {data.get('revision')}\n"
                f"Final HEAD: {observation.final_head_revision}"
            ),
        )
    if isinstance(issue, dict):
        _check_equal(
            failures=failures,
            actual=issue.get("summary"),
            expected=config.updated_summary,
            message=(
                "Step 2 failed: the returned issue payload did not preserve "
                "the updated summary.\n"
                f"Observed issue: {issue}"
            ),
        )
        _check_equal(
            failures=failures,
            actual=issue.get("priority"),
            expected=config.updated_priority_id,
            message=(
                "Step 2 failed: the returned issue payload did not resolve "
                "the updated priority to the canonical id.\n"
                f"Observed issue: {issue}"
            ),
        )
        _check_equal(
            failures=failures,
            actual=issue.get("assignee"),
            expected=config.updated_assignee,
            message=(
                "Step 2 failed: the returned issue payload did not preserve "
                "the updated assignee.\n"
                f"Observed issue: {issue}"
            ),
        )
        _check_equal(
            failures=failures,
            actual=issue.get("labels"),
            expected=list(config.updated_labels),
            message=(
                "Step 2 failed: the returned issue payload did not preserve "
                "the updated labels.\n"
                f"Observed issue: {issue}"
            ),
        )
        _check_equal(
            failures=failures,
            actual=issue.get("storagePath"),
            expected=observation.main_file_relative_path,
            message=(
                "Expected result failed: the updated issue payload did not "
                "point to the canonical markdown file path.\n"
                f"Observed issue: {issue}"
            ),
        )
    elif payload is not None:
        failures.append(
            "Step 2 failed: the success envelope did not include an updated "
            f"issue object.\nObserved payload: {payload}"
        )

    _check_equal(
        failures=failures,
        actual=observation.final_commit_count,
        expected=observation.initial_commit_count + 1,
        message=(
            "Step 2 failed: the multi-field update did not persist as exactly "
            "one new Git commit.\n"
            f"Initial commit count: {observation.initial_commit_count}\n"
            f"Final commit count: {observation.final_commit_count}\n"
            f"Latest commit subject: {observation.latest_commit_subject}"
        ),
    )
    _check_not_equal(
        failures=failures,
        actual=observation.initial_head_revision,
        unexpected=observation.final_head_revision,
        message=(
            "Step 2 failed: the repository HEAD did not change after the "
            "multi-field update command completed.\n"
            f"Initial HEAD: {observation.initial_head_revision}\n"
            f"Final HEAD: {observation.final_head_revision}"
        ),
    )
    _check_equal(
        failures=failures,
        actual=observation.latest_commit_subject,
        expected=config.expected_commit_subject,
        message=(
            "Expected result failed: the latest Git commit was not dedicated "
            "to the single issue field update.\n"
            f"Observed commit subject: {observation.latest_commit_subject}"
        ),
    )
    _check_false(
        failures=failures,
        condition=bool(observation.git_status.strip()),
        message=(
            "Expected result failed: the repository worktree was not clean "
            "after the update commit completed.\n"
            f"git status --short:\n{observation.git_status}"
        ),
    )

    main_file = observation.main_file_content
    _check_in(
        failures=failures,
        member='summary: "New Title"',
        container=main_file,
        message=(
            "Step 2 failed: main.md did not visibly show the updated "
            "summary.\n"
            f"Observed {observation.main_file_relative_path} contents:\n"
            f"{main_file}"
        ),
    )
    _check_in(
        failures=failures,
        member="priority: high",
        container=main_file,
        message=(
            "Step 2 failed: main.md did not visibly show the updated "
            "canonical priority id.\n"
            f"Observed {observation.main_file_relative_path} contents:\n"
            f"{main_file}"
        ),
    )
    _check_in(
        failures=failures,
        member="assignee: user1",
        container=main_file,
        message=(
            "Step 2 failed: main.md did not visibly show the updated "
            "assignee.\n"
            f"Observed {observation.main_file_relative_path} contents:\n"
            f"{main_file}"
        ),
    )
    _check_in(
        failures=failures,
        member='labels: ["bug","ai"]',
        container=main_file,
        message=(
            "Step 2 failed: main.md did not visibly show the updated "
            "labels.\n"
            f"Observed {observation.main_file_relative_path} contents:\n"
            f"{main_file}"
        ),
    )
    _check_in(
        failures=failures,
        member="# Summary",
        container=main_file,
        message=(
            "Human-style verification failed: the issue markdown did not "
            "show the rendered summary section after the update.\n"
            f"Observed {observation.main_file_relative_path} contents:\n"
            f"{main_file}"
        ),
    )
    _check_in(
        failures=failures,
        member=config.updated_summary,
        container=main_file,
        message=(
            "Human-style verification failed: the updated issue markdown "
            "did not show the new summary text in the rendered content.\n"
            f"Observed {observation.main_file_relative_path} contents:\n"
            f"{main_file}"
        ),
    )
    _check_not_in(
        failures=failures,
        member=config.initial_summary,
        container=main_file,
        message=(
            "Expected result failed: main.md still showed the original "
            "summary after the update completed.\n"
            f"Observed {observation.main_file_relative_path} contents:\n"
            f"{main_file}"
        ),
    )
    _check_not_in(
        failures=failures,
        member=f"assignee: {config.initial_assignee}",
        container=main_file,
        message=(
            "Expected result failed: main.md still showed the original "
            "assignee after the update completed.\n"
            f"Observed {observation.main_file_relative_path} contents:\n"
            f"{main_file}"
        ),
    )

    for fragment in (
        f'"command": "{config.expected_command_name}"',
        '"summary": "New Title"',
        '"priority": "high"',
        '"assignee": "user1"',
        '"labels": [',
        '"bug"',
        '"ai"',
        f'"revision": "{observation.final_head_revision}"',
    ):
        _check_in(
            failures=failures,
            member=fragment,
            container=observation.result.stdout,
            message=(
                "Human-style verification failed: the visible CLI JSON "
                "response did not show the expected updated issue "
                "details.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}"
            ),
        )

    return Ts460Evaluation(
        config=config,
        observation=observation,
        failures=tuple(failures),
    )


def _successful_envelope_or_failures(
    *,
    result: CliCommandResult,
    failure_prefix: str,
    failures: list[str],
    config: TrackStateCliMultiFieldUpdateConfig,
) -> dict[str, object] | None:
    _check_true(
        failures=failures,
        condition=result.succeeded,
        message=(
            f"{failure_prefix}: the multi-field update command did not "
            "complete successfully.\n"
            f"Executed command: {result.command_text}\n"
            f"Exit code: {result.exit_code}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        ),
    )
    payload = result.json_payload
    if not isinstance(payload, dict):
        failures.append(
            f"{failure_prefix}: the CLI did not return a single JSON success "
            "envelope.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        return None
    missing_top_level_keys = [
        key for key in config.required_top_level_keys if key not in payload
    ]
    _check_false(
        failures=failures,
        condition=bool(missing_top_level_keys),
        message=(
            f"{failure_prefix}: the success envelope was missing required "
            "top-level keys.\n"
            f"Missing keys: {missing_top_level_keys}\n"
            f"Observed payload: {payload}"
        ),
    )
    _check_true(
        failures=failures,
        condition=payload.get("ok") is True,
        message=(
            f"{failure_prefix}: the envelope reported a non-success result.\n"
            f"Observed payload: {payload}"
        ),
    )
    data = payload.get("data")
    if not isinstance(data, dict):
        failures.append(
            f"{failure_prefix}: the envelope data payload was not an "
            f"object.\nObserved payload: {payload}"
        )
        return payload
    missing_data_keys = [
        key for key in config.required_data_keys if key not in data
    ]
    _check_false(
        failures=failures,
        condition=bool(missing_data_keys),
        message=(
            f"{failure_prefix}: the envelope data object was missing "
            "required keys.\n"
            f"Missing keys: {missing_data_keys}\n"
            f"Observed payload: {payload}"
        ),
    )
    return payload


def _check_true(*, failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _check_false(*, failures: list[str], condition: bool, message: str) -> None:
    _check_true(failures=failures, condition=not condition, message=message)


def _check_equal(
    *,
    failures: list[str],
    actual: object,
    expected: object,
    message: str,
) -> None:
    if actual != expected:
        failures.append(message)


def _check_not_equal(
    *,
    failures: list[str],
    actual: object,
    unexpected: object,
    message: str,
) -> None:
    if actual == unexpected:
        failures.append(message)


def _check_in(
    *,
    failures: list[str],
    member: str,
    container: str,
    message: str,
) -> None:
    if member not in container:
        failures.append(message)


def _check_not_in(
    *,
    failures: list[str],
    member: str,
    container: str,
    message: str,
) -> None:
    if member in container:
        failures.append(message)


def _result_context(
    evaluation: Ts460Evaluation | None,
) -> dict[str, object]:
    observation = evaluation.observation if evaluation is not None else None
    config = evaluation.config if evaluation is not None else None
    return {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "test_file": TEST_FILE_PATH,
        "run_command": RUN_COMMAND,
        "discover_command": DISCOVER_COMMAND,
        "os": platform.platform(),
        "requested_steps": list(REQUEST_STEPS),
        "expected_result": EXPECTED_RESULT,
        "issue_key": config.issue_key if config is not None else "TS-1",
        "repository_path": observation.repository_path if observation is not None else None,
        "executed_command": (
            observation.executed_command_text if observation is not None else None
        ),
        "requested_command": (
            observation.requested_command_text if observation is not None else None
        ),
        "fallback_reason": observation.fallback_reason if observation is not None else None,
        "main_file_path": (
            observation.main_file_relative_path if observation is not None else None
        ),
        "main_file_content": (
            observation.main_file_content if observation is not None else None
        ),
        "stdout": observation.result.stdout if observation is not None else None,
        "stderr": observation.result.stderr if observation is not None else None,
        "exit_code": observation.result.exit_code if observation is not None else None,
        "initial_head_revision": (
            observation.initial_head_revision if observation is not None else None
        ),
        "final_head_revision": (
            observation.final_head_revision if observation is not None else None
        ),
        "initial_commit_count": (
            observation.initial_commit_count if observation is not None else None
        ),
        "final_commit_count": (
            observation.final_commit_count if observation is not None else None
        ),
        "latest_commit_subject": (
            observation.latest_commit_subject if observation is not None else None
        ),
        "git_status": observation.git_status if observation is not None else None,
    }


def _write_pass_outputs(evaluation: Ts460Evaluation) -> None:
    context = _result_context(evaluation)
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
    JIRA_COMMENT_PATH.write_text(_jira_comment(context, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(context, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(context, passed=True), encoding="utf-8")


def _write_failure_outputs(
    evaluation: Ts460Evaluation | None,
    *,
    error_message: str,
    trace: str,
    product_failure: bool,
) -> None:
    context = _result_context(evaluation)
    context["error_message"] = error_message
    context["trace"] = trace
    context["failures"] = list(evaluation.failures) if evaluation is not None else []
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
    JIRA_COMMENT_PATH.write_text(_jira_comment(context, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_pr_body(context, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_response(context, passed=False), encoding="utf-8")
    if product_failure:
        BUG_DESCRIPTION_PATH.write_text(_bug_description(context), encoding="utf-8")
    else:
        BUG_DESCRIPTION_PATH.unlink(missing_ok=True)


def _jira_comment(context: dict[str, object], *, passed: bool) -> str:
    if passed:
        return "\n".join(
            [
                "h3. TS-460 automated result",
                "",
                "*Status:* PASSED",
                "",
                "*What automation checked:*",
                f"* Executed the live public command {{code}}{context['executed_command']}{{code}}.",
                (
                "* Verified the CLI returned one success envelope for "
                    "{{ticket-update}} and reported one {{update-fields}} operation."
                ),
                (
                    f"* Verified {{{{{context['main_file_path']}}}}} reflected "
                    "{{summary: \"New Title\"}}, {{priority: high}}, {{assignee: user1}}, "
                    "and {{labels: [\"bug\",\"ai\"]}}."
                ),
                (
                    f"* Verified Git history advanced from "
                    f"{{{{{context['initial_commit_count']}}}}} to "
                    f"{{{{{context['final_commit_count']}}}}} commit(s), the HEAD revision "
                    f"changed to {{{{{context['final_head_revision']}}}}}, and the latest "
                    f"subject was {{{{{context['latest_commit_subject']}}}}}."
                ),
                "",
                "*Human-style verification:*",
                (
                    "* Confirmed the visible terminal JSON showed the updated summary, "
                    "priority, assignee, labels, and revision a user would inspect."
                ),
                (
                    f"* Confirmed {{{{{context['main_file_path']}}}}} visibly showed the "
                    "{{# Summary}} section with {{New Title}} and the updated frontmatter."
                ),
                "",
                "*Observed result:* Matched the expected result.",
                "",
                "*Test file:*",
                "{code}",
                TEST_FILE_PATH,
                "{code}",
                "",
                "*Run command:*",
                "{code:bash}",
                RUN_COMMAND,
                "{code}",
            ]
        )

    failures = context.get("failures", [])
    failure_lines = [
        f"* {failure}" for failure in failures[:6]
    ] or ["* The public multi-field update flow failed before the expected success envelope was produced."]
    return "\n".join(
        [
            "h3. TS-460 automated result",
            "",
            "*Status:* FAILED",
            "",
            "*What automation checked:*",
            f"* Executed the live public command {{code}}{context['executed_command']}{{code}} against a disposable Local Git repository.",
            (
                f"* Inspected the visible CLI JSON output, "
                f"{{{{{context['main_file_path']}}}}}, commit counts, HEAD revision, and latest commit subject."
            ),
            "",
            "*Which step failed and why:*",
            *failure_lines,
            "",
            "*Human-style verification:*",
            (
                "* Checked the visible terminal JSON exactly as a user would after "
                "running the command."
            ),
            (
                f"* Checked {{{{{context['main_file_path']}}}}} as a user-visible issue "
                "artifact to confirm whether the new summary and fields appeared."
            ),
            "",
            "*Observed result:*",
            (
                f"* The CLI returned exit code {{{{{context['exit_code']}}}}} with "
                f"{{INVALID_ARGUMENT}} instead of a success envelope."
            ),
            (
                f"* The latest commit subject stayed {{{{{context['latest_commit_subject']}}}}}, "
                "so no update commit was created."
            ),
            (
                f"* {{{{{context['main_file_path']}}}}} still showed the original "
                "{{summary: \"Old Title\"}}, {{priority: low}}, {{assignee: old-user}}, "
                "and {{labels: [\"legacy\"]}}."
            ),
            "",
            "*Exact error:*",
            "{code}",
            str(context.get("error_message", "")),
            "{code}",
            "",
            "*Run command:*",
            "{code:bash}",
            RUN_COMMAND,
            "{code}",
        ]
    )


def _pr_body(context: dict[str, object], *, passed: bool) -> str:
    if passed:
        return "\n".join(
            [
                f"## {TICKET_KEY} automated result",
                "",
                "**Status:** PASSED",
                "",
                "### What automation checked",
                f"- Executed the live public command `{context['executed_command']}`.",
                "- Verified the CLI returned one `ticket-update` success envelope with one `update-fields` operation.",
                f"- Verified `{context['main_file_path']}` showed `summary: \"New Title\"`, `priority: high`, `assignee: user1`, and `labels: [\"bug\",\"ai\"]`.",
                f"- Verified Git history advanced from `{context['initial_commit_count']}` to `{context['final_commit_count']}` commit(s) and the latest subject was `{context['latest_commit_subject']}`.",
                "",
                "### Human-style verification",
                "- Checked the visible terminal JSON a user would read after running the command.",
                f"- Checked `{context['main_file_path']}` to confirm the rendered `# Summary` section displayed `New Title` in the right place.",
                "",
                "**Observed result:** Matched the expected result.",
                "",
                "### Test file",
                f"- `{TEST_FILE_PATH}`",
                "",
                "### Run command",
                "```bash",
                RUN_COMMAND,
                "```",
            ]
        )

    failures = context.get("failures", [])
    failure_lines = [f"- {failure}" for failure in failures[:6]]
    return "\n".join(
        [
            f"## {TICKET_KEY} automated result",
            "",
            "**Status:** FAILED",
            "",
            "### What automation checked",
            f"- Executed the live public command `{context['executed_command']}` against a disposable local Git repository.",
            f"- Inspected the CLI JSON response, `{context['main_file_path']}`, Git commit count, HEAD revision, and latest commit subject.",
            "",
            "### Which step failed and why",
            *failure_lines,
            "",
            "### Human-style verification",
            "- Checked the visible terminal JSON output a user would inspect after the command finished.",
            f"- Checked `{context['main_file_path']}` to confirm whether the summary and frontmatter actually changed.",
            "",
            "### Observed result",
            f"- The CLI exited with code `{context['exit_code']}` and returned `INVALID_ARGUMENT` instead of a success envelope.",
            f"- `{context['main_file_path']}` still rendered `Old Title` under `# Summary` and kept the original frontmatter values.",
            f"- Git history did not advance: commit count stayed `{context['final_commit_count']}` and the latest subject remained `{context['latest_commit_subject']}`.",
            "",
            "### Exact error",
            "```text",
            str(context.get("error_message", "")),
            "```",
            "",
            "### Run command",
            "```bash",
            RUN_COMMAND,
            "```",
        ]
    )


def _response(context: dict[str, object], *, passed: bool) -> str:
    if passed:
        return (
            f"{TICKET_KEY} passed. The live public multi-field update command returned "
            "one success envelope, updated TS/TS-1/main.md with the new summary, "
            "priority, assignee, and labels, and created exactly one Git commit."
        )
    return "\n".join(
        [
            f"{TICKET_KEY} failed.",
            "",
            f"Command: `{context['executed_command']}`",
            f"Exit code: `{context['exit_code']}`",
            "",
            f"Error: `{context.get('error_message', '')}`",
            "",
            (
                f"`{context['main_file_path']}` stayed unchanged and Git history did not "
                f"advance beyond `{context['latest_commit_subject']}`."
            ),
        ]
    )


def _bug_description(context: dict[str, object]) -> str:
    return "\n".join(
        [
            f"# {TICKET_KEY}: {TEST_CASE_TITLE}",
            "",
            "## Summary",
            (
                "The live public TrackState CLI multi-field update flow still rejects "
                "the labels array assignment with `INVALID_ARGUMENT`, so the ticket is "
                "not updated, `main.md` stays unchanged, and no Git commit is created."
            ),
            "",
            "## Exact steps to reproduce",
            "1. Execute the public multi-field update command for `TS-1`.",
            "   - **Expected:** The command returns one success envelope for the atomic update.",
            (
                f"   - **Actual:** ❌ The command `{context['executed_command']}` exited with "
                f"code `{context['exit_code']}` and returned `INVALID_ARGUMENT` instead of success."
            ),
            "2. Inspect the CLI JSON response and the issue's `TS/TS-1/main.md` file.",
            "   - **Expected:** The JSON response includes the updated issue and revision, `TS/TS-1/main.md` shows the new summary/priority/labels/assignee, and Git history has one new commit.",
            (
                "   - **Actual:** ❌ The JSON response only contained an error envelope, "
                f"`{context['main_file_path']}` still showed `summary: \"Old Title\"`, "
                "`priority: low`, `assignee: old-user`, and `labels: [\"legacy\"]`, and "
                f"the latest commit subject remained `{context['latest_commit_subject']}`."
            ),
            "",
            "## Actual vs Expected",
            "- **Expected:** One successful `ticket-update` response, updated issue markdown, and exactly one new Git commit.",
            (
                "- **Actual:** The CLI returned `INVALID_ARGUMENT: Field assignments must "
                "use key=value syntax. Invalid value: \"\"ai\"]\".` and left the issue "
                "markdown plus Git history unchanged."
            ),
            "",
            "## Exact error message / assertion failure",
            "```text",
            str(context.get("error_message", "")),
            "",
            str(context.get("trace", "")),
            "```",
            "",
            "## Environment details",
            f"- OS: `{context['os']}`",
            "- Surface: `TrackState CLI`",
            "- Target: `local`",
            f"- Disposable repository path used during run: `{context['repository_path']}`",
            f"- Run command: `{RUN_COMMAND}`",
            f"- Executed CLI command: `{context['executed_command']}`",
            f"- Main issue file: `{context['main_file_path']}`",
            "",
            "## Relevant logs",
            "### CLI stdout",
            "```json",
            str(context.get("stdout", "")).strip(),
            "```",
            "",
            "### CLI stderr",
            "```text",
            str(context.get("stderr", "")).strip(),
            "```",
            "",
            "### Observed issue markdown",
            "```markdown",
            str(context.get("main_file_content", "")).strip(),
            "```",
        ]
    )


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    evaluation: Ts460Evaluation | None = None
    try:
        evaluation = evaluate_ts_460(REPO_ROOT)
        if evaluation.failures:
            raise AssertionError("\n\n".join(evaluation.failures))
        _write_pass_outputs(evaluation)
    except AssertionError as error:
        _write_failure_outputs(
            evaluation,
            error_message=f"AssertionError: {error}",
            trace=traceback.format_exc(),
            product_failure=True,
        )
        raise SystemExit(1) from error
    except Exception as error:  # pragma: no cover - infrastructure failure path
        _write_failure_outputs(
            evaluation,
            error_message=f"{type(error).__name__}: {error}",
            trace=traceback.format_exc(),
            product_failure=False,
        )
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
