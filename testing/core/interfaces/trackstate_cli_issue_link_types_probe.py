from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_issue_link_types_config import (
    TrackStateCliIssueLinkTypesConfig,
)
from testing.core.models.trackstate_cli_issue_link_types_result import (
    TrackStateCliIssueLinkTypesValidationResult,
)


class TrackStateCliIssueLinkTypesProbe(Protocol):
    def observe_issue_link_types(
        self,
        *,
        config: TrackStateCliIssueLinkTypesConfig,
    ) -> TrackStateCliIssueLinkTypesValidationResult: ...
