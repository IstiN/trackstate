from __future__ import annotations

import json
import platform
import sys
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from testing.components.services.trackstate_cli_self_link_guard_validator import (  # noqa: E402
    TrackStateCliSelfLinkGuardValidator,
)
from testing.core.config.trackstate_cli_self_link_guard_config import (  # noqa: E402
    TrackStateCliSelfLinkGuardConfig,
)
from testing.core.models.trackstate_cli_command_observation import (  # noqa: E402
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_self_link_guard_result import (  # noqa: E402
    TrackStateCliSelfLinkGuardObservation,
    TrackStateCliSelfLinkGuardValidationResult,
    TrackStateCliSelfLinkLinksJsonSnapshot,
)
from testing.tests.support.trackstate_cli_self_link_guard_probe_factory import (  # noqa: E402
    create_trackstate_cli_self_link_guard_probe,
)

TICKET_KEY = "TS-663"
TICKET_SUMMARY = "Link issue to itself using mixed-case keys — CLI returns exit code 2"
OUTPUTS_DIR = REPO_ROOT / "outputs"
JIRA_COMMENT_PATH = OUTPUTS_DIR / "jira_comment.md"
PR_BODY_PATH = OUTPUTS_DIR / "pr_body.md"
RESPONSE_PATH = OUTPUTS_DIR / "response.md"
RESULT_PATH = OUTPUTS_DIR / "test_automation_result.json"
BUG_DESCRIPTION_PATH = OUTPUTS_DIR / "bug_description.md"
TEST_FILE_PATH = "testing/tests/TS-663/test_ts_663.py"
RUN_COMMAND = "python3 testing/tests/TS-663/test_ts_663.py"


class Ts663MixedCaseSelfLinkGuardScenario:
    def __init__(self) -> None:
        self.repository_root = REPO_ROOT
        self.config_path = self.repository_root / "testing/tests/TS-663/config.yaml"
        self.config = TrackStateCliSelfLinkGuardConfig.from_file(self.config_path)
        self.validator = TrackStateCliSelfLinkGuardValidator(
            probe=create_trackstate_cli_self_link_guard_probe(self.repository_root)
        )

    def execute(self) -> tuple[dict[str, object], list[str]]:
        validation = self.validator.validate(config=self.config)
        result = self._build_result(validation)
        failures: list[str] = []
        failures.extend(self._validate_precondition(validation, result))
        failures.extend(self._validate_command_execution(validation.observation, result))
        failures.extend(self._validate_runtime(validation.observation, result))
        failures.extend(self._validate_metadata_state(validation.observation, result))
        failures.extend(self._validate_human_verification(validation.observation, result))
        return result, failures

    def _build_result(
        self,
        validation: TrackStateCliSelfLinkGuardValidationResult,
    ) -> dict[str, object]:
        create_payload = validation.observation.issue_a_create_observation.result.json_payload
        create_payload_dict = create_payload if isinstance(create_payload, dict) else None
        create_data = (
            create_payload_dict.get("data")
            if isinstance(create_payload_dict, dict)
            else None
        )
        create_data_dict = create_data if isinstance(create_data, dict) else None
        created_issue = (
            create_data_dict.get("issue")
            if isinstance(create_data_dict, dict)
            else None
        )
        created_issue_dict = created_issue if isinstance(created_issue, dict) else None

        link_payload = validation.observation.self_link_observation.result.json_payload
        link_payload_dict = link_payload if isinstance(link_payload, dict) else None
        link_error = (
            link_payload_dict.get("error") if isinstance(link_payload_dict, dict) else None
        )
        link_error_dict = link_error if isinstance(link_error, dict) else None
        link_target = (
            link_payload_dict.get("target")
            if isinstance(link_payload_dict, dict)
            else None
        )
        link_target_dict = link_target if isinstance(link_target, dict) else None

        return {
            "ticket": TICKET_KEY,
            "ticket_summary": TICKET_SUMMARY,
            "config_path": str(self.config_path),
            "compiled_source_ref": self.config.compiled_source_ref,
            "issue_a_create_command": (
                validation.observation.issue_a_create_observation.requested_command_text
            ),
            "requested_command": validation.observation.self_link_observation.requested_command_text,
            "executed_command": validation.observation.self_link_observation.executed_command_text,
            "compiled_binary_path": (
                validation.observation.self_link_observation.compiled_binary_path
            ),
            "fallback_reason": validation.observation.self_link_observation.fallback_reason,
            "repository_path": validation.observation.self_link_observation.repository_path,
            "provider": link_payload_dict.get("provider")
            if isinstance(link_payload_dict, dict)
            else None,
            "target_type": link_target_dict.get("type")
            if isinstance(link_target_dict, dict)
            else None,
            "target_value": link_target_dict.get("value")
            if isinstance(link_target_dict, dict)
            else None,
            "issue_a_payload": create_payload_dict,
            "created_issue": created_issue_dict,
            "payload": link_payload_dict,
            "error": link_error_dict,
            "observed_error_code": link_error_dict.get("code")
            if isinstance(link_error_dict, dict)
            else None,
            "observed_error_category": link_error_dict.get("category")
            if isinstance(link_error_dict, dict)
            else None,
            "observed_error_message": link_error_dict.get("message")
            if isinstance(link_error_dict, dict)
            else None,
            "observed_error_exit_code": link_error_dict.get("exitCode")
            if isinstance(link_error_dict, dict)
            else None,
            "observed_error_details": link_error_dict.get("details")
            if isinstance(link_error_dict, dict)
            else None,
            "stdout": validation.observation.self_link_observation.result.stdout,
            "stderr": validation.observation.self_link_observation.result.stderr,
            "process_exit_code": validation.observation.self_link_observation.result.exit_code,
            "links_json_relative_path": validation.observation.links_json_relative_path,
            "links_json_content": validation.observation.links_json_content,
            "links_json_payload": validation.observation.links_json_payload,
            "discovered_links_json_files": list(
                validation.observation.discovered_links_json_files
            ),
            "discovered_links_json_snapshots": [
                _snapshot_to_dict(snapshot)
                for snapshot in validation.observation.discovered_links_json_snapshots
            ],
            "steps": [],
            "human_verification": [],
        }

    def _validate_precondition(
        self,
        validation: TrackStateCliSelfLinkGuardValidationResult,
        result: dict[str, object],
    ) -> list[str]:
        observation = validation.observation.issue_a_create_observation
        failures: list[str] = []
        expected_command = self.config.issue_a_create_command(observation.repository_path)
        if observation.requested_command != expected_command:
            failures.append(
                "Precondition failed: TS-663 must create Issue A in the disposable Local "
                "Git repository before attempting the mixed-case self-referencing link.\n"
                f"Expected command: {' '.join(expected_command)}\n"
                f"Observed command: {observation.requested_command_text}"
            )
        if observation.compiled_binary_path is None:
            failures.append(
                "Precondition failed: TS-663 must execute a repository-local compiled "
                "CLI binary.\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}"
            )
        if observation.result.exit_code != 0:
            failures.append(
                "Precondition failed: creating Issue A did not complete successfully.\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )

        payload = observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        if not isinstance(payload_dict, dict):
            failures.append(
                "Precondition failed: the Issue A create command did not return a JSON "
                "object envelope.\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}"
            )
        else:
            if payload_dict.get("ok") is not True:
                failures.append(
                    "Precondition failed: the Issue A create response was not a success "
                    "envelope.\n"
                    f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
                )
            data = payload_dict.get("data")
            data_dict = data if isinstance(data, dict) else None
            issue = data_dict.get("issue") if isinstance(data_dict, dict) else None
            issue_dict = issue if isinstance(issue, dict) else None
            if not isinstance(issue_dict, dict):
                failures.append(
                    "Precondition failed: the Issue A create response did not include the "
                    "created issue payload.\n"
                    f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
                )
            else:
                if issue_dict.get("key") != self.config.issue_a_key:
                    failures.append(
                        "Precondition failed: the Issue A create response returned an "
                        "unexpected issue key.\n"
                        f"Expected key: {self.config.issue_a_key}\n"
                        f"Observed issue: {json.dumps(issue_dict, indent=2, sort_keys=True)}"
                    )
                if issue_dict.get("summary") != self.config.issue_a_summary:
                    failures.append(
                        "Precondition failed: the Issue A create response did not preserve "
                        "the requested summary.\n"
                        f"Expected summary: {self.config.issue_a_summary}\n"
                        f"Observed issue: {json.dumps(issue_dict, indent=2, sort_keys=True)}"
                    )

        if failures:
            _record_step(
                result,
                step=0,
                status="failed",
                action="Create Issue A in a disposable local-git TrackState repository.",
                observed=_summarize_failures(failures),
            )
        else:
            created_issue = result.get("created_issue") or {}
            _record_step(
                result,
                step=0,
                status="passed",
                action="Create Issue A in a disposable local-git TrackState repository.",
                observed=(
                    f"issue_key={created_issue.get('key')}; "
                    f"summary={created_issue.get('summary')}; "
                    f"repository_path={observation.repository_path}"
                ),
            )
        return failures

    def _validate_command_execution(
        self,
        observation: TrackStateCliSelfLinkGuardObservation,
        result: dict[str, object],
    ) -> list[str]:
        link_observation = observation.self_link_observation
        failures: list[str] = []
        expected_command = self.config.self_link_command(link_observation.repository_path)
        if link_observation.requested_command != expected_command:
            failures.append(
                "Step 1 failed: TS-663 must execute the exact mixed-case self-link "
                "command from the ticket against the disposable Local Git repository.\n"
                f"Expected command: {' '.join(expected_command)}\n"
                f"Observed command: {link_observation.requested_command_text}"
            )
        if link_observation.compiled_binary_path is None:
            failures.append(
                "Step 1 failed: TS-663 did not run a repository-local compiled CLI "
                "binary.\n"
                f"Executed command: {link_observation.executed_command_text}\n"
                f"Fallback reason: {link_observation.fallback_reason}"
            )
        elif link_observation.executed_command[0] != link_observation.compiled_binary_path:
            failures.append(
                "Step 1 failed: TS-663 did not execute the compiled local CLI binary "
                "for the mixed-case self-link command.\n"
                f"Executed command: {link_observation.executed_command_text}\n"
                f"Compiled binary path: {link_observation.compiled_binary_path}"
            )

        if failures:
            _record_step(
                result,
                step=1,
                status="failed",
                action=(
                    'Execute `trackstate ticket link --key TS-1 --target-key ts-1 '
                    '--type "relates to"`.'
                ),
                observed=_summarize_failures(failures),
            )
        else:
            _record_step(
                result,
                step=1,
                status="passed",
                action=(
                    'Execute `trackstate ticket link --key TS-1 --target-key ts-1 '
                    '--type "relates to"`.'
                ),
                observed=(
                    f"requested_command={link_observation.requested_command_text}; "
                    f"executed_command={link_observation.executed_command_text}"
                ),
            )
        return failures

    def _validate_runtime(
        self,
        observation: TrackStateCliSelfLinkGuardObservation,
        result: dict[str, object],
    ) -> list[str]:
        link_observation = observation.self_link_observation
        failures: list[str] = []
        payload = link_observation.result.json_payload
        payload_dict = payload if isinstance(payload, dict) else None
        error = payload_dict.get("error") if isinstance(payload_dict, dict) else None
        error_dict = error if isinstance(error, dict) else None

        if link_observation.result.exit_code != self.config.expected_error_exit_code:
            failures.append(
                "Step 2 failed: the mixed-case self-link command did not return the "
                "expected validation exit code.\n"
                f"Expected exit code: {self.config.expected_error_exit_code}\n"
                f"Observed exit code: {link_observation.result.exit_code}\n"
                f"stdout:\n{link_observation.result.stdout}\n"
                f"stderr:\n{link_observation.result.stderr}"
            )
        if not isinstance(payload_dict, dict):
            failures.append(
                "Step 2 failed: the CLI did not return a JSON object failure envelope "
                "for the mixed-case self-link command.\n"
                f"stdout:\n{link_observation.result.stdout}\n"
                f"stderr:\n{link_observation.result.stderr}"
            )
        else:
            if payload_dict.get("ok") is not False:
                failures.append(
                    "Step 2 failed: the JSON envelope did not report a failed mutation "
                    "for the mixed-case self-link command.\n"
                    f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
                )
            if payload_dict.get("provider") != "local-git":
                failures.append(
                    "Step 2 failed: the visible CLI JSON response did not identify the "
                    "Local Git provider.\n"
                    f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
                )
            if not isinstance(error_dict, dict):
                failures.append(
                    "Step 2 failed: the CLI response did not include an `error` object "
                    "for the mixed-case self-referencing link attempt.\n"
                    f"Observed payload: {json.dumps(payload_dict, indent=2, sort_keys=True)}"
                )
            else:
                if error_dict.get("code") != self.config.expected_error_code:
                    failures.append(
                        "Step 2 failed: the CLI did not classify the mixed-case self-link "
                        "attempt as a validation mutation error.\n"
                        f"Expected error.code: {self.config.expected_error_code}\n"
                        f"Observed error payload: {json.dumps(error_dict, indent=2, sort_keys=True)}"
                    )
                if error_dict.get("category") != self.config.expected_error_category:
                    failures.append(
                        "Step 2 failed: the CLI did not report the mixed-case self-link "
                        "attempt under the validation error category.\n"
                        f"Expected error.category: {self.config.expected_error_category}\n"
                        f"Observed error payload: {json.dumps(error_dict, indent=2, sort_keys=True)}"
                    )
                if error_dict.get("exitCode") != self.config.expected_error_exit_code:
                    failures.append(
                        "Step 2 failed: the CLI did not surface the expected validation "
                        "exit code in the machine-readable error payload.\n"
                        f"Expected error.exitCode: {self.config.expected_error_exit_code}\n"
                        f"Observed error payload: {json.dumps(error_dict, indent=2, sort_keys=True)}"
                    )
                error_message = error_dict.get("message")
                if not isinstance(error_message, str):
                    failures.append(
                        "Step 2 failed: the CLI error payload did not include a "
                        "descriptive message for the mixed-case self-link attempt.\n"
                        f"Observed error payload: {json.dumps(error_dict, indent=2, sort_keys=True)}"
                    )
                else:
                    normalized_message = error_message.lower()
                    missing_fragments = [
                        fragment
                        for fragment in self.config.expected_error_message_fragments
                        if fragment.lower() not in normalized_message
                    ]
                    if missing_fragments:
                        failures.append(
                            "Step 2 failed: the CLI error message did not make it clear "
                            "that the issue cannot be linked to itself regardless of key "
                            "casing.\n"
                            f"Missing fragments: {missing_fragments}\n"
                            f"Observed message: {error_message}"
                        )
                error_details = error_dict.get("details")
                details_dict = error_details if isinstance(error_details, dict) else None
                if not isinstance(details_dict, dict):
                    failures.append(
                        "Step 2 failed: the CLI error response did not expose details for "
                        "the mixed-case self-referencing link attempt.\n"
                        f"Observed error payload: {json.dumps(error_dict, indent=2, sort_keys=True)}"
                    )
                else:
                    if details_dict.get("operation") != "link":
                        failures.append(
                            "Step 2 failed: the CLI error details did not preserve the "
                            "ticket-link operation name.\n"
                            f"Observed error details: {json.dumps(details_dict, indent=2, sort_keys=True)}"
                        )
                    if details_dict.get("issueKey") != self.config.issue_a_key:
                        failures.append(
                            "Step 2 failed: the CLI error details did not preserve the "
                            "source issue key from the attempted mixed-case self-link "
                            "command.\n"
                            f"Expected issueKey: {self.config.issue_a_key}\n"
                            f"Observed error details: {json.dumps(details_dict, indent=2, sort_keys=True)}"
                        )

        visible_error = _visible_error_text(payload, stdout=link_observation.result.stdout)
        result["visible_error_text"] = visible_error
        if failures:
            _record_step(
                result,
                step=2,
                status="failed",
                action="Check the command's exit status and visible validation error.",
                observed=(
                    f"process_exit_code={link_observation.result.exit_code}; "
                    f"error_code={result.get('observed_error_code')}; "
                    f"error_category={result.get('observed_error_category')}; "
                    f"visible_error={visible_error}"
                ),
            )
        else:
            _record_step(
                result,
                step=2,
                status="passed",
                action="Check the command's exit status and visible validation error.",
                observed=(
                    f"process_exit_code={link_observation.result.exit_code}; "
                    f"error_code={result.get('observed_error_code')}; "
                    f"error_category={result.get('observed_error_category')}; "
                    f"visible_error={visible_error}"
                ),
            )
        return failures

    def _validate_metadata_state(
        self,
        observation: TrackStateCliSelfLinkGuardObservation,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        if observation.discovered_links_json_files:
            failures.append(
                "Step 3 failed: the mixed-case self-link mutation still produced one or "
                "more `links.json` files even though the CLI should reject the "
                "relationship.\n"
                f"Observed files: {observation.discovered_links_json_files}\n"
                f"Observed files detail:\n{_format_links_json_snapshots(observation)}"
            )
        if observation.links_json_content is not None:
            failures.append(
                "Step 3 failed: the source issue still has persisted link metadata after "
                "the mixed-case self-link attempt should have been rejected.\n"
                f"Unexpected path: {observation.links_json_relative_path}\n"
                f"Observed content:\n{observation.links_json_content}"
            )
        if observation.links_json_payload is not None:
            failures.append(
                "Step 3 failed: the source issue still has parsed link metadata after "
                "the mixed-case self-link attempt should have been rejected.\n"
                f"Unexpected path: {observation.links_json_relative_path}\n"
                f"Observed payload: {json.dumps(observation.links_json_payload, indent=2, sort_keys=True)}"
            )

        if failures:
            _record_step(
                result,
                step=3,
                status="failed",
                action="Verify no relationship metadata is recorded in the repository.",
                observed=_summarize_failures(failures),
            )
        else:
            _record_step(
                result,
                step=3,
                status="passed",
                action="Verify no relationship metadata is recorded in the repository.",
                observed=(
                    f"links_json_relative_path={observation.links_json_relative_path}; "
                    "discovered_links_json_files=[]"
                ),
            )
        return failures

    def _validate_human_verification(
        self,
        observation: TrackStateCliSelfLinkGuardObservation,
        result: dict[str, object],
    ) -> list[str]:
        failures: list[str] = []
        for fragment in (
            '"ok": false',
            f'"code": "{self.config.expected_error_code}"',
            f'"exitCode": {self.config.expected_error_exit_code}',
            f'"issueKey": "{self.config.issue_a_key}"',
            '"targetKey": "ts-1"',
        ):
            if fragment not in observation.self_link_observation.result.stdout:
                failures.append(
                    "Human-style verification failed: the visible CLI JSON output did "
                    "not show the rejection details a user would read in the terminal "
                    "after attempting the mixed-case self-referencing relationship.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.self_link_observation.result.stdout}"
                )

        if failures:
            _record_human_verification(
                result,
                check=(
                    "Verified the terminal-visible JSON output a user would see after "
                    "running the mixed-case self-link command."
                ),
                observed=_summarize_failures(failures),
                status="failed",
            )
        else:
            _record_human_verification(
                result,
                check=(
                    "Verified the terminal-visible JSON output a user would see after "
                    "running the mixed-case self-link command."
                ),
                observed=_visible_error_text(
                    observation.self_link_observation.result.json_payload,
                    stdout=observation.self_link_observation.result.stdout,
                ),
                status="passed",
            )
        return failures


def main() -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    scenario = Ts663MixedCaseSelfLinkGuardScenario()
    result: dict[str, object] = {
        "ticket": TICKET_KEY,
        "ticket_summary": TICKET_SUMMARY,
        "steps": [],
        "human_verification": [],
    }
    try:
        result, failures = scenario.execute()
        if failures:
            raise AssertionError("\n\n".join(failures))
        _write_pass_outputs(result)
    except Exception as error:
        result.setdefault("ticket", TICKET_KEY)
        result.setdefault("ticket_summary", TICKET_SUMMARY)
        result["error"] = f"{type(error).__name__}: {error}"
        result["traceback"] = traceback.format_exc()
        _write_failure_outputs(result)
        raise


def _write_pass_outputs(result: dict[str, object]) -> None:
    if BUG_DESCRIPTION_PATH.exists():
        BUG_DESCRIPTION_PATH.unlink()
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
    error = str(result.get("error", "AssertionError: unknown failure"))
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


def _jira_comment(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"h3. {TICKET_KEY} {status}",
        "",
        "*Automation coverage*",
        (
            f"* Compiled the TrackState CLI from source ref "
            f"{{{{{_jira_inline(_as_text(result.get('compiled_source_ref')))}}}}}."
        ),
        "* Seeded a disposable local-git TrackState repository and created {{TS-1}}.",
        (
            "* Executed the exact ticket command "
            "{{trackstate ticket link --key TS-1 --target-key ts-1 --type \"relates to\"}}."
        ),
        (
            "* Verified the machine-readable exit status and validation envelope, then "
            "confirmed no {{links.json}} relationship metadata was persisted."
        ),
        "",
        "*Observed result*",
        (
            "* ✅ Matched the expected result: exit code {{2}}, "
            "{{code:INVALID_MUTATION}}, validation category, and no persisted "
            "{{links.json}} metadata."
            if passed
            else "* ❌ Did not match the expected result."
        ),
        (
            f"* Human-style verification: the terminal-visible JSON error was "
            f"{{{{{_jira_inline(_as_text(result.get('visible_error_text')))}}}}}."
        ),
        (
            f"* Environment: provider {{{{{_jira_inline(_as_text(result.get('provider')))}}}}}, "
            f"source ref {{{{{_jira_inline(_as_text(result.get('compiled_source_ref')))}}}}}, "
            f"repository path {{{{{_jira_inline(_as_text(result.get('repository_path')))}}}}}, "
            f"OS {{{{{platform.system()}}}}}."
        ),
        "",
        "*Step results*",
        *_step_lines(result, jira=True),
        "",
        "*Human-style verification*",
        *_human_lines(result, jira=True),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "*Exact error*",
                "{code}",
                str(result.get("traceback", result.get("error", ""))),
                "{code}",
            ]
        )
    return "\n".join(lines) + "\n"


def _pr_body(result: dict[str, object], *, passed: bool) -> str:
    status = "Passed" if passed else "Failed"
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        "### Automation",
        f"- Compiled the TrackState CLI from source ref `{_as_text(result.get('compiled_source_ref'))}`.",
        "- Seeded a disposable local-git TrackState repository and created `TS-1`.",
        (
            '- Executed the exact ticket command '
            '`trackstate ticket link --key TS-1 --target-key ts-1 --type "relates to"`.'
        ),
        (
            "- Verified the machine-readable exit status and validation envelope, then "
            "confirmed no `links.json` relationship metadata was persisted."
        ),
        "",
        "### Observed result",
        (
            "- ✅ Matched the expected result: exit code `2`, `INVALID_MUTATION`, "
            "validation category, and no persisted `links.json` metadata."
            if passed
            else "- ❌ Did not match the expected result."
        ),
        (
            f"- Human-style verification: the terminal-visible JSON error was "
            f"`{_as_text(result.get('visible_error_text'))}`."
        ),
        (
            f"- Environment: provider `{_as_text(result.get('provider'))}`, "
            f"source ref `{_as_text(result.get('compiled_source_ref'))}`, "
            f"repository path `{_as_text(result.get('repository_path'))}`, "
            f"OS `{platform.system()}`."
        ),
        "",
        "### Step results",
        *_step_lines(result, jira=False),
        "",
        "### Human-style verification",
        *_human_lines(result, jira=False),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "### Exact error",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _response_summary(result: dict[str, object], *, passed: bool) -> str:
    status = "PASSED" if passed else "FAILED"
    lines = [
        f"## {TICKET_KEY} {status}",
        "",
        (
            f"- Compiled the CLI from `{_as_text(result.get('compiled_source_ref'))}` and "
            "ran the mixed-case self-link command against a disposable local-git repository."
        ),
        (
            "- Expected result: exit code `2`, validation error, and no persisted "
            "`links.json` metadata."
        ),
        (
            f"- Observed result: process exit code `{_as_text(result.get('process_exit_code'))}`, "
            f"error code `{_as_text(result.get('observed_error_code'))}`, "
            f"message `{_as_text(result.get('visible_error_text'))}`."
        ),
        (
            "- Outcome: PASSED."
            if passed
            else f"- Outcome: FAILED — {_as_text(result.get('error'))}."
        ),
    ]
    if not passed:
        lines.extend(
            [
                "",
                "```text",
                str(result.get("traceback", result.get("error", ""))),
                "```",
            ]
        )
    return "\n".join(lines) + "\n"


def _bug_description(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "# TS-663 - Mixed-case self-link command does not return validation exit code 2",
            "",
            "## Steps to reproduce",
            "1. Create or use an existing issue such as `TS-1` in a local-git TrackState repository.",
            f"   - {'✅' if _step_status(result, 0) == 'passed' else '❌'} {_step_observation(result, 0)}",
            '2. Execute `trackstate ticket link --key TS-1 --target-key ts-1 --type "relates to"`.',
            f"   - {'✅' if _step_status(result, 1) == 'passed' else '❌'} {_step_observation(result, 1)}",
            "3. Check the command's exit status and visible JSON response.",
            f"   - {'✅' if _step_status(result, 2) == 'passed' else '❌'} {_step_observation(result, 2)}",
            "4. Inspect the repository metadata for any persisted relationship.",
            f"   - {'✅' if _step_status(result, 3) == 'passed' else '❌'} {_step_observation(result, 3)}",
            "",
            "## Actual vs Expected",
            (
                "- Expected: the command should fail with a validation error, return exit "
                "code `2`, include an `INVALID_MUTATION` validation envelope that makes it "
                "clear `TS-1` cannot be linked to itself with target key `ts-1`, and leave "
                "the repository without any `links.json` relationship metadata."
            ),
            (
                "- Actual: "
                f"process exit code `{_as_text(result.get('process_exit_code'))}`, "
                f"error code `{_as_text(result.get('observed_error_code'))}`, "
                f"category `{_as_text(result.get('observed_error_category'))}`, "
                f"message `{_as_text(result.get('visible_error_text'))}`."
            ),
            "",
            "## Missing or broken production capability",
            (
                "- The CLI does not consistently treat the source key `TS-1` and target key "
                "`ts-1` as the same issue for self-link validation before checking whether "
                "the linked issue exists."
            ),
            "",
            "## Exact error message or assertion failure",
            "```text",
            str(result.get("traceback", result.get("error", ""))),
            "```",
            "",
            "## Environment details",
            f"- Provider: `{_as_text(result.get('provider'))}`",
            f"- Source ref: `{_as_text(result.get('compiled_source_ref'))}`",
            f"- Repository root: `{REPO_ROOT}`",
            f"- Disposable repository path: `{_as_text(result.get('repository_path'))}`",
            f"- OS: `{platform.platform()}`",
            "",
            "## Logs",
            f"- Run command: `{RUN_COMMAND}`",
            "### stdout",
            "```json",
            _as_text(result.get("stdout")),
            "```",
            "### stderr",
            "```text",
            _as_text(result.get("stderr")),
            "```",
            "### links.json snapshots",
            "```json",
            json.dumps(result.get("discovered_links_json_snapshots", []), indent=2, sort_keys=True),
            "```",
        ]
    ) + "\n"


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
    status: str,
) -> None:
    human = result.setdefault("human_verification", [])
    if isinstance(human, list):
        human.append({"status": status, "check": check, "observed": observed})


def _step_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        prefix = "#" if jira else "1."
        lines.append(
            f"{prefix} Step {step['step']} — {step['action']} — "
            f"{str(step.get('status', 'failed')).upper() if jira else step.get('status', 'failed')}: "
            f"{step.get('observed', '')}"
        )
    if not lines:
        lines.append("# No step details were recorded." if jira else "1. No step details were recorded.")
    return lines


def _human_lines(result: dict[str, object], *, jira: bool) -> list[str]:
    lines: list[str] = []
    for item in result.get("human_verification", []):
        if not isinstance(item, dict):
            continue
        prefix = "*" if jira else "-"
        lines.append(
            f"{prefix} {str(item.get('status', 'failed')).upper() if jira else item.get('status', 'failed')}: "
            f"{item.get('check', '')} Observed: {item.get('observed', '')}"
        )
    if not lines:
        lines.append("* No human-style verification details were recorded." if jira else "- No human-style verification details were recorded.")
    return lines


def _step_status(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return str(step.get("status", "failed"))
    return "failed"


def _step_observation(result: dict[str, object], step_number: int) -> str:
    for step in result.get("steps", []):
        if isinstance(step, dict) and step.get("step") == step_number:
            return _as_text(step.get("observed"))
    return "No observation recorded."


def _snapshot_to_dict(snapshot: TrackStateCliSelfLinkLinksJsonSnapshot) -> dict[str, object]:
    return {
        "relative_path": snapshot.relative_path,
        "content": snapshot.content,
        "payload": snapshot.payload,
    }


def _format_links_json_snapshots(observation: TrackStateCliSelfLinkGuardObservation) -> str:
    if not observation.discovered_links_json_snapshots:
        return "<none>"
    return "\n".join(
        f"- {snapshot.relative_path}\n{snapshot.content or '<empty>'}"
        for snapshot in observation.discovered_links_json_snapshots
    )


def _visible_error_text(payload: object | None, *, stdout: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return stdout.strip()


def _summarize_failures(failures: list[str]) -> str:
    return failures[0] if failures else ""


def _as_text(value: object | None) -> str:
    if value is None:
        return ""
    return str(value)


def _jira_inline(value: str) -> str:
    return value.replace("{", "\\{").replace("}", "\\}")


if __name__ == "__main__":
    main()
