from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_raw_jira_comment_response_config import (
    TrackStateCliRawJiraCommentResponseConfig,
)
from testing.core.models.trackstate_cli_raw_jira_comment_response_result import (
    TrackStateCliRawJiraCommentResponseValidationResult,
)


class TrackStateCliRawJiraCommentResponseProbe(Protocol):
    def observe_raw_comment_response(
        self,
        *,
        config: TrackStateCliRawJiraCommentResponseConfig,
    ) -> TrackStateCliRawJiraCommentResponseValidationResult: ...
