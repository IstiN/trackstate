from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_inverse_link_canonical_storage_config import (
    TrackStateCliInverseLinkCanonicalStorageConfig,
)
from testing.core.models.trackstate_cli_inverse_link_canonical_storage_result import (
    TrackStateCliInverseLinkCanonicalStorageValidationResult,
)


class TrackStateCliInverseLinkCanonicalStorageProbe(Protocol):
    def observe_inverse_link_canonical_storage(
        self,
        *,
        config: TrackStateCliInverseLinkCanonicalStorageConfig,
    ) -> TrackStateCliInverseLinkCanonicalStorageValidationResult: ...
