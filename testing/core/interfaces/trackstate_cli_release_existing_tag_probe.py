from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_existing_tag_config import (
    TrackStateCliReleaseExistingTagConfig,
)
from testing.core.models.trackstate_cli_release_existing_tag_result import (
    TrackStateCliReleaseExistingTagValidationResult,
)


class TrackStateCliReleaseExistingTagProbe(Protocol):
    def observe_release_existing_tag(
        self,
        *,
        config: TrackStateCliReleaseExistingTagConfig,
        remote_origin_url: str,
        token: str,
    ) -> TrackStateCliReleaseExistingTagValidationResult: ...
