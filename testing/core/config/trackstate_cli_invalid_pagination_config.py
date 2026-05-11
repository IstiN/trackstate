from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackStateCliInvalidPaginationCase:
    name: str
    requested_command: tuple[str, ...]
    expected_message: str
    expected_option: str
    expected_value: str


@dataclass(frozen=True)
class TrackStateCliInvalidPaginationConfig:
    supported_control_command: tuple[str, ...]
    expected_issue_keys: tuple[str, ...]
    expected_provider: str
    expected_target_type: str
    expected_control_start_at: int
    expected_control_max_results: int
    expected_control_total: int
    expected_error_category: str
    required_stdout_fragments: tuple[str, ...]
    invalid_start_at_case: TrackStateCliInvalidPaginationCase
    invalid_max_results_case: TrackStateCliInvalidPaginationCase

    @property
    def cases(self) -> tuple[TrackStateCliInvalidPaginationCase, ...]:
        return (
            self.invalid_start_at_case,
            self.invalid_max_results_case,
        )

    @classmethod
    def from_defaults(cls) -> "TrackStateCliInvalidPaginationConfig":
        return cls(
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
            expected_provider="local-git",
            expected_target_type="local",
            expected_control_start_at=0,
            expected_control_max_results=2,
            expected_control_total=2,
            expected_error_category="validation",
            required_stdout_fragments=(
                '"ok": false',
                '"category": "validation"',
            ),
            invalid_start_at_case=TrackStateCliInvalidPaginationCase(
                name="invalid_start_at_string",
                requested_command=(
                    "trackstate",
                    "search",
                    "--jql",
                    "project = TRACK",
                    "--startAt",
                    "first",
                ),
                expected_message='Option "--start-at" must be a non-negative integer.',
                expected_option="start-at",
                expected_value="first",
            ),
            invalid_max_results_case=TrackStateCliInvalidPaginationCase(
                name="invalid_max_results_negative",
                requested_command=(
                    "trackstate",
                    "search",
                    "--jql",
                    "project = TRACK",
                    "--maxResults",
                    "-10",
                ),
                expected_message='Option "--max-results" must be a non-negative integer.',
                expected_option="max-results",
                expected_value="-10",
            ),
        )
