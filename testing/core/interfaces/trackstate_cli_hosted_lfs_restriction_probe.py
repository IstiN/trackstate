from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_hosted_lfs_restriction_config import (
    TrackStateCliHostedLfsRestrictionConfig,
)
from testing.core.models.trackstate_cli_hosted_lfs_restriction_result import (
    TrackStateCliHostedLfsRestrictionValidationResult,
)


class TrackStateCliHostedLfsRestrictionProbe(Protocol):
    def observe(
        self,
        *,
        config: TrackStateCliHostedLfsRestrictionConfig,
    ) -> TrackStateCliHostedLfsRestrictionValidationResult: ...
