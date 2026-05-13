from __future__ import annotations

from testing.core.config.trackstate_cli_release_asset_filename_sanitization_config import (
    TrackStateCliReleaseAssetFilenameSanitizationConfig,
)
from testing.core.interfaces.trackstate_cli_release_asset_filename_sanitization_probe import (
    TrackStateCliReleaseAssetFilenameSanitizationProbe,
)
from testing.core.models.trackstate_cli_release_asset_filename_sanitization_result import (
    TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
)


class TrackStateCliReleaseAssetFilenameSanitizationValidator:
    def __init__(
        self,
        probe: TrackStateCliReleaseAssetFilenameSanitizationProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationValidationResult:
        return self._probe.observe_release_asset_filename_sanitization(config=config)
