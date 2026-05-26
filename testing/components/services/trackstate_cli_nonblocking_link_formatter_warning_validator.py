from __future__ import annotations

from testing.core.config.trackstate_cli_nonblocking_link_formatter_warning_config import (
    TrackStateCliNonblockingLinkFormatterWarningConfig,
)
from testing.core.interfaces.trackstate_cli_nonblocking_link_formatter_warning_probe import (
    TrackStateCliNonblockingLinkFormatterWarningProbe,
)
from testing.core.models.trackstate_cli_nonblocking_link_formatter_warning_result import (
    TrackStateCliNonblockingLinkFormatterWarningValidationResult,
)


class TrackStateCliNonblockingLinkFormatterWarningValidator:
    def __init__(
        self,
        probe: TrackStateCliNonblockingLinkFormatterWarningProbe,
    ) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliNonblockingLinkFormatterWarningConfig,
    ) -> TrackStateCliNonblockingLinkFormatterWarningValidationResult:
        return TrackStateCliNonblockingLinkFormatterWarningValidationResult(
            observation=self._probe.observe(config=config)
        )
