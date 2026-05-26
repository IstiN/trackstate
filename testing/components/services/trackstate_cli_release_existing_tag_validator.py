from __future__ import annotations

from testing.core.config.trackstate_cli_release_existing_tag_config import (
    TrackStateCliReleaseExistingTagConfig,
)
from testing.core.interfaces.trackstate_cli_release_existing_tag_probe import (
    TrackStateCliReleaseExistingTagProbe,
)
from testing.core.models.trackstate_cli_release_existing_tag_result import (
    TrackStateCliReleaseExistingTagValidationResult,
)


class TrackStateCliReleaseExistingTagValidator:
    def __init__(self, probe: TrackStateCliReleaseExistingTagProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseExistingTagConfig,
        remote_origin_url: str,
        token: str,
    ) -> TrackStateCliReleaseExistingTagValidationResult:
        return self._probe.observe_release_existing_tag(
            config=config,
            remote_origin_url=remote_origin_url,
            token=token,
        )
