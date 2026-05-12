from __future__ import annotations

from pathlib import Path
import unittest

from testing.components.services.trackstate_cli_read_ticket_shape_validator import (
    TrackStateCliReadTicketShapeValidator,
)
from testing.core.config.trackstate_cli_read_ticket_shape_config import (
    TrackStateCliReadTicketShapeConfig,
)
from testing.tests.support.trackstate_cli_read_ticket_shape_probe_factory import (
    create_trackstate_cli_read_ticket_shape_probe,
)


class TrackStateCliReadTicketRawIssueShapeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.repository_root = Path(__file__).resolve().parents[3]
        self.config = TrackStateCliReadTicketShapeConfig.from_defaults()
        self.validator = TrackStateCliReadTicketShapeValidator(
            probe=create_trackstate_cli_read_ticket_shape_probe(self.repository_root)
        )

    def test_read_ticket_returns_a_raw_jira_issue_object(self) -> None:
        observation = self.validator.validate(config=self.config).observation

        self.assertEqual(
            observation.requested_command,
            self.config.requested_command,
            "Precondition failed: TS-375 did not execute the canonical read ticket "
            "command required by the ticket.\n"
            f"Expected command: {' '.join(self.config.requested_command)}\n"
            f"Observed command: {observation.requested_command_text}",
        )
        self.assertIsNotNone(
            observation.compiled_binary_path,
            "Precondition failed: TS-375 must execute a repository-local compiled "
            "binary so the seeded repository can stay the current working "
            "directory.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Fallback reason: {observation.fallback_reason}",
        )
        self.assertEqual(
            observation.executed_command[0],
            observation.compiled_binary_path,
            "Precondition failed: TS-375 did not run the compiled repository-local "
            "CLI binary.\n"
            f"Executed command: {observation.executed_command_text}\n"
            f"Compiled binary path: {observation.compiled_binary_path}",
        )
        self.assertEqual(
            observation.result.exit_code,
            0,
            "Step 1 failed: executing `trackstate read ticket --key TS-20` did not "
            "complete successfully from a valid TrackState repository.\n"
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
            "Step 2 failed: the read ticket command did not return a JSON object.\n"
            f"stdout:\n{observation.result.stdout}\n"
            f"stderr:\n{observation.result.stderr}",
        )
        payload = observation.result.json_payload
        assert isinstance(payload, dict)

        missing_root_keys = [
            key for key in self.config.required_root_keys if key not in payload
        ]
        self.assertFalse(
            missing_root_keys,
            "Step 2 failed: the root JSON object did not expose the expected Jira "
            "issue keys directly.\n"
            f"Missing root keys: {missing_root_keys}\n"
            f"Observed payload: {payload}",
        )
        for forbidden_key in self.config.forbidden_root_keys:
            self.assertNotIn(
                forbidden_key,
                payload,
                "Expected result failed: the read ticket response was still wrapped "
                "in the TrackState success envelope.\n"
                f"Unexpected wrapper key: {forbidden_key}\n"
                f"Observed payload: {payload}",
            )

        self.assertEqual(
            payload["id"],
            self.config.expected_issue_id,
            "Expected result failed: the raw Jira issue id did not match the seeded "
            "ticket suffix.\n"
            f"Observed payload: {payload}",
        )
        self.assertEqual(
            payload["key"],
            self.config.fixture_ticket.key,
            "Step 2 failed: the raw Jira issue object did not preserve the requested "
            "ticket key.\n"
            f"Observed payload: {payload}",
        )

        fields = payload["fields"]
        self.assertIsInstance(
            fields,
            dict,
            "Step 2 failed: the raw Jira issue object did not expose `fields` as an "
            "object at the root.\n"
            f"Observed payload: {payload}",
        )
        assert isinstance(fields, dict)

        missing_field_keys = [
            key for key in self.config.required_field_keys if key not in fields
        ]
        self.assertFalse(
            missing_field_keys,
            "Expected result failed: the raw Jira issue fields object was missing "
            "expected issue metadata.\n"
            f"Missing field keys: {missing_field_keys}\n"
            f"Observed fields: {fields}",
        )
        self.assertEqual(
            fields["summary"],
            self.config.fixture_ticket.summary,
            "Expected result failed: the raw Jira issue fields did not preserve the "
            "ticket summary.\n"
            f"Observed fields: {fields}",
        )
        self.assertEqual(
            fields["description"],
            self.config.fixture_ticket.issue_description,
            "Expected result failed: the raw Jira issue fields did not preserve the "
            "ticket description.\n"
            f"Observed fields: {fields}",
        )

        project = fields["project"]
        self.assertIsInstance(
            project,
            dict,
            "Expected result failed: the raw Jira issue fields did not expose the "
            "project block as an object.\n"
            f"Observed fields: {fields}",
        )
        assert isinstance(project, dict)
        self.assertEqual(
            project.get("key"),
            self.config.project_key,
            "Expected result failed: the raw Jira issue fields did not identify the "
            "seeded project key.\n"
            f"Observed project payload: {project}",
        )
        self.assertEqual(
            project.get("name"),
            self.config.project_name,
            "Human-style verification failed: the visible project metadata did not "
            "show the seeded project name a user would inspect.\n"
            f"Observed project payload: {project}",
        )

        issuetype = fields["issuetype"]
        self.assertIsInstance(
            issuetype,
            dict,
            "Expected result failed: the raw Jira issue fields did not expose the "
            "issue type block as an object.\n"
            f"Observed fields: {fields}",
        )
        assert isinstance(issuetype, dict)
        self.assertEqual(
            issuetype.get("id"),
            self.config.fixture_ticket.issue_type,
            "Expected result failed: the raw Jira issue fields did not expose the "
            "canonical issue type id.\n"
            f"Observed issue type payload: {issuetype}",
        )

        status = fields["status"]
        self.assertIsInstance(
            status,
            dict,
            "Expected result failed: the raw Jira issue fields did not expose the "
            "status block as an object.\n"
            f"Observed fields: {fields}",
        )
        assert isinstance(status, dict)
        self.assertEqual(
            status.get("id"),
            self.config.fixture_ticket.status,
            "Expected result failed: the raw Jira issue fields did not expose the "
            "canonical status id.\n"
            f"Observed status payload: {status}",
        )

        for fragment in self.config.required_stdout_fragments:
            self.assertIn(
                fragment,
                observation.result.stdout,
                "Human-style verification failed: the terminal output did not visibly "
                "show the expected raw Jira issue content.\n"
                f"Missing fragment: {fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )
        for forbidden_fragment in ('"ok":', '"schemaVersion":', '"data":'):
            self.assertNotIn(
                forbidden_fragment,
                observation.result.stdout,
                "Human-style verification failed: the terminal output still showed "
                "TrackState envelope fields instead of a raw Jira issue object.\n"
                f"Unexpected fragment: {forbidden_fragment}\n"
                f"Observed stdout:\n{observation.result.stdout}",
            )


if __name__ == "__main__":
    unittest.main()
