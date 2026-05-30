from __future__ import annotations

from testing.core.config.trackstate_cli_release_download_missing_asset_config import (
    TrackStateCliReleaseDownloadMissingAssetConfig,
)
from testing.core.interfaces.trackstate_cli_release_download_missing_asset_probe import (
    TrackStateCliReleaseDownloadMissingAssetProbe,
)
from testing.core.models.trackstate_cli_release_download_missing_asset_result import (
    TrackStateCliReleaseDownloadMissingAssetValidationResult,
)


class TrackStateCliReleaseDownloadMissingAssetValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseDownloadMissingAssetProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseDownloadMissingAssetConfig,
    ) -> TrackStateCliReleaseDownloadMissingAssetValidationResult:
        return self._probe.observe_release_download_missing_asset(config=config)
