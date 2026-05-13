from __future__ import annotations

from testing.core.config.trackstate_cli_issue_link_types_config import (
    TrackStateCliIssueLinkTypesConfig,
)
from testing.core.interfaces.trackstate_cli_issue_link_types_probe import (
    TrackStateCliIssueLinkTypesProbe,
)
from testing.core.models.trackstate_cli_issue_link_types_result import (
    TrackStateCliIssueLinkTypesValidationResult,
)


class TrackStateCliIssueLinkTypesValidator:
    def __init__(self, probe: TrackStateCliIssueLinkTypesProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliIssueLinkTypesConfig,
    ) -> TrackStateCliIssueLinkTypesValidationResult:
        return self._probe.observe_issue_link_types(config=config)
