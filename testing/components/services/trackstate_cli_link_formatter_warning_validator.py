from __future__ import annotations

from testing.core.config.trackstate_cli_link_formatter_warning_config import (
    TrackStateCliLinkFormatterWarningConfig,
)
from testing.core.interfaces.trackstate_cli_link_formatter_warning_probe import (
    TrackStateCliLinkFormatterWarningProbe,
)
from testing.core.models.trackstate_cli_link_formatter_warning_result import (
    TrackStateCliLinkFormatterWarningValidationResult,
)


class TrackStateCliLinkFormatterWarningValidator:
    def __init__(
        self,
        probe: TrackStateCliLinkFormatterWarningProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliLinkFormatterWarningConfig,
    ) -> TrackStateCliLinkFormatterWarningValidationResult:
        return TrackStateCliLinkFormatterWarningValidationResult(
            observation=self._probe.observe(config=config)
        )
