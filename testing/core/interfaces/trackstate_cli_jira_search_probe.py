from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchConfig,
)
from testing.core.models.trackstate_cli_jira_search_result import (
    TrackStateCliJiraSearchValidationResult,
)


class TrackStateCliJiraSearchProbe(Protocol):
    def observe_search_response_shape(
        self,
        *,
        config: TrackStateCliJiraSearchConfig,
    ) -> TrackStateCliJiraSearchValidationResult: ...
