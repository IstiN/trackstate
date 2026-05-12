from __future__ import annotations

from testing.core.config.trackstate_cli_comment_creation_config import (
    TrackStateCliCommentCreationConfig,
)
from testing.core.interfaces.trackstate_cli_comment_creation_probe import (
    TrackStateCliCommentCreationProbe,
)
from testing.core.models.trackstate_cli_comment_creation_result import (
    TrackStateCliCommentCreationValidationResult,
)


class TrackStateCliCommentCreationValidator:
    def __init__(self, probe: TrackStateCliCommentCreationProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliCommentCreationConfig,
    ) -> TrackStateCliCommentCreationValidationResult:
        return TrackStateCliCommentCreationValidationResult(
            observation=self._probe.observe_non_idempotent_comment_creation(
                config=config
            )
        )
