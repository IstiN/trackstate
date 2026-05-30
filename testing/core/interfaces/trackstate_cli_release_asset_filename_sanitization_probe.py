from __future__ import annotations

from typing import Protocol

from testing.core.config.trackstate_cli_release_asset_filename_sanitization_config import (
    TrackStateCliReleaseAssetFilenameSanitizationConfig,
)
from testing.core.models.trackstate_cli_release_asset_filename_sanitization_result import (
    TrackStateCliReleaseAssetFilenameSanitizationValidationResult,
)


class TrackStateCliReleaseAssetFilenameSanitizationProbe(Protocol):
    def observe_release_asset_filename_sanitization(
        self,
        *,
        config: TrackStateCliReleaseAssetFilenameSanitizationConfig,
    ) -> TrackStateCliReleaseAssetFilenameSanitizationValidationResult: ...
