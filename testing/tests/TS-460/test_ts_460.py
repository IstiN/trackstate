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


class TrackStateCliMultiFieldUpdateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliMultiFieldUpdateConfig.from_env()
        self.validator = TrackStateCliMultiFieldUpdateValidator(
            probe=create_trackstate_cli_multi_field_update_probe(self.repository_root)
        )

    def test_multi_field_update_uses_one_success_envelope_and_one_commit(self) -> None:
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
                "Precondition failed: TS-460 did not execute the expected "
                "multi-field update command against the disposable Local Git "
                "repository.\n"
                f"Requested command: {observation.requested_command_text}"
            ),
        )

        payload = self._successful_envelope_or_failures(
            result=observation.result,
            failure_prefix="Step 1 failed",
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
                    "Step 1 failed: the success envelope did not identify the "
                    "canonical multi-field update command.\n"
                    f"Observed payload: {payload}"
                ),
            )
            self._check_equal(
                failures=failures,
                actual=data.get("operation"),
                expected="update-fields",
                message=(
                    "Expected result failed: the update did not report the shared "
                    "field mutation operation.\n"
                    f"Observed payload: {payload}"
                ),
            )
            self._check_equal(
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
            self._check_equal(
                failures=failures,
                actual=issue.get("summary"),
                expected=self.config.updated_summary,
                message=(
                    "Step 2 failed: the returned issue payload did not preserve "
                    "the updated summary.\n"
                    f"Observed issue: {issue}"
                ),
            )
            self._check_equal(
                failures=failures,
                actual=issue.get("priority"),
                expected=self.config.updated_priority_id,
                message=(
                    "Step 2 failed: the returned issue payload did not resolve "
                    "the updated priority to the canonical id.\n"
                    f"Observed issue: {issue}"
                ),
            )
            self._check_equal(
                failures=failures,
                actual=issue.get("assignee"),
                expected=self.config.updated_assignee,
                message=(
                    "Step 2 failed: the returned issue payload did not preserve "
                    "the updated assignee.\n"
                    f"Observed issue: {issue}"
                ),
            )
            self._check_equal(
                failures=failures,
                actual=issue.get("labels"),
                expected=list(self.config.updated_labels),
                message=(
                    "Step 2 failed: the returned issue payload did not preserve "
                    "the updated labels.\n"
                    f"Observed issue: {issue}"
                ),
            )
            self._check_equal(
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

        self._check_equal(
            failures=failures,
            actual=observation.final_commit_count,
            expected=observation.initial_commit_count + 1,
            message=(
                "Step 3 failed: the multi-field update did not persist as exactly "
                "one new Git commit.\n"
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
                "Step 3 failed: the repository HEAD did not change after the "
                "multi-field update command completed.\n"
                f"Initial HEAD: {observation.initial_head_revision}\n"
                f"Final HEAD: {observation.final_head_revision}"
            ),
        )
        self._check_equal(
            failures=failures,
            actual=observation.latest_commit_subject,
            expected=self.config.expected_commit_subject,
            message=(
                "Expected result failed: the latest Git commit was not dedicated "
                "to the single issue field update.\n"
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

        main_file = observation.main_file_content
        self._check_in(
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
        self._check_in(
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
        self._check_in(
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
        self._check_in(
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
        self._check_in(
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
        self._check_in(
            failures=failures,
            member=self.config.updated_summary,
            container=main_file,
            message=(
                "Human-style verification failed: the updated issue markdown "
                "did not show the new summary text in the rendered content.\n"
                f"Observed {observation.main_file_relative_path} contents:\n"
                f"{main_file}"
            ),
        )
        self._check_not_in(
            failures=failures,
            member=self.config.initial_summary,
            container=main_file,
            message=(
                "Expected result failed: main.md still showed the original "
                "summary after the update completed.\n"
                f"Observed {observation.main_file_relative_path} contents:\n"
                f"{main_file}"
            ),
        )
        self._check_not_in(
            failures=failures,
            member=f"assignee: {self.config.initial_assignee}",
            container=main_file,
            message=(
                "Expected result failed: main.md still showed the original "
                "assignee after the update completed.\n"
                f"Observed {observation.main_file_relative_path} contents:\n"
                f"{main_file}"
            ),
        )

        for fragment in (
            f'"command": "{self.config.expected_command_name}"',
            '"summary": "New Title"',
            '"priority": "high"',
            '"assignee": "user1"',
            '"labels": [',
            '"bug"',
            '"ai"',
            f'"revision": "{observation.final_head_revision}"',
        ):
            self._check_in(
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
