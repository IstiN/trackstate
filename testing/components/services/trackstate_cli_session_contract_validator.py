from __future__ import annotations

from testing.core.config.trackstate_cli_session_contract_config import (
    TrackStateCliSessionContractConfig,
)
from testing.core.interfaces.trackstate_cli_session_contract_probe import (
    TrackStateCliSessionContractProbe,
)
from testing.core.models.trackstate_cli_session_contract_result import (
    TrackStateCliSessionContractValidationResult,
)


class TrackStateCliSessionContractValidator:
    def __init__(self, probe: TrackStateCliSessionContractProbe) -> None:
        self._probe = probe

    def validate(
        self,
        *,
        config: TrackStateCliSessionContractConfig,
    ) -> TrackStateCliSessionContractValidationResult:
        return TrackStateCliSessionContractValidationResult(
            observation=self._probe.observe_default_json_session(config=config)
        )
