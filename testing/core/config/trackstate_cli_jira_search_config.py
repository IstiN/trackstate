from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliJiraSearchConfig:
    requested_command: tuple[str, ...]
    supported_control_command: tuple[str, ...]
    expected_issue_keys: tuple[str, ...]
    required_data_keys: tuple[str, ...]
    expected_provider: str
    expected_target_type: str
    expected_start_at: int
    expected_max_results: int
    expected_total: int
    expected_is_last_page: bool

    @classmethod
    def from_defaults(cls) -> "TrackStateCliJiraSearchConfig":
        return cls(
            requested_command=(
                "trackstate",
                "search",
                "--jql",
                "project = TRACK",
                "--startAt",
                "0",
                "--maxResults",
                "2",
            ),
            supported_control_command=(
                "trackstate",
                "search",
                "--target",
                "local",
                "--jql",
                "project = TRACK",
                "--start-at",
                "0",
                "--max-results",
                "2",
            ),
            expected_issue_keys=("TRACK-1", "TRACK-2"),
            required_data_keys=("issues", "startAt", "maxResults", "total", "isLastPage"),
            expected_provider="local-git",
            expected_target_type="local",
            expected_start_at=0,
            expected_max_results=2,
            expected_total=2,
            expected_is_last_page=True,
        )
