from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_jira_search_validator import (
    TrackStateCliJiraSearchValidator,
)
from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchConfig,
)
from testing.core.models.trackstate_cli_jira_search_result import (
    TrackStateCliJiraSearchObservation,
)
from testing.tests.support.trackstate_cli_jira_search_probe_factory import (
    create_trackstate_cli_jira_search_probe,
)


class CliSearchNoResultsFlattenedPaginationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.query = "project = TRACK and status = 'Non-Existent-Status-XYZ'"
        self.config = TrackStateCliJiraSearchConfig(
            requested_command=(
                "trackstate",
                "search",
                "--jql",
                self.query,
            ),
            supported_control_command=(
                "trackstate",
                "search",
                "--jql",
                "project = TRACK",
            ),
            expected_issue_keys=(),
            required_data_keys=("issues", "startAt", "maxResults", "total", "isLastPage"),
            expected_provider="local-git",
            expected_target_type="local",
            expected_start_at=0,
            expected_max_results=50,
            expected_total=0,
            expected_is_last_page=True,
        )
        self.validator = TrackStateCliJiraSearchValidator(
            probe=create_trackstate_cli_jira_search_probe(self.repository_root)
        )

    def test_search_with_no_results_keeps_flattened_pagination_shape(self) -> None:
        result = self.validator.validate(config=self.config)
        control_data = self._assert_successful_search_observation(
            result.supported_control,
            expected_command=self.config.supported_control_command,
            failure_prefix="Precondition failed",
            expected_issue_keys=("TRACK-1", "TRACK-2"),
            expected_total=2,
            expected_is_last_page=True,
        )
        ticket_data = self._assert_successful_search_observation(
            result.ticket_command,
            expected_command=self.config.requested_command,
            failure_prefix="Step 1 failed",
            expected_issue_keys=(),
            expected_total=self.config.expected_total,
            expected_is_last_page=self.config.expected_is_last_page,
        )

        self.assertEqual(
            result.ticket_command.repository_path,
            result.supported_control.repository_path,
            "Precondition failed: TS-348 did not run the ticket command against the "
            "same seeded repository that proved the fixture had searchable issues.\n"
            f"Ticket repository path: {result.ticket_command.repository_path}\n"
            f"Control repository path: {result.supported_control.repository_path}",
        )
        self.assertEqual(
            [issue.get("key") for issue in control_data["issues"] if isinstance(issue, dict)],
            ["TRACK-1", "TRACK-2"],
            "Precondition failed: the supported control search did not confirm that "
            "the seeded repository contains searchable TRACK issues.\n"
            f"Observed control data: {control_data}",
        )
        self.assertEqual(
            ticket_data.get("issues"),
            [],
            "Expected result failed: `data.issues` was not empty for the no-results "
            "search query.\n"
            f"Observed data: {ticket_data}",
        )
        self.assertEqual(
            ticket_data.get("jql"),
            self.query,
            "Expected result failed: the CLI response did not preserve the exact no-"
            "results JQL that was executed.\n"
            f"Observed data: {ticket_data}",
        )
        self.assertNotIn(
            "page",
            ticket_data,
            "Expected result failed: the response still exposed the legacy nested "
            "`data.page` object for the empty-result search.\n"
            f"Observed data: {ticket_data}",
        )

        output = result.ticket_command.result.stdout
        for fragment in (
            '"jql": "project = TRACK and status = \'Non-Existent-Status-XYZ\'"',
            '"startAt": 0',
            '"maxResults": 50',
            '"total": 0',
            '"isLastPage": true',
            '"issues": []',
        ):
            self.assertIn(
                fragment,
                output,
                "Human-style verification failed: the visible CLI JSON output did "
                "not show the expected empty search result with flattened pagination "
                "fields.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{output}",
            )
        for absent_fragment in ('"page": {', '"key": "TRACK-1"', '"key": "TRACK-2"'):
            self.assertNotIn(
                absent_fragment,
                output,
                "Human-style verification failed: the visible CLI JSON output still "
                "showed legacy pagination or seeded issue rows for the no-results "
                "search.\n"
                f"Unexpected fragment: {absent_fragment}\n"
                f"Observed stdout:\n{output}",
            )

    def _assert_successful_search_observation(
        self,
        observation: TrackStateCliJiraSearchObservation,
        *,
        expected_command: tuple[str, ...],
        failure_prefix: str,
        expected_issue_keys: tuple[str, ...],
        expected_total: int,
        expected_is_last_page: bool,
    ) -> dict[str, object]:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{failure_prefix}: the wrong command was executed for the TS-348 "
            "scenario.\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-348 must execute a repository-local compiled "
            "binary so the seeded repository can stay the current working "
            "directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-348 did not run the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            f"{failure_prefix}: executing `{observation.requested_command_text}` did "
            "not succeed from a valid TrackState repository.\n"
            f"Repository path: {observation.repository_path}\n"
            f"Requested command: {observation.requested_command_text}\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}\n"
            f"Observed exit code: {observation.result.exit_code}\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        self.assertIsInstance(
            observation.result.json_payload,
            dict,
            f"{failure_prefix}: the CLI command did not return a machine-readable "
            "JSON envelope.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        assert isinstance(payload, dict)
        self.assertIs(
            payload.get("ok"),
            True,
            f"{failure_prefix}: the CLI command returned a failure envelope instead "
            "of search results.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload.get("provider"),
            self.config.expected_provider,
            "Expected result failed: the successful search envelope did not identify "
            "the Local Git runtime.\n"
            f"Observed payload: {payload}",
        )

        target = payload.get("target")
        self.assertIsInstance(
            target,
            dict,
            "Expected result failed: the successful search envelope did not include "
            "target metadata as an object.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(target, dict)
        self.assertEqual(
            target.get("type"),
            self.config.expected_target_type,
            "Expected result failed: the successful search envelope did not identify "
            "the target type as local.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            target.get("value"),
            observation.repository_path,
            "Expected result failed: the successful search envelope did not keep the "
            "seeded repository as the resolved target.\n"
            f"Observed payload: {payload}",
        )

        data = payload.get("data")
        self.assertIsInstance(
            data,
            dict,
            "Step 2 failed: the JSON envelope did not include a `data` object for "
            "the search response.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(data, dict)
        missing_data_keys = [
            key for key in self.config.required_data_keys if key not in data
        ]
        self.assertFalse(
            missing_data_keys,
            "Expected result failed: the search response under `data` was missing the "
            "flattened Jira-compatible pagination keys required by TS-348.\n"
            f"Missing keys: {missing_data_keys}\n"
            f"Observed data: {data}",
        )

        issues = data.get("issues")
        self.assertIsInstance(
            issues,
            list,
            "Expected result failed: `data.issues` was not encoded as an array.\n"
            f"Observed data: {data}",
        )
        assert isinstance(issues, list)
        self.assertEqual(
            [issue.get("key") for issue in issues if isinstance(issue, dict)],
            list(expected_issue_keys),
            "Expected result failed: the search response did not include the expected "
            "issue keys for this scenario.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data.get("startAt"),
            self.config.expected_start_at,
            "Expected result failed: `data.startAt` did not report the requested "
            "offset.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data.get("maxResults"),
            self.config.expected_max_results,
            "Expected result failed: `data.maxResults` did not report the default "
            "page size for the no-results search.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data.get("total"),
            expected_total,
            "Expected result failed: `data.total` did not report the expected number "
            "of matching issues.\n"
            f"Observed data: {data}",
        )
        self.assertIsInstance(
            data.get("isLastPage"),
            bool,
            "Expected result failed: `data.isLastPage` was missing or not encoded as "
            "a boolean.\n"
            f"Observed data: {data}",
        )
        self.assertIs(
            data.get("isLastPage"),
            expected_is_last_page,
            "Expected result failed: `data.isLastPage` did not report the expected "
            "pagination boundary.\n"
            f"Expected: {expected_is_last_page}\n"
            f"Observed data: {data}",
        )
        return data


if __name__ == "__main__":
    unittest.main()
