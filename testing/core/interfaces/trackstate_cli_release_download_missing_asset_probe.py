from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_download_missing_asset_config import (
    TrackStateCliReleaseDownloadMissingAssetConfig,
)
from testing.core.models.trackstate_cli_release_download_missing_asset_result import (
    TrackStateCliReleaseDownloadMissingAssetValidationResult,
)


class TrackStateCliReleaseDownloadMissingAssetProbe(Protocol):
    def observe_release_download_missing_asset(
        self,
        *,
        config: TrackStateCliReleaseDownloadMissingAssetConfig,
    ) -> TrackStateCliReleaseDownloadMissingAssetValidationResult: ...
