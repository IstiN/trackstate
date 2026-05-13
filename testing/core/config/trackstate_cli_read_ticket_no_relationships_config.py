from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchFixtureIssue,
)
from testing.core.config.trackstate_cli_read_ticket_shape_config import (
    TrackStateCliReadTicketShapeConfig,
)


@dataclass(frozen=True)
class TrackStateCliReadTicketNoRelationshipsConfig(TrackStateCliReadTicketShapeConfig):
    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadTicketNoRelationshipsConfig":
        fixture_ticket = TrackStateCliJiraSearchFixtureIssue(
            key="TS-10",
            summary="No relationships mapper regression",
            assignee="cli-user",
            reporter="cli-user",
            description=(
                "Seeded local issue used to verify read ticket handles an empty Jira "
                "`issuelinks` array without mapping errors and without inventing "
                "relationship data."
            ),
        )
        return cls(
            project_key="TS",
            project_name="TrackState Read Ticket No Relationships Project",
            fixture_ticket=fixture_ticket,
            requested_command=("trackstate", "read", "ticket", "--key", "TS-10"),
            required_root_keys=("id", "key", "fields"),
            forbidden_root_keys=(
                "ok",
                "schemaVersion",
                "data",
                "provider",
                "target",
                "output",
                "error",
            ),
            required_field_keys=(
                "summary",
                "issuelinks",
            ),
            required_stdout_fragments=(
                '"id": "10"',
                '"key": "TS-10"',
                '"fields": {',
                '"summary": "No relationships mapper regression"',
                '"issuelinks": []',
            ),
            expected_issue_id="10",
        )
