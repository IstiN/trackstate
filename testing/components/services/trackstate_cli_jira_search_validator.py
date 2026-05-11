from __future__ import annotations

from testing.core.config.trackstate_cli_jira_search_config import (
    TrackStateCliJiraSearchConfig,
)
from testing.core.interfaces.trackstate_cli_jira_search_probe import (
    TrackStateCliJiraSearchProbe,
)
from testing.core.models.trackstate_cli_jira_search_result import (
    TrackStateCliJiraSearchValidationResult,
)


class TrackStateCliJiraSearchValidator:
    def __init__(self, probe: TrackStateCliJiraSearchProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliJiraSearchConfig,
    ) -> TrackStateCliJiraSearchValidationResult:
        return self._probe.observe_search_response_shape(config=config)
