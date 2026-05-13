from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchFixtureIssue,
)


@dataclass(frozen=True)
class TrackStateCliLifecycleConfig:
    project_key: str
    project_name: str
    delete_issue: TrackStateCliJiraSearchFixtureIssue
    archive_issue: TrackStateCliJiraSearchFixtureIssue
    delete_command: tuple[str, ...]
    archive_command: tuple[str, ...]
    expected_deleted_issue_former_path: str
    expected_tombstone_artifact_path: str

    @classmethod
    def from_defaults(cls) -> "TrackStateCliLifecycleConfig":
        project_key = "TS"
        delete_issue = TrackStateCliJiraSearchFixtureIssue(
            key="TS-10",
            summary="Delete should reserve a tombstone",
            assignee="cli-user",
            reporter="cli-user",
            description=(
                "Seeded local issue used to verify permanent delete removes the "
                "repository folder and records a tombstone."
            ),
        )
        archive_issue = TrackStateCliJiraSearchFixtureIssue(
            key="TS-11",
            summary="Archive should stay reversible",
            assignee="cli-user",
            reporter="cli-user",
            description=(
                "Seeded local issue used to verify archive keeps the issue content "
                "available as an archived issue instead of hard deleting it."
            ),
        )
        return cls(
            project_key=project_key,
            project_name="TrackState Lifecycle Test Project",
            delete_issue=delete_issue,
            archive_issue=archive_issue,
            delete_command=("trackstate", "jira_delete_ticket", delete_issue.key),
            archive_command=("trackstate", "archive", archive_issue.key),
            expected_deleted_issue_former_path=f"{project_key}/{delete_issue.key}/main.md",
            expected_tombstone_artifact_path=(
                f"{project_key}/.trackstate/tombstones/{delete_issue.key}.json"
            ),
        )
