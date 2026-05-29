from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_draft_creation_config import (
    TrackStateCliReleaseDraftCreationConfig,
)
from testing.core.models.trackstate_cli_release_draft_creation_result import (
    TrackStateCliReleaseDraftCreationValidationResult,
)


class TrackStateCliReleaseDraftCreationProbe(Protocol):
    def observe_release_draft_creation(
        self,
        *,
        config: TrackStateCliReleaseDraftCreationConfig,
    ) -> TrackStateCliReleaseDraftCreationValidationResult: ...
