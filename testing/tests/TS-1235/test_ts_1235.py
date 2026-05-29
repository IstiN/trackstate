from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_multi_field_update_validator import (
    TrackStateCliMultiFieldUpdateValidator,
)
from testing.core.config.trackstate_cli_multi_field_update_config import (
    TrackStateCliMultiFieldUpdateConfig,
)
from testing.core.models.cli_command_result import CliCommandResult
from testing.tests.support.trackstate_cli_multi_field_update_probe_factory import (
    create_trackstate_cli_multi_field_update_probe,
)


class TrackStateCliArrayFieldUpdateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliMultiFieldUpdateConfig.from_env()
        self.validator = TrackStateCliMultiFieldUpdateValidator(
            probe=create_trackstate_cli_multi_field_update_probe(self.repository_root)
        )

    def test_json_array_field_update_succeeds_without_comma_fragmentation(
        self,
    ) -> None:
        observation = self.validator.validate(config=self.config).observation
        failures: list[str] = []

        self._check_equal(
            failures=failures,
            actual=observation.requested_command,
            expected=(
                *self.config.requested_command_prefix,
                "--path",
                observation.repository_path,
                "--key",
                self.config.issue_key,
                "--field",
                self.config.field_assignments[0],
                "--field",
                self.config.field_assignments[1],
                "--field",
                self.config.field_assignments[2],
                "--field",
                self.config.field_assignments[3],
            ),
            message=(
                "Precondition failed: TS-1235 did not execute the expected "
                "ticket update command against the disposable Local Git "
                "repository.\n"
                f"Requested command: {observation.requested_command_text}"
            ),
        )
        self._check_in(
            failures=failures,
            member='labels=["bug","ai"]',
            container=observation.requested_command_text,
            message=(
                "Step 1 failed: the JSON array field assignment was not passed "
                "to the CLI as one intact `key=value` argument.\n"
                f"Requested command: {observation.requested_command_text}"
            ),
        )

        combined_output = f"{observation.result.stdout}\n{observation.result.stderr}"
        self._check_false(
            failures=failures,
            condition="INVALID_ARGUMENT" in combined_output,
            message=(
                "Step 2 failed: the CLI still reported INVALID_ARGUMENT for the "
                "JSON array field assignment.\n"
                f"Command output:\n{combined_output}"
            ),
        )
        self._check_false(
            failures=failures,
            condition="Field assignments must use key=value syntax" in combined_output,
            message=(
                "Step 2 failed: the CLI still showed the historical comma-"
                "fragmentation parser error for the JSON array field.\n"
                f"Command output:\n{combined_output}"
            ),
        )

        payload = self._successful_envelope_or_failures(
            result=observation.result,
            failure_prefix="Step 2 failed",
            failures=failures,
        )
        data = payload.get("data") if payload is not None else None
        issue = data.get("issue") if isinstance(data, dict) else None

        if isinstance(data, dict):
            self._check_equal(
                failures=failures,
                actual=data.get("command"),
                expected=self.config.expected_command_name,
                message=(
                    "Step 2 failed: the CLI success envelope did not identify "
                    "the canonical ticket update command.\n"
                    f"Observed payload: {payload}"
                ),
            )
            self._check_equal(
                failures=failures,
                actual=data.get("operation"),
                expected="update-fields",
                message=(
                    "Step 2 failed: the CLI did not report the shared "
                    "multi-field update operation.\n"
                    f"Observed payload: {payload}"
                ),
            )
        if isinstance(issue, dict):
            self._check_equal(
                failures=failures,
                actual=issue.get("summary"),
                expected=self.config.updated_summary,
                message=(
                    "Step 2 failed: the returned issue payload did not show "
                    'summary "New Title".\n'
                    f"Observed issue: {issue}"
                ),
            )
            self._check_equal(
                failures=failures,
                actual=issue.get("priority"),
                expected=self.config.updated_priority_id,
                message=(
                    "Step 2 failed: the returned issue payload did not show the "
                    "updated priority id.\n"
                    f"Observed issue: {issue}"
                ),
            )
            self._check_equal(
                failures=failures,
                actual=issue.get("assignee"),
                expected=self.config.updated_assignee,
                message=(
                    "Step 2 failed: the returned issue payload did not show the "
                    "updated assignee.\n"
                    f"Observed issue: {issue}"
                ),
            )
            self._check_equal(
                failures=failures,
                actual=issue.get("labels"),
                expected=list(self.config.updated_labels),
                message=(
                    "Step 2 failed: the returned issue payload did not preserve "
                    'the JSON array labels ["bug", "ai"].\n'
                    f"Observed issue: {issue}"
                ),
            )
        elif payload is not None:
            failures.append(
                "Step 2 failed: the success envelope did not include an updated "
                f"issue object.\nObserved payload: {payload}"
            )

        main_file = observation.main_file_content
        self._check_in(
            failures=failures,
            member='summary: "New Title"',
            container=main_file,
            message=(
                "Step 3 failed: main.md did not visibly store the updated "
                'summary "New Title".\n'
                f"Observed {observation.main_file_relative_path} contents:\n"
                f"{main_file}"
            ),
        )
        self._check_in(
            failures=failures,
            member='labels: ["bug","ai"]',
            container=main_file,
            message=(
                "Step 3 failed: main.md did not visibly store the intact JSON "
                'array labels ["bug","ai"].\n'
                f"Observed {observation.main_file_relative_path} contents:\n"
                f"{main_file}"
            ),
        )
        self._check_not_in(
            failures=failures,
            member='labels: ["legacy"]',
            container=main_file,
            message=(
                "Expected result failed: main.md still showed the original "
                "labels after the update completed.\n"
                f"Observed {observation.main_file_relative_path} contents:\n"
                f"{main_file}"
            ),
        )
        self._check_in(
            failures=failures,
            member="# Summary",
            container=main_file,
            message=(
                "Human-style verification failed: the issue markdown no longer "
                "showed the rendered summary section.\n"
                f"Observed {observation.main_file_relative_path} contents:\n"
                f"{main_file}"
            ),
        )
        self._check_in(
            failures=failures,
            member=self.config.updated_summary,
            container=main_file,
            message=(
                "Human-style verification failed: the visible issue markdown did "
                "not show the updated summary text.\n"
                f"Observed {observation.main_file_relative_path} contents:\n"
                f"{main_file}"
            ),
        )

        self._check_equal(
            failures=failures,
            actual=observation.final_commit_count,
            expected=observation.initial_commit_count + 1,
            message=(
                "Expected result failed: the atomic multi-field update did not "
                "persist as exactly one new Git commit.\n"
                f"Initial commit count: {observation.initial_commit_count}\n"
                f"Final commit count: {observation.final_commit_count}\n"
                f"Latest commit subject: {observation.latest_commit_subject}"
            ),
        )
        self._check_not_equal(
            failures=failures,
            actual=observation.initial_head_revision,
            unexpected=observation.final_head_revision,
            message=(
                "Expected result failed: the repository HEAD did not change "
                "after the update command completed.\n"
                f"Initial HEAD: {observation.initial_head_revision}\n"
                f"Final HEAD: {observation.final_head_revision}"
            ),
        )
        self._check_equal(
            failures=failures,
            actual=observation.latest_commit_subject,
            expected=self.config.expected_commit_subject,
            message=(
                "Expected result failed: the latest Git commit was not the "
                "dedicated ticket field update commit.\n"
                f"Observed commit subject: {observation.latest_commit_subject}"
            ),
        )
        self._check_false(
            failures=failures,
            condition=bool(observation.git_status.strip()),
            message=(
                "Expected result failed: the repository worktree was not clean "
                "after the update commit completed.\n"
                f"git status --short:\n{observation.git_status}"
            ),
        )

        for fragment in (
            '"ok": true',
            f'"command": "{self.config.expected_command_name}"',
            '"operation": "update-fields"',
            '"summary": "New Title"',
            '"priority": "high"',
            '"assignee": "user1"',
            '"labels": [',
            '"bug"',
            '"ai"',
        ):
            self._check_in(
                failures=failures,
                member=fragment,
                container=observation.result.stdout,
                message=(
                    "Human-style verification failed: the visible CLI JSON "
                    "response did not show the expected updated issue details.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.result.stdout}"
                ),
            )

        if failures:
            self.fail("\n\n".join(failures))

    def _successful_envelope_or_failures(
        self,
        *,
        result: CliCommandResult,
        failure_prefix: str,
        failures: list[str],
    ) -> dict[str, object] | None:
        self._check_true(
            failures=failures,
            condition=result.succeeded,
            message=(
                f"{failure_prefix}: the ticket update command did not complete "
                "successfully.\n"
                f"Executed command: {result.command_text}\n"
                f"Exit code: {result.exit_code}\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            ),
        )
        payload = result.json_payload
        if not isinstance(payload, dict):
            failures.append(
                f"{failure_prefix}: the CLI did not return one JSON success "
                "envelope.\n"
                f"stdout:\n{result.stdout}\n"
                f"stderr:\n{result.stderr}"
            )
            return None
        missing_top_level_keys = [
            key for key in self.config.required_top_level_keys if key not in payload
        ]
        self._check_false(
            failures=failures,
            condition=bool(missing_top_level_keys),
            message=(
                f"{failure_prefix}: the success envelope was missing required "
                "top-level keys.\n"
                f"Missing keys: {missing_top_level_keys}\n"
                f"Observed payload: {payload}"
            ),
        )
        self._check_true(
            failures=failures,
            condition=payload.get("ok") is True,
            message=(
                f"{failure_prefix}: the envelope reported a non-success "
                "result.\n"
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
            key for key in self.config.required_data_keys if key not in data
        ]
        self._check_false(
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

    @staticmethod
    def _check_true(
        *,
        failures: list[str],
        condition: bool,
        message: str,
    ) -> None:
        if not condition:
            failures.append(message)

    @classmethod
    def _check_false(
        cls,
        *,
        failures: list[str],
        condition: bool,
        message: str,
    ) -> None:
        cls._check_true(failures=failures, condition=not condition, message=message)

    @staticmethod
    def _check_equal(
        *,
        failures: list[str],
        actual: object,
        expected: object,
        message: str,
    ) -> None:
        if actual != expected:
            failures.append(message)

    @staticmethod
    def _check_not_equal(
        *,
        failures: list[str],
        actual: object,
        unexpected: object,
        message: str,
    ) -> None:
        if actual == unexpected:
            failures.append(message)

    @staticmethod
    def _check_in(
        *,
        failures: list[str],
        member: str,
        container: str,
        message: str,
    ) -> None:
        if member not in container:
            failures.append(message)

    @staticmethod
    def _check_not_in(
        *,
        failures: list[str],
        member: str,
        container: str,
        message: str,
    ) -> None:
        if member in container:
            failures.append(message)


if __name__ == "__main__":
    unittest.main()
