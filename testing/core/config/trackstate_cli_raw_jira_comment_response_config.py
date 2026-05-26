from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliRawJiraCommentFixture:
    id: str
    author: str
    created: str
    updated: str
    body: str


@dataclass(frozen=True)
class TrackStateCliRawJiraCommentResponseConfig:
    ticket_command: tuple[str, ...]
    compatibility_command: tuple[str, ...]
    project_key: str
    project_name: str
    issue_key: str
    issue_summary: str
    fixture_comments: tuple[TrackStateCliRawJiraCommentFixture, ...]
    required_root_keys: tuple[str, ...]
    forbidden_root_keys: tuple[str, ...]
    required_stdout_fragments: tuple[str, ...]

    @property
    def expected_comment_count(self) -> int:
        return len(self.fixture_comments)

    @classmethod
    def from_defaults(cls) -> "TrackStateCliRawJiraCommentResponseConfig":
        fixture_comments = (
            TrackStateCliRawJiraCommentFixture(
                id="0001",
                author="qa-user",
                created="2026-05-12T09:00:00Z",
                updated="2026-05-12T09:00:00Z",
                body="TS-384 first seeded comment confirms the oldest visible Jira row.",
            ),
            TrackStateCliRawJiraCommentFixture(
                id="0002",
                author="qa-user",
                created="2026-05-12T09:05:00Z",
                updated="2026-05-12T09:05:00Z",
                body="TS-384 second seeded comment confirms the raw comments array stays unwrapped.",
            ),
        )
        return cls(
            ticket_command=(
                "trackstate",
                "jira_execute_request",
                "--method",
                "GET",
                "--path",
                "rest/api/2/issue/TS-22/comment",
            ),
            compatibility_command=(
                "trackstate",
                "jira_execute_request",
                "--target",
                "local",
                "--method",
                "GET",
                "--request-path",
                "/rest/api/2/issue/TS-22/comment",
            ),
            project_key="TS",
            project_name="TS-384 Project",
            issue_key="TS-22",
            issue_summary="Raw Jira compatibility fixture",
            fixture_comments=fixture_comments,
            required_root_keys=("startAt", "maxResults", "total", "comments"),
            forbidden_root_keys=("ok", "schemaVersion", "data", "provider", "target", "output"),
            required_stdout_fragments=(
                '"startAt": 0',
                '"comments": [',
                *(comment.body for comment in fixture_comments),
            ),
        )
