from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_lifecycle_validator import (
    TrackStateCliLifecycleValidator,
)
from testing.core.config.trackstate_cli_lifecycle_config import (
    TrackStateCliLifecycleConfig,
)
from testing.core.models.trackstate_cli_command_observation import (
    TrackStateCliCommandObservation,
)
from testing.core.models.trackstate_cli_lifecycle_result import (
    TrackStateCliLifecycleRepositoryState,
    TrackStateCliLifecycleValidationResult,
)
from testing.tests.support.trackstate_cli_lifecycle_probe_factory import (
    create_trackstate_cli_lifecycle_probe,
)


class CliLifecycleCommandsDistinctionTest(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliLifecycleConfig.from_defaults()
        self.validator = TrackStateCliLifecycleValidator(
            probe=create_trackstate_cli_lifecycle_probe(self.repository_root)
        )

    def test_delete_creates_tombstone_while_archive_stays_reversible(self) -> None:
        result = self.validator.validate(config=self.config)

        self._assert_command_was_executed_exactly(
            observation=result.delete_observation,
            expected_command=self.config.delete_command,
            ticket_key="TS-461",
            precondition_message=(
                "Precondition failed: TS-461 must execute the exact delete ticket "
                "command from the seeded repository."
            ),
        )
        self._assert_command_was_executed_exactly(
            observation=result.archive_observation,
            expected_command=self.config.archive_command,
            ticket_key="TS-461",
            precondition_message=(
                "Precondition failed: TS-461 must execute the exact archive ticket "
                "command from the seeded repository."
            ),
        )
        self._assert_initial_fixture(result.initial_state)

        failures = [
            *self._collect_delete_failures(result),
            *self._collect_archive_failures(result),
        ]
        self.assertFalse(failures, "\n\n".join(failures))

    def _assert_command_was_executed_exactly(
        self,
        *,
        observation: TrackStateCliCommandObservation,
        expected_command: tuple[str, ...],
        ticket_key: str,
        precondition_message: str,
    ) -> None:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{precondition_message}\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            f"{ticket_key} must execute a repository-local compiled binary so the "
            "seeded repository stays the current working directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{precondition_message}\n"
            f"{ticket_key} did not run the compiled repository-local CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )

    def _assert_initial_fixture(
        self,
        state: TrackStateCliLifecycleRepositoryState,
    ) -> None:
        self.assertTrue(
            state.deleted_issue_directory_exists and state.deleted_issue_main_exists,
            "Precondition failed: the seeded repository did not contain TS-10 before "
            "executing the delete scenario.\n"
            f"Observed repository state:\n{self._describe_state(state)}",
        )
        self.assertTrue(
            state.archived_issue_directory_exists and state.archived_issue_main_exists,
            "Precondition failed: the seeded repository did not contain TS-11 before "
            "executing the archive scenario.\n"
            f"Observed repository state:\n{self._describe_state(state)}",
        )
        self.assertFalse(
            state.tombstone_index_exists,
            "Precondition failed: the seeded repository already contained a tombstone "
            "index before TS-461 ran.\n"
            f"Observed repository state:\n{self._describe_state(state)}",
        )
        self.assertFalse(
            state.deleted_issue_tombstone_exists or state.archived_issue_tombstone_exists,
            "Precondition failed: the seeded repository already contained tombstone "
            "artifacts before TS-461 ran.\n"
            f"Observed repository state:\n{self._describe_state(state)}",
        )

    def _collect_delete_failures(
        self,
        result: TrackStateCliLifecycleValidationResult,
    ) -> list[str]:
        observation = result.delete_observation
        state = result.after_delete_state
        if observation.result.exit_code != 0:
            return [
                "Step 1 failed: executing `trackstate jira_delete_ticket TS-10` did "
                "not succeed from a valid TrackState repository.\n"
                f"Repository path: {observation.repository_path}\n"
                f"Requested command: {observation.requested_command_text}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}\n"
                "\n"
                "Repository state after the failed delete attempt:\n"
                f"{self._describe_state(state)}"
            ]

        failures: list[str] = []
        if state.deleted_issue_directory_exists or state.deleted_issue_main_exists:
            failures.append(
                "Step 2 failed: TS-10 was not physically removed after the delete "
                "command completed.\n"
                f"Observed repository state:\n{self._describe_state(state)}"
            )
        if state.deleted_issue_archive_main_exists:
            failures.append(
                "Expected result failed: `jira_delete_ticket` appeared to archive TS-10 "
                "instead of hard deleting it, because an archived issue file was found "
                "under `TS/.trackstate/archive/TS-10/main.md`.\n"
                f"Observed repository state:\n{self._describe_state(state)}"
            )
        if not state.tombstone_index_exists:
            failures.append(
                "Step 2 failed: deleting TS-10 did not create "
                "`TS/.trackstate/index/tombstones.json`.\n"
                f"Observed repository state:\n{self._describe_state(state)}"
            )
        elif not isinstance(state.tombstone_index_payload, list):
            failures.append(
                "Step 2 failed: `TS/.trackstate/index/tombstones.json` was not a JSON "
                "array.\n"
                f"Observed file contents:\n{state.tombstone_index_text}"
            )
        else:
            matching_entries = [
                entry
                for entry in state.tombstone_index_payload
                if isinstance(entry, dict) and entry.get("key") == self.config.delete_issue.key
            ]
            if not matching_entries:
                failures.append(
                    "Step 2 failed: the tombstone index did not include TS-10 after "
                    "the delete command completed.\n"
                    f"Observed file contents:\n{state.tombstone_index_text}"
                )
            elif matching_entries[0].get("path") != self.config.expected_tombstone_artifact_path:
                failures.append(
                    "Step 2 failed: the tombstone index did not point TS-10 at the "
                    "expected tombstone artifact path.\n"
                    f"Expected path: {self.config.expected_tombstone_artifact_path}\n"
                    f"Observed entry: {matching_entries[0]}"
                )
        if not state.deleted_issue_tombstone_exists:
            failures.append(
                "Step 2 failed: deleting TS-10 did not create a tombstone artifact at "
                f"`{self.config.expected_tombstone_artifact_path}`.\n"
                f"Observed repository state:\n{self._describe_state(state)}"
            )
        elif not isinstance(state.deleted_issue_tombstone_payload, dict):
            failures.append(
                "Step 2 failed: the TS-10 tombstone artifact was not a JSON object.\n"
                f"Observed file contents:\n{state.deleted_issue_tombstone_text}"
            )
        else:
            if state.deleted_issue_tombstone_payload.get("key") != self.config.delete_issue.key:
                failures.append(
                    "Step 2 failed: the TS-10 tombstone artifact did not preserve the "
                    "deleted issue key.\n"
                    f"Observed tombstone: {state.deleted_issue_tombstone_payload}"
                )
            if (
                state.deleted_issue_tombstone_payload.get("formerPath")
                != self.config.expected_deleted_issue_former_path
            ):
                failures.append(
                    "Expected result failed: the TS-10 tombstone did not preserve the "
                    "issue's former repository path.\n"
                    f"Expected formerPath: {self.config.expected_deleted_issue_former_path}\n"
                    f"Observed tombstone: {state.deleted_issue_tombstone_payload}"
                )
        for fragment in (
            '"command": "jira-delete-ticket"',
            '"deletedIssue": {',
            f'"key": "{self.config.delete_issue.key}"',
            f'"formerPath": "{self.config.expected_deleted_issue_former_path}"',
        ):
            if fragment not in observation.result.stdout:
                failures.append(
                    "Human-style verification failed: the visible CLI output for the "
                    "delete command did not show the expected delete/tombstone details.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.result.stdout}"
                )
        return failures

    def _collect_archive_failures(
        self,
        result: TrackStateCliLifecycleValidationResult,
    ) -> list[str]:
        observation = result.archive_observation
        state = result.after_archive_state
        if observation.result.exit_code != 0:
            return [
                "Step 3 failed: executing `trackstate archive TS-11` did not succeed "
                "from the same TrackState repository used for the delete scenario.\n"
                f"Repository path: {observation.repository_path}\n"
                f"Requested command: {observation.requested_command_text}\n"
                f"Executed command: {observation.executed_command_text}\n"
                f"Fallback reason: {observation.fallback_reason}\n"
                f"Observed exit code: {observation.result.exit_code}\n"
                f"stdout:\n{observation.result.stdout}\n"
                f"stderr:\n{observation.result.stderr}\n"
                "\n"
                "Repository state after the failed archive attempt:\n"
                f"{self._describe_state(state)}"
            ]

        failures: list[str] = []
        if not state.archived_issue_directory_exists or not state.archived_issue_main_exists:
            failures.append(
                "Step 4 failed: TS-11 did not remain in its canonical issue path after "
                "the archive command completed.\n"
                f"Observed repository state:\n{self._describe_state(state)}"
            )
        if state.archived_issue_archive_main_exists:
            failures.append(
                "Expected result failed: `archive` moved TS-11 into "
                "`TS/.trackstate/archive/TS-11/main.md` instead of leaving the issue "
                "in `TS/TS-11/main.md` with archived metadata.\n"
                f"Observed repository state:\n{self._describe_state(state)}"
            )
        if "archived: true" not in (state.archived_issue_main_content or ""):
            failures.append(
                "Step 4 failed: `TS/TS-11/main.md` did not show `archived: true` in "
                "its frontmatter after the archive command completed.\n"
                f"Observed file contents:\n{state.archived_issue_main_content}"
            )
        if state.archived_issue_tombstone_exists:
            failures.append(
                "Expected result failed: archiving TS-11 created a tombstone artifact, "
                "which indicates the archive command fell back to delete behavior.\n"
                f"Observed repository state:\n{self._describe_state(state)}"
            )
        if isinstance(state.tombstone_index_payload, list):
            if any(
                isinstance(entry, dict) and entry.get("key") == self.config.archive_issue.key
                for entry in state.tombstone_index_payload
            ):
                failures.append(
                    "Expected result failed: the tombstone index included TS-11 after "
                    "running `archive`, which means archive reused delete logic.\n"
                    f"Observed file contents:\n{state.tombstone_index_text}"
                )
        for fragment in (
            '"command": "ticket-archive"',
            '"issue": {',
            f'"key": "{self.config.archive_issue.key}"',
            '"archived": true',
        ):
            if fragment not in observation.result.stdout:
                failures.append(
                    "Human-style verification failed: the visible CLI output for the "
                    "archive command did not show the expected archived issue details.\n"
                    f"Missing fragment: {fragment}\n"
                    f"Observed stdout:\n{observation.result.stdout}"
                )
        return failures

    def _describe_state(self, state: TrackStateCliLifecycleRepositoryState) -> str:
        return "\n".join(
            (
                f"deleted_issue_directory_exists={state.deleted_issue_directory_exists}",
                f"deleted_issue_main_exists={state.deleted_issue_main_exists}",
                (
                    "deleted_issue_archive_main_exists="
                    f"{state.deleted_issue_archive_main_exists}"
                ),
                (
                    "archived_issue_directory_exists="
                    f"{state.archived_issue_directory_exists}"
                ),
                f"archived_issue_main_exists={state.archived_issue_main_exists}",
                (
                    "archived_issue_archive_main_exists="
                    f"{state.archived_issue_archive_main_exists}"
                ),
                f"tombstone_index_exists={state.tombstone_index_exists}",
                f"tombstone_index_payload={state.tombstone_index_payload}",
                (
                    "deleted_issue_tombstone_exists="
                    f"{state.deleted_issue_tombstone_exists}"
                ),
                (
                    "deleted_issue_tombstone_payload="
                    f"{state.deleted_issue_tombstone_payload}"
                ),
                (
                    "archived_issue_tombstone_exists="
                    f"{state.archived_issue_tombstone_exists}"
                ),
                (
                    "archived_issue_tombstone_payload="
                    f"{state.archived_issue_tombstone_payload}"
                ),
                "archived_issue_main_content=",
                state.archived_issue_main_content or "<missing>",
                "archived_issue_archive_main_content=",
                state.archived_issue_archive_main_content or "<missing>",
            )
        )


if __name__ == "__main__":
    unittest.main()
