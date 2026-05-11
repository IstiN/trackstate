from __future__ import annotations

from dataclasses import dataclass

from testing.core.config.trackstate_cli_invalid_pagination_config import (
    TrackStateCliInvalidPaginationCase,
)
from testing.core.models.trackstate_cli_jira_search_result import (
    TrackStateCliJiraSearchObservation,
)


@dataclass(frozen=True)
class TrackStateCliInvalidPaginationCaseResult:
    case: TrackStateCliInvalidPaginationCase
    observation: TrackStateCliJiraSearchObservation


@dataclass(frozen=True)
class TrackStateCliInvalidPaginationValidationResult:
    supported_control: TrackStateCliJiraSearchObservation
    case_results: tuple[TrackStateCliInvalidPaginationCaseResult, ...]
