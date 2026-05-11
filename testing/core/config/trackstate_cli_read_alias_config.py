from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchFixtureIssue,
)


@dataclass(frozen=True)
class TrackStateCliReadAliasCase:
    step: int
    name: str
    alias_command: tuple[str, ...]
    canonical_command: tuple[str, ...]
    expected_json_kind: str
    required_stdout_fragments: tuple[str, ...]


@dataclass(frozen=True)
class TrackStateCliReadAliasConfig:
    project_key: str
    project_name: str
    fixture_ticket: TrackStateCliJiraSearchFixtureIssue
    cases: tuple[TrackStateCliReadAliasCase, ...]

    @classmethod
    def from_defaults(cls) -> "TrackStateCliReadAliasConfig":
        fixture_ticket = TrackStateCliJiraSearchFixtureIssue(
            key="TS-20",
            summary="Alias coverage regression",
            assignee="cli-user",
            reporter="cli-user",
            issue_type="story",
            status="todo",
            description=(
                "Seeded local issue used to verify ticket and metadata shorthand "
                "commands return the same raw Jira payloads as canonical read commands."
            ),
        )
        return cls(
            project_key="TS",
            project_name="TrackState Alias Test Project",
            fixture_ticket=fixture_ticket,
            cases=(
                TrackStateCliReadAliasCase(
                    step=1,
                    name="ticket_get_shorthand",
                    alias_command=("trackstate", "ticket", "get", "TS-20"),
                    canonical_command=(
                        "trackstate",
                        "read",
                        "ticket",
                        "--key",
                        "TS-20",
                    ),
                    expected_json_kind="object",
                    required_stdout_fragments=(
                        '"key": "TS-20"',
                        '"summary": "Alias coverage regression"',
                        '"project": {',
                    ),
                ),
                TrackStateCliReadAliasCase(
                    step=2,
                    name="fields_list_shorthand",
                    alias_command=("trackstate", "fields", "list"),
                    canonical_command=("trackstate", "read", "fields"),
                    expected_json_kind="array",
                    required_stdout_fragments=(
                        '"id": "summary"',
                        '"name": "Summary"',
                        '"system": "summary"',
                    ),
                ),
                TrackStateCliReadAliasCase(
                    step=3,
                    name="statuses_list_shorthand",
                    alias_command=("trackstate", "statuses", "list"),
                    canonical_command=("trackstate", "read", "statuses"),
                    expected_json_kind="array",
                    required_stdout_fragments=(
                        '"name": "Story"',
                        '"id": "todo"',
                        '"statusCategory": {',
                    ),
                ),
            ),
        )
