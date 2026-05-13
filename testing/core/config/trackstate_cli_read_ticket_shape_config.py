from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchFixtureIssue,
)


@dataclass(frozen=True)
class TrackStateCliReadTicketShapeConfig:
    project_key: str
    project_name: str
    fixture_ticket: TrackStateCliJiraSearchFixtureIssue
    requested_command: tuple[str, ...]
    required_root_keys: tuple[str, ...]
    forbidden_root_keys: tuple[str, ...]
    required_field_keys: tuple[str, ...]
    required_stdout_fragments: tuple[str, ...]
    expected_issue_id: str

    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadTicketShapeConfig":
        fixture_ticket = TrackStateCliJiraSearchFixtureIssue(
            key="TS-20",
            summary="Raw Jira issue output regression",
            assignee="cli-user",
            reporter="cli-user",
            issue_type="story",
            status="todo",
            description=(
                "Seeded local issue used to verify the canonical read ticket command "
                "returns a single raw Jira issue object without the TrackState "
                "success envelope."
            ),
        )
        return cls(
            project_key="TS",
            project_name="TrackState Read Test Project",
            fixture_ticket=fixture_ticket,
            requested_command=("trackstate", "read", "ticket", "--key", "TS-20"),
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
                "description",
                "issuetype",
                "status",
                "priority",
                "project",
                "assignee",
                "reporter",
                "labels",
                "components",
                "fixVersions",
                "parent",
            ),
            required_stdout_fragments=(
                '"id": "20"',
                '"key": "TS-20"',
                '"fields": {',
                '"summary": "Raw Jira issue output regression"',
                '"project": {',
                '"name": "TrackState Read Test Project"',
            ),
            expected_issue_id="20",
        )
