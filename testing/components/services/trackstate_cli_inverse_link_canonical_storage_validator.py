from __future__ import annotations

from testing.core.config.trackstate_cli_inverse_link_canonical_storage_config import (
    TrackStateCliInverseLinkCanonicalStorageConfig,
)
from testing.core.interfaces.trackstate_cli_inverse_link_canonical_storage_probe import (
    TrackStateCliInverseLinkCanonicalStorageProbe,
)
from testing.core.models.trackstate_cli_inverse_link_canonical_storage_result import (
    TrackStateCliInverseLinkCanonicalStorageValidationResult,
)


class TrackStateCliInverseLinkCanonicalStorageValidator:
    def __init__(
        self,
        probe: TrackStateCliInverseLinkCanonicalStorageProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliInverseLinkCanonicalStorageConfig,
    ) -> TrackStateCliInverseLinkCanonicalStorageValidationResult:
        return self._probe.observe_inverse_link_canonical_storage(config=config)
