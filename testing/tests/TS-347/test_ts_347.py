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


class CamelCaseCliSearchPaginationShapeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliJiraSearchConfig(
            requested_command=(
                "trackstate",
                "search",
                "--jql",
                "project = TRACK",
                "--startAt",
                "0",
                "--maxResults",
                "1",
            ),
            supported_control_command=(
                "trackstate",
                "search",
                "--jql",
                "project = TRACK",
                "--start-at",
                "0",
                "--max-results",
                "1",
            ),
            expected_issue_keys=("TRACK-1",),
            required_data_keys=("issues", "startAt", "maxResults", "total", "isLastPage"),
            expected_provider="local-git",
            expected_target_type="local",
            expected_start_at=0,
            expected_max_results=1,
            expected_total=2,
            expected_is_last_page=False,
        )
        self.validator = TrackStateCliJiraSearchValidator(
            probe=create_trackstate_cli_jira_search_probe(self.repository_root)
        )

    def test_camel_case_flags_return_flattened_pagination_fields(self) -> None:
        result = self.validator.validate(config=self.config)
        control_data = self._assert_successful_search_observation(
            result.supported_control,
            expected_command=self.config.supported_control_command,
            failure_prefix="Precondition failed",
        )
        ticket_data = self._assert_successful_search_observation(
            result.ticket_command,
            expected_command=self.config.requested_command,
            failure_prefix="Step 1 failed",
        )

        self.assertEqual(
            ticket_data,
            control_data,
            "Expected result failed: the camelCase pagination flags did not produce "
            "the same flattened `data` payload as the kebab-case control command.\n"
            f"Observed camelCase data: {ticket_data}\n"
            f"Observed kebab-case data: {control_data}",
        )
        self.assertNotIn(
            "page",
            ticket_data,
            "Expected result failed: the response still nested pagination fields "
            "inside `data.page` for the camelCase flag path.\n"
            f"Observed data: {ticket_data}",
        )

        output = result.ticket_command.result.stdout
        for fragment in (
            '"issues": [',
            '"startAt": 0',
            '"maxResults": 1',
            '"total": 2',
            '"isLastPage": false',
            '"key": "TRACK-1"',
            '"summary": "Issue 1"',
        ):
            self.assertIn(
                fragment,
                output,
                "Human-style verification failed: the visible CLI JSON output did "
                "not show the expected flattened pagination fields for the camelCase "
                "command.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{output}",
            )
        self.assertNotIn(
            '"page": {',
            output,
            "Human-style verification failed: the visible CLI JSON output still "
            "showed a nested `page` object for the camelCase command.\n"
            f"Observed stdout:\n{output}",
        )

    def _assert_successful_search_observation(
        self,
        observation: TrackStateCliJiraSearchObservation,
        *,
        expected_command: tuple[str, ...],
        failure_prefix: str,
    ) -> dict[str, object]:
        self.assertEqual(
            observation.requested_command,
            expected_command,
            f"{failure_prefix}: the wrong command was executed for the TS-347 "
            "scenario.\n"
            f"Expected command: {' '.join(expected_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-347 must execute a repository-local compiled "
            "binary so the seeded repository can stay the current working "
            "directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            f"{failure_prefix}: TS-347 did not run the compiled repository-local "
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
            "flattened Jira-compatible pagination keys required by TS-347.\n"
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
            list(self.config.expected_issue_keys),
            "Expected result failed: the search response did not include the expected "
            "paged issue keys.\n"
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
            "Expected result failed: `data.maxResults` did not report the requested "
            "page size.\n"
            f"Observed data: {data}",
        )
        self.assertEqual(
            data.get("total"),
            self.config.expected_total,
            "Expected result failed: `data.total` did not report the total number of "
            "matching issues.\n"
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
            self.config.expected_is_last_page,
            "Expected result failed: `data.isLastPage` did not report the expected "
            "pagination boundary.\n"
            f"Expected: {self.config.expected_is_last_page}\n"
            f"Observed data: {data}",
        )
        return data


if __name__ == "__main__":
    unittest.main()
