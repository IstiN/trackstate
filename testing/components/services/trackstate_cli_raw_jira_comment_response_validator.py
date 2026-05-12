from __future__ import annotations

from testing.core.config.trackstate_cli_raw_jira_comment_response_config import (
    TrackStateCliRawJiraCommentResponseConfig,
)
from testing.core.interfaces.trackstate_cli_raw_jira_comment_response_probe import (
    TrackStateCliRawJiraCommentResponseProbe,
)
from testing.core.models.trackstate_cli_raw_jira_comment_response_result import (
    TrackStateCliRawJiraCommentResponseValidationResult,
)


class TrackStateCliRawJiraCommentResponseValidator:
    def __init__(self, probe: TrackStateCliRawJiraCommentResponseProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliRawJiraCommentResponseConfig,
    ) -> TrackStateCliRawJiraCommentResponseValidationResult:
        return self._probe.observe_raw_comment_response(config=config)
