from __future__ import annotations

from pathlib import Path

from testing.core.config.unsupported_provider_cli_config import (
    UnsupportedProviderCliConfig,
)
from testing.core.interfaces.unsupported_provider_cli_probe import (
    UnsupportedProviderCliProbe,
)
from testing.core.models.unsupported_provider_cli_result import (
    UnsupportedProviderCliValidationResult,
)


class UnsupportedProviderCliValidator:
    def __init__(
        self,
        repository_root: Path,
        probe: UnsupportedProviderCliProbe,
    ) -> None:
        self._repository_root = Path(repository_root)
        self._probe = probe

    def validate(
        self,
        *,
        config: UnsupportedProviderCliConfig,
    ) -> UnsupportedProviderCliValidationResult:
        return UnsupportedProviderCliValidationResult(
            unsupported_provider=self._probe.unsupported_provider(config=config),
        )
