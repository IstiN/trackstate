from __future__ import annotations

from testing.core.config.trackstate_cli_hosted_lfs_restriction_config import (
    TrackStateCliHostedLfsRestrictionConfig,
)
from testing.core.interfaces.trackstate_cli_hosted_lfs_restriction_probe import (
    TrackStateCliHostedLfsRestrictionProbe,
)
from testing.core.models.trackstate_cli_hosted_lfs_restriction_result import (
    TrackStateCliHostedLfsRestrictionValidationResult,
)


class TrackStateCliHostedLfsRestrictionValidator:
    def __init__(
        self,
        probe: TrackStateCliHostedLfsRestrictionProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliHostedLfsRestrictionConfig,
    ) -> TrackStateCliHostedLfsRestrictionValidationResult:
        return self._probe.observe(config=config)
