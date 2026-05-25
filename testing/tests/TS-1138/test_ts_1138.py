from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_issue_link_types_validator import (  # noqa: E402
    TrackStateCliIssueLinkTypesValidator,
)
from testing.core.config.trackstate_cli_issue_link_types_config import (  # noqa: E402
    TrackStateCliIssueLinkTypesConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.tests.support.live_startup_case_support import (  # noqa: E402
    build_annotated_steps,
    format_human_lines,
    format_step_lines,
    record_human_verification,
    record_step,
    write_test_automation_result,
)
from testing.tests.support.trackstate_cli_issue_link_types_probe_factory import (  # noqa: E402
    create_trackstate_cli_issue_link_types_probe,
)

TICKET_KEY = "TS-1138"
TEST_CASE_TITLE = "Execute synonymous link-type commands — response payloads are identical"
TEST_FILE_PATH = "testing/tests/TS-1138/test_ts_1138.py"
RUN_COMMAND = "mkdir -p outputs && PYTHONPATH=. python3 testing/tests/TS-1138/test_ts_1138.py"
LINKED_BUGS = ["TS-1076"]
LINKED_BUG_NOTES = (
    "Reviewed TS-1076. The merged fix routes `trackstate read issue-link-types` "
    "through the same static metadata as `trackstate read link-types`. This is a "
    "synchronous CLI metadata read, so no extra timing wait is required before "
    "asserting the observed JSON output."
)
REQUEST_STEPS = [
    "Execute command: `trackstate read issue-link-types` and capture the JSON output.",
    "Execute command: `trackstate read link-types` and capture the JSON output.",
    "Compare the two JSON response objects.",
]
EXPECTED_RESULT = (
    "The JSON payloads are identical, confirming that both commands pull from the "
    "same static data source and return the four canonical link types ('blocks', "
    "'relates-to', 'duplicates', 'clones') with correct Jira labels."
)
VISIBLE_OUTPUT_FRAGMENTS = (
    '"id": "blocks"',
    '"name": "Blocks"',
    '"outward": "blocks"',
    '"inward": "is blocked by"',
    '"id": "relates-to"',
    '"outward": "relates to"',
    '"id": "duplicates"',
    '"inward": "is duplicated by"',
    '"id": "clones"',
    '"inward": "is cloned by"',
)

OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)

    config = TrackStateCliIssueLinkTypesConfig.from_defaults()
    expected_payload = [fixture.to_payload() for fixture in config.expected_link_types]
    result: dict[str, Any] = {
        "ticket": TICKET_KEY,
        "test_case_title": TEST_CASE_TITLE,
        "os": platform.platform(),
        "run_command": RUN_COMMAND,
        "test_file_path": TEST_FILE_PATH,
        "expected_result": EXPECTED_RESULT,
        "linked_bugs": LINKED_BUGS,
        "linked_bug_notes": LINKED_BUG_NOTES,
        "framework": "python",
        "surface": "TrackState CLI",
        "environment": "Local Git",
        "repository_root": str(REPO_ROOT),
        "expected_payload": expected_payload,
        "steps": [],
        "human_verification": [],
        "product_failure": False,
    }

    try:
        validator = TrackStateCliIssueLinkTypesValidator(
            probe=create_trackstate_cli_issue_link_types_probe(REPO_ROOT),
        )
        validation = validator.validate(config=config)
        ticket_observation = validation.ticket_observation
        canonical_observation = validation.canonical_observation
        result["ticket_observation"] = _observation_payload(ticket_observation)
        result["canonical_observation"] = _observation_payload(canonical_observation)

        failures: list[str] = []
        ticket_payload, ticket_issues = _evaluate_command_step(
            result=result,
            step=1,
            action=REQUEST_STEPS[0],
            observation=ticket_observation,
            expected_command=config.ticket_command,
            ticket_label="ticket alias",
        )
        canonical_payload, canonical_issues = _evaluate_command_step(
            result=result,
            step=2,
            action=REQUEST_STEPS[1],
            observation=canonical_observation,
            expected_command=config.canonical_command,
            ticket_label="canonical control",
        )
        failures.extend(ticket_issues)
        failures.extend(canonical_issues)

        if (
            ticket_observation.result.exit_code != 0
            and canonical_observation.result.exit_code == 0
        ) or (
            canonical_observation.result.exit_code != 0
            and ticket_observation.result.exit_code == 0
        ):
            result["product_failure"] = True

        compare_issues = _evaluate_comparison_step(
            result=result,
            ticket_payload=ticket_payload,
            canonical_payload=canonical_payload,
            expected_payload=expected_payload,
            ticket_observation=ticket_observation,
            canonical_observation=canonical_observation,
        )
        if compare_issues:
            result["product_failure"] = True
            failures.extend(compare_issues)

        human_issues = _evaluate_human_verification(
            result=result,
            ticket_observation=ticket_observation,
            canonical_observation=canonical_observation,
        )
        if human_issues:
            result["product_failure"] = True
            failures.extend(human_issues)

        if failures:
            raise AssertionError("\n\n".join(failures))

        _write_pass_outputs(result)
    except Exception as error:  # noqa: BLE001
        result["error"] = str(error)
        result["traceback"] = traceback.format_exc()
        if not result.get("product_failure"):
            result["product_failure"] = _looks_like_product_failure(result)
        result["failure_kind"] = "product" if result["product_failure"] else "setup"
        _write_failure_outputs(result)
        raise SystemExit(1) from error


def _evaluate_command_step(
    *,
    result: dict[str, Any],
    step: int,
    action: str,
    observation: TrackStateCliCommandObservation,
    expected_command: tuple[str, ...],
    ticket_label: str,
) -> tuple[list[dict[str, object]] | None, list[str]]:
    issues: list[str] = []
    payload = observation.result.json_payload
    parsed_payload: list[dict[str, object]] | None = None

    if observation.requested_command != expected_command:
        issues.append(
            f"Step {step} failed: expected the {ticket_label} command to be "
            f"`{' '.join(expected_command)}`, but the probe requested "
            f"`{observation.requested_command_text}`.",
        )
    if observation.compiled_binary_path is None:
        issues.append(
            f"Step {step} failed: the {ticket_label} command did not run through a "
            "repository-local compiled CLI binary wrapper.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
    elif observation.executed_command[0] != observation.compiled_binary_path:
        issues.append(
            f"Step {step} failed: the {ticket_label} command did not execute the "
            "expected repository-local compiled binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    if observation.result.exit_code != 0:
        issues.append(
            f"Step {step} failed: `{observation.requested_command_text}` exited with "
            f"code {observation.result.exit_code}.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
    elif not isinstance(payload, list):
        issues.append(
            f"Step {step} failed: `{observation.requested_command_text}` did not return "
            "a JSON array payload.\n"
            f"Observed payload: {payload}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
    elif not all(isinstance(entry, dict) for entry in payload):
        issues.append(
            f"Step {step} failed: `{observation.requested_command_text}` returned a JSON "
            "array containing non-object entries.\n"
            f"Observed payload: {payload}",
        )
    else:
        parsed_payload = [dict(entry) for entry in payload]

    record_step(
        result,
        step=step,
        status="passed" if not issues else "failed",
        action=action,
        observed=(
            f"requested={observation.requested_command_text}; "
            f"executed={observation.executed_command_text}; "
            f"exit_code={observation.result.exit_code}; "
            f"repository={observation.repository_path}; "
            f"payload_entries={len(parsed_payload) if parsed_payload is not None else 'unavailable'}"
        ),
    )
    return parsed_payload, issues


def _evaluate_comparison_step(
    *,
    result: dict[str, Any],
    ticket_payload: list[dict[str, object]] | None,
    canonical_payload: list[dict[str, object]] | None,
    expected_payload: list[dict[str, object]],
    ticket_observation: TrackStateCliCommandObservation,
    canonical_observation: TrackStateCliCommandObservation,
) -> list[str]:
    issues: list[str] = []

    if ticket_payload is None or canonical_payload is None:
        issues.append(
            "Step 3 failed: the JSON payloads could not be compared because one or "
            "both commands did not produce a valid JSON array.\n"
            f"Alias payload: {ticket_observation.result.json_payload}\n"
            f"Canonical payload: {canonical_observation.result.json_payload}",
        )
    else:
        if ticket_payload != canonical_payload:
            issues.append(
                "Step 3 failed: `trackstate read issue-link-types` did not return the "
                "same JSON payload as `trackstate read link-types`.\n"
                f"Alias payload: {json.dumps(ticket_payload, indent=2)}\n"
                f"Canonical payload: {json.dumps(canonical_payload, indent=2)}",
            )
        if ticket_payload != expected_payload:
            issues.append(
                "Expected result failed: the alias command did not return exactly the "
                "four canonical Jira link types.\n"
                f"Expected payload: {json.dumps(expected_payload, indent=2)}\n"
                f"Observed payload: {json.dumps(ticket_payload, indent=2)}",
            )
        if canonical_payload != expected_payload:
            issues.append(
                "Precondition failed: the canonical control command did not return the "
                "expected canonical Jira link type payload.\n"
                f"Expected payload: {json.dumps(expected_payload, indent=2)}\n"
                f"Observed payload: {json.dumps(canonical_payload, indent=2)}",
            )

    record_step(
        result,
        step=3,
        status="passed" if not issues else "failed",
        action=REQUEST_STEPS[2],
        observed=(
            f"alias_matches_canonical={ticket_payload == canonical_payload if ticket_payload is not None and canonical_payload is not None else False}; "
            f"alias_matches_expected={ticket_payload == expected_payload if ticket_payload is not None else False}; "
            f"canonical_matches_expected={canonical_payload == expected_payload if canonical_payload is not None else False}"
        ),
    )
    return issues


def _evaluate_human_verification(
    *,
    result: dict[str, Any],
    ticket_observation: TrackStateCliCommandObservation,
    canonical_observation: TrackStateCliCommandObservation,
) -> list[str]:
    issues: list[str] = []
    missing_alias_fragments = [
        fragment
        for fragment in VISIBLE_OUTPUT_FRAGMENTS
        if fragment not in ticket_observation.result.stdout
    ]
    missing_canonical_fragments = [
        fragment
        for fragment in VISIBLE_OUTPUT_FRAGMENTS
        if fragment not in canonical_observation.result.stdout
    ]
    if missing_alias_fragments:
        issues.append(
            "Human-style verification failed: the visible CLI JSON from "
            "`trackstate read issue-link-types` did not show all expected Jira label "
            "fragments.\n"
            f"Missing fragments: {missing_alias_fragments}\n"
            f"Observed stdout:\n{ticket_observation.result.stdout}",
        )
    if missing_canonical_fragments:
        issues.append(
            "Human-style verification failed: the visible CLI JSON from "
            "`trackstate read link-types` did not show all expected Jira label "
            "fragments.\n"
            f"Missing fragments: {missing_canonical_fragments}\n"
            f"Observed stdout:\n{canonical_observation.result.stdout}",
        )

    record_human_verification(
        result,
        check=(
            "Read the CLI JSON output as a user would and verified the visible alias "
            "and canonical command output both listed the four Jira link types with "
            "their inward and outward labels."
        ),
        observed=(
            f"alias_stdout={_snippet(ticket_observation.result.stdout)!r}; "
            f"canonical_stdout={_snippet(canonical_observation.result.stdout)!r}"
        ),
    )
    return issues


def _observation_payload(
    observation: TrackStateCliCommandObservation,
) -> dict[str, Any]:
    return {
        "requested_command": list(observation.requested_command),
        "requested_command_text": observation.requested_command_text,
        "executed_command": list(observation.executed_command),
        "executed_command_text": observation.executed_command_text,
        "fallback_reason": observation.fallback_reason,
        "repository_path": observation.repository_path,
        "compiled_binary_path": observation.compiled_binary_path,
        "result": {
            "exit_code": observation.result.exit_code,
            "stdout": observation.result.stdout,
            "stderr": observation.result.stderr,
            "json_payload": observation.result.json_payload,
        },
    }


def _looks_like_product_failure(result: dict[str, Any]) -> bool:
    ticket_observation = result.get("ticket_observation")
    canonical_observation = result.get("canonical_observation")
    if not isinstance(ticket_observation, dict) or not isinstance(canonical_observation, dict):
        return False
    ticket_result = ticket_observation.get("result")
    canonical_result = canonical_observation.get("result")
    if not isinstance(ticket_result, dict) or not isinstance(canonical_result, dict):
        return False
    ticket_exit = ticket_result.get("exit_code")
    canonical_exit = canonical_result.get("exit_code")
    ticket_payload = ticket_result.get("json_payload")
    canonical_payload = canonical_result.get("json_payload")
    if ticket_exit == 0 and canonical_exit == 0:
        return True
    if ticket_exit != 0 and canonical_exit == 0:
        return True
    if ticket_exit == 0 and canonical_exit != 0:
        return True
    return isinstance(ticket_payload, list) or isinstance(canonical_payload, list)


def _write_pass_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(RESULT_PATH, passed=True)
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=True), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=True), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=True), encoding="utf-8")


def _write_failure_outputs(result: dict[str, Any]) -> None:
    BUG_DESCRIPTION_PATH.unlink(missing_ok=True)
    write_test_automation_result(
        RESULT_PATH,
        passed=False,
        error=_exact_error_summary(result),
    )
    JIRA_COMMENT_PATH.write_text(_build_jira_comment(result, passed=False), encoding="utf-8")
    PR_BODY_PATH.write_text(_build_pr_body(result, passed=False), encoding="utf-8")
    RESPONSE_PATH.write_text(_build_response_summary(result, passed=False), encoding="utf-8")
    if result.get("failure_kind") == "product":
        BUG_DESCRIPTION_PATH.write_text(_build_bug_description(result), encoding="utf-8")


def _build_jira_comment(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    actual_result = (
        "Both commands returned the same four-entry JSON array, and the visible CLI "
        "output showed the canonical Jira labels for blocks, relates-to, duplicates, "
        "and clones."
        if passed
        else str(result.get("error", "The expected alias parity was not observed."))
    )
    lines = [
        f"h3. {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"*Test case*: {TEST_CASE_TITLE}",
        f"*Environment*: Surface={result.get('surface')} | Mode={result.get('environment')} | OS={result.get('os')}",
        f"*Run command*: {{{{code}}}}{RUN_COMMAND}{{{{code}}}}",
        f"*Linked bugs considered*: {', '.join(LINKED_BUGS)}",
        f"*Linked bug notes*: {LINKED_BUG_NOTES}",
        "",
        "h4. Automation checks",
        *format_step_lines(result, jira=True),
        "",
        "h4. Real user-style verification",
        *format_human_lines(result, jira=True),
        "",
        "h4. Expected result",
        EXPECTED_RESULT,
        "",
        "h4. Actual result",
        actual_result,
    ]
    if not passed:
        lines.extend(
            [
                "",
                "h4. Assertion / error",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_pr_body(result: dict[str, Any], *, passed: bool) -> str:
    status_icon = "✅" if passed else "❌"
    status_word = "PASSED" if passed else "FAILED"
    actual_result = (
        "Both commands returned the same four-entry JSON array, and the visible CLI "
        "output showed the canonical Jira labels for blocks, relates-to, duplicates, "
        "and clones."
        if passed
        else str(result.get("error", "The expected alias parity was not observed."))
    )
    lines = [
        f"## {status_icon} Automated test {status_word} — {TICKET_KEY}",
        "",
        f"**Test case:** {TEST_CASE_TITLE}",
        (
            f"**Environment:** Surface={result.get('surface')} | "
            f"Mode={result.get('environment')} | OS={result.get('os')}"
        ),
        f"**Run command:** `{RUN_COMMAND}`",
        f"**Linked bugs considered:** {', '.join(LINKED_BUGS)}",
        f"**Linked bug notes:** {LINKED_BUG_NOTES}",
        "",
        "### Automation checks",
        *format_step_lines(result, jira=False),
        "",
        "### Real user-style verification",
        *format_human_lines(result, jira=False),
        "",
        "### Expected result",
        EXPECTED_RESULT,
        "",
        "### Actual result",
        actual_result,
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Assertion / error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ],
        )
    return "\n".join(lines) + "\n"


def _build_response_summary(result: dict[str, Any], *, passed: bool) -> str:
    status_word = "PASSED" if passed else "FAILED"
    actual_result = (
        "Both commands returned the same four canonical Jira link types."
        if passed
        else str(result.get("error", "The alias parity expectation was not observed."))
    )
    return (
        f"# {TICKET_KEY} {status_word}\n\n"
        f"**Test case:** {TEST_CASE_TITLE}\n\n"
        f"**Expected result:** {EXPECTED_RESULT}\n\n"
        f"**Actual result:** {actual_result}\n"
    )


def _build_bug_description(result: dict[str, Any]) -> str:
    ticket_observation = result.get("ticket_observation", {})
    canonical_observation = result.get("canonical_observation", {})
    return "\n".join(
        [
            f"# Bug report — {TICKET_KEY}",
            "",
            f"## Summary",
            str(result.get("error", "The CLI link-type alias parity scenario failed.")),
            "",
            "## Steps to reproduce",
            *build_annotated_steps(result, request_steps=REQUEST_STEPS),
            "",
            "## Expected result",
            EXPECTED_RESULT,
            "",
            "## Actual result",
            str(result.get("error", "The alias parity behavior was not observed.")),
            "",
            "## Environment",
            f"- Surface: {result.get('surface')}",
            f"- Mode: {result.get('environment')}",
            f"- OS: {result.get('os')}",
            f"- Repository root: {result.get('repository_root')}",
            f"- Alias repository path: {ticket_observation.get('repository_path')}",
            f"- Canonical repository path: {canonical_observation.get('repository_path')}",
            f"- Run command: {RUN_COMMAND}",
            "",
            "## Exact assertion / error",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Alias command logs",
            "```text",
            _format_observation_logs(ticket_observation),
            "```",
            "",
            "## Canonical command logs",
            "```text",
            _format_observation_logs(canonical_observation),
            "```",
        ],
    ) + "\n"


def _format_observation_logs(observation: object) -> str:
    if not isinstance(observation, dict):
        return "Observation unavailable."
    result = observation.get("result")
    if not isinstance(result, dict):
        return json.dumps(observation, indent=2)
    return (
        f"requested_command={observation.get('requested_command_text')}\n"
        f"executed_command={observation.get('executed_command_text')}\n"
        f"repository_path={observation.get('repository_path')}\n"
        f"compiled_binary_path={observation.get('compiled_binary_path')}\n"
        f"fallback_reason={observation.get('fallback_reason')}\n"
        f"exit_code={result.get('exit_code')}\n"
        f"stdout:\n{result.get('stdout', '')}\n"
        f"stderr:\n{result.get('stderr', '')}"
    )


def _exact_error_summary(result: dict[str, Any]) -> str:
    error = str(result.get("error", "")).strip()
    if result.get("traceback"):
        return f"AssertionError: {error}" if error else "AssertionError"
    return error or "AssertionError"


def _snippet(text: str, *, limit: int = 240) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[:limit].rstrip()}..."


if __name__ == "__main__":
    main()
