from __future__ import annotations

from testing.core.config.trackstate_cli_release_draft_creation_config import (
    TrackStateCliReleaseDraftCreationConfig,
)
from testing.core.interfaces.trackstate_cli_release_draft_creation_probe import (
    TrackStateCliReleaseDraftCreationProbe,
)
from testing.core.models.trackstate_cli_release_draft_creation_result import (
    TrackStateCliReleaseDraftCreationValidationResult,
)


class TrackStateCliReleaseDraftCreationValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseDraftCreationProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseDraftCreationConfig,
    ) -> TrackStateCliReleaseDraftCreationValidationResult:
        return self._probe.observe_release_draft_creation(config=config)
