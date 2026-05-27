from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_comment_creation_config import (
    TrackStateCliCommentCreationConfig,
)
from testing.core.models.trackstate_cli_comment_creation_result import (
    TrackStateCliCommentCreationObservation,
)


class TrackStateCliCommentCreationProbe(Protocol):
    def observe_non_idempotent_comment_creation(
        self,
        *,
        config: TrackStateCliCommentCreationConfig,
    ) -> TrackStateCliCommentCreationObservation: ...
